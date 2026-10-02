import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.store import StoreCategory, StorePricingRule, StoreProduct
from app.models.store_enums import StorePricingRuleType, StoreProductType, StoreUnit
from app.schemas.store_pricing import CorniceInput, PilasterInput, PricingCalculateRequest, RoundColumnInput, ShohonaInput, TrimInput
from app.services.store_pricing.errors import PricingError
from app.services.store_pricing.money import PI, quantize_money
from app.services.store_pricing.service import calculate_quote
from app.store.catalog_seed import seed_store_categories

TRIM = {
    "opening": "window",
    "discount_percent": "10",
    "sizes": {
        "M": {
            "cornice": "10000",
            "jamb": "8000",
            "sill": "5000",
            "extra_meter": {"cornice": "2000", "jamb": "2000", "sill": "1500"},
        }
    },
    "addons": {"kalvak": "3000", "karona": "4500"},
}
PILASTER = {
    "meter_prices": {"30": {"4": "10000", "3.50": "9000"}, "25": {"4": "8000"}},
    "capitals": {"klassik": "7000"},
    "bases": {"oddiy": "4000"},
}
ROUND = {
    "meter_price": "10000",
    "coating_multiplier": "1.7",
    "capitals": {
        "oddiy": [
            {"min_diameter_cm": "25", "max_diameter_cm": "30", "price": "5000"},
            {"min_diameter_cm": "30", "max_diameter_cm": "35", "price": "8000"},
        ],
        "gulli": [
            {"min_diameter_cm": "25", "max_diameter_cm": "30", "price": "9000"},
            {"min_diameter_cm": "30", "max_diameter_cm": "35", "price": "12000"},
        ],
    },
    "bases": {
        "oddiy": [
            {"min_diameter_cm": "25", "max_diameter_cm": "30", "price": "3000"},
            {"min_diameter_cm": "30", "max_diameter_cm": "35", "price": "4500"},
        ]
    },
}


def _category(slug: str, *, category_id: int, parent: StoreCategory | None = None, rules: list | None = None) -> StoreCategory:
    category = StoreCategory(
        id=category_id,
        name=slug,
        slug=slug,
        sort_order=0,
        is_active=True,
        parent_id=None if parent is None else parent.id,
    )
    category.parent = parent
    category.pricing_rules = list(rules or [])
    return category


def _rule(rule_type: StorePricingRuleType, config: dict, *, active: bool = True, rule_id: int = 5) -> StorePricingRule:
    return StorePricingRule(
        id=rule_id,
        rule_type=rule_type,
        name="Narx",
        config=config,
        is_active=active,
    )


def _product(
    category: StoreCategory,
    *,
    product_type: StoreProductType = StoreProductType.MADE_TO_ORDER,
    unit: StoreUnit = StoreUnit.SET,
    rules: list | None = None,
    price: str | None = None,
    stock: int | None = None,
    active: bool = True,
    name: str = "Model",
) -> StoreProduct:
    product = StoreProduct(
        id=10,
        category_id=category.id,
        name=name,
        slug="model",
        images=[],
        product_type=product_type,
        unit=unit,
        is_active=active,
        selling_price=price,
        available_quantity=stock,
    )
    product.category = category
    product.pricing_rules = list(rules or [])
    return product


def _rooted(root_slug: str, child_slug: str | None = None) -> StoreCategory:
    root = _category(root_slug, category_id=1)
    if child_slug is None:
        return root
    return _category(child_slug, category_id=2, parent=root)


def _trim_product(*, door: bool = False, rules: list | None = None) -> StoreProduct:
    if door:
        category = _rooted("rom-va-eshik", "eshik-bezaklari")
    else:
        category = _rooted("rom-va-eshik", "deraza-romlari")
    rule = _rule(StorePricingRuleType.FIXED, TRIM)
    return _product(category, rules=rules if rules is not None else [rule])


def _request(product: StoreProduct, **fields) -> PricingCalculateRequest:
    return PricingCalculateRequest(product_id=product.id, **fields)


def test_money_rounds_half_up():
    assert quantize_money(Decimal("1.005")) == Decimal("1.01")
    assert quantize_money(Decimal("1.004")) == Decimal("1.00")


def test_trim_set_sums_component_prices():
    product = _trim_product()
    quote = calculate_quote(
        product,
        _request(product, quantity=1, trim=TrimInput(size="M", components=["cornice", "jamb", "sill"])),
    )
    assert quote.status == "PRICED"
    assert quote.currency == "UZS"
    assert [item.amount for item in quote.components] == ["10000.00", "8000.00", "5000.00"]
    assert quote.total == "23000.00"
    assert quote.subtotal == "23000.00"
    assert quote.requires_manual_quote is False

    with_addon = calculate_quote(
        product,
        _request(
            product,
            quantity=1,
            trim=TrimInput(size="M", components=["cornice", "jamb", "sill"], addons=["kalvak"]),
        ),
    )
    assert with_addon.total == "26000.00"
    karona = calculate_quote(
        product,
        _request(
            product,
            quantity=1,
            trim=TrimInput(size="M", components=["sill"], addons=["karona"]),
        ),
    )
    assert karona.total == "9500.00"
    doubled = calculate_quote(
        product,
        _request(product, quantity=2, trim=TrimInput(size="M", components=["cornice", "jamb", "sill"])),
    )
    assert doubled.total == "46000.00"


def test_removing_trim_component_reduces_total():
    product = _trim_product()
    full = calculate_quote(
        product,
        _request(product, quantity=1, trim=TrimInput(size="M", components=["cornice", "jamb", "sill"])),
    )
    without_sill = calculate_quote(
        product,
        _request(product, quantity=1, trim=TrimInput(size="M", components=["cornice", "jamb"])),
    )
    assert full.total == "23000.00"
    assert without_sill.total == "18000.00"
    assert Decimal(without_sill.total) == Decimal(full.total) - Decimal("5000.00")


def test_trim_extra_meters_use_component_meter_price():
    product = _trim_product()
    quote = calculate_quote(
        product,
        _request(
            product,
            quantity=1,
            trim=TrimInput(
                size="M",
                components=["cornice", "jamb", "sill"],
                extra_meters={"jamb": "0.5"},
            ),
        ),
    )
    extra = next(item for item in quote.components if item.code == "extra_jamb")
    assert extra.amount == "1000.00"
    assert quote.total == "24000.00"
    with pytest.raises(PricingError) as stray:
        calculate_quote(
            product,
            _request(
                product,
                quantity=1,
                trim=TrimInput(size="M", components=["cornice"], extra_meters={"jamb": "1"}),
            ),
        )
    assert stray.value.code == "INVALID_INPUT"


def test_door_rejects_sill():
    product = _trim_product(door=True)
    with pytest.raises(PricingError) as rejected:
        calculate_quote(
            product,
            _request(product, quantity=1, trim=TrimInput(size="M", components=["cornice", "sill"])),
        )
    assert rejected.value.code == "INVALID_INPUT"
    assert rejected.value.status_code == 422
    assert "podokonnik" in rejected.value.message

    with pytest.raises(PricingError) as extra:
        calculate_quote(
            product,
            _request(
                product,
                quantity=1,
                trim=TrimInput(size="M", components=["jamb"], extra_meters={"sill": "1"}),
            ),
        )
    assert extra.value.code == "INVALID_INPUT"

    allowed = calculate_quote(
        product,
        _request(product, quantity=1, trim=TrimInput(size="M", components=["cornice", "jamb"])),
    )
    assert allowed.total == "18000.00"
    assert allowed.applied["opening"] == "door"


def test_pilaster_exact_width_and_thickness():
    category = _category("pilastrlar", category_id=1)
    product = _product(category, unit=StoreUnit.PIECE, rules=[_rule(StorePricingRuleType.DIMENSION_COMBINATION, PILASTER)])
    quote = calculate_quote(
        product,
        _request(
            product,
            quantity=3,
            pilaster=PilasterInput(width_cm="30", thickness_cm="4", length_m="2", capital="klassik", base="oddiy"),
        ),
    )
    amounts = {item.code: item.amount for item in quote.components}
    assert amounts == {"body": "60000.00", "capital": "21000.00", "base": "12000.00"}
    assert quote.total == "93000.00"
    assert quote.unit_price == "31000.00"

    half = calculate_quote(
        product,
        _request(
            product,
            quantity=1,
            pilaster=PilasterInput(width_cm="30.0", thickness_cm="3.5", length_m="1"),
        ),
    )
    assert half.total == "9000.00"


def test_pilaster_missing_combination_is_not_configured():
    category = _category("pilastrlar", category_id=1)
    product = _product(category, unit=StoreUnit.PIECE, rules=[_rule(StorePricingRuleType.DIMENSION_COMBINATION, PILASTER)])
    with pytest.raises(PricingError) as missing:
        calculate_quote(
            product,
            _request(
                product,
                quantity=1,
                pilaster=PilasterInput(width_cm="45", thickness_cm="6", length_m="1"),
            ),
        )
    assert missing.value.code == "PRICE_NOT_CONFIGURED"
    assert missing.value.status_code == 409


def _round_product(config: dict | None = None) -> StoreProduct:
    category = _category("yumaloq-ustunlar", category_id=1)
    return _product(
        category,
        unit=StoreUnit.PIECE,
        rules=[_rule(StorePricingRuleType.ROUND_COLUMN, ROUND if config is None else config)],
    )


def _round_input(**overrides) -> RoundColumnInput:
    payload = {
        "existing_diameter_cm": "20",
        "final_diameter_cm": "30",
        "height_m": "2",
        "coating": False,
    }
    payload.update(overrides)
    return RoundColumnInput(**payload)


def test_round_column_height_and_quantity():
    product = _round_product()
    quote = calculate_quote(product, _request(product, quantity=2, round_column=_round_input()))
    assert quote.components[0].amount == "40000.00"
    assert quote.total == "40000.00"
    other_model = calculate_quote(
        product,
        _request(product, quantity=2, round_column=_round_input(model="boshqa-model")),
    )
    assert other_model.total == quote.total


def test_round_column_coating_multiplier_comes_from_config():
    product = _round_product()
    coated = calculate_quote(product, _request(product, quantity=2, round_column=_round_input(coating=True)))
    assert coated.applied["coating_multiplier"] == "1.7"
    assert coated.components[0].amount == "68000.00"
    assert coated.total == "68000.00"

    doubled = dict(ROUND)
    doubled["coating_multiplier"] = "2.0"
    by_config = calculate_quote(
        _round_product(doubled),
        _request(product, quantity=2, round_column=_round_input(coating=True)),
    )
    assert by_config.total == "80000.00"

    plain = calculate_quote(
        _round_product(doubled),
        _request(product, quantity=2, round_column=_round_input(coating=False)),
    )
    assert plain.total == "40000.00"
    assert "coating_multiplier" not in plain.applied

    missing = dict(ROUND)
    del missing["coating_multiplier"]
    with pytest.raises(PricingError) as error:
        calculate_quote(_round_product(missing), _request(product, quantity=1, round_column=_round_input(coating=True)))
    assert error.value.code == "PRICE_NOT_CONFIGURED"

    floated = dict(ROUND)
    floated["coating_multiplier"] = 1.5
    with pytest.raises(PricingError) as float_error:
        calculate_quote(_round_product(floated), _request(product, quantity=1, round_column=_round_input(coating=True)))
    assert float_error.value.code == "PRICE_NOT_CONFIGURED"


def test_round_capital_and_base_use_diameter_band():
    product = _round_product()
    quote = calculate_quote(
        product,
        _request(
            product,
            quantity=2,
            round_column=_round_input(final_diameter_cm="30", capital="oddiy", base="oddiy"),
        ),
    )
    amounts = {item.code: item.amount for item in quote.components}
    assert amounts["body"] == "40000.00"
    assert amounts["capital"] == "16000.00"
    assert amounts["base"] == "9000.00"
    assert quote.total == "65000.00"

    floral = calculate_quote(
        product,
        _request(product, quantity=2, round_column=_round_input(final_diameter_cm="30", capital="gulli")),
    )
    assert next(item.amount for item in floral.components if item.code == "capital") == "24000.00"

    lower = calculate_quote(
        product,
        _request(product, quantity=1, round_column=_round_input(final_diameter_cm="25", capital="oddiy")),
    )
    assert next(item.amount for item in lower.components if item.code == "capital") == "5000.00"

    circumference = str(Decimal("10") * PI)
    from_circumference = calculate_quote(
        product,
        _request(
            product,
            quantity=1,
            round_column=RoundColumnInput(
                circumference_cm=circumference,
                final_diameter_cm="30",
                height_m="1",
                capital="oddiy",
            ),
        ),
    )
    assert next(item.amount for item in from_circumference.components if item.code == "capital") == "8000.00"
    assert from_circumference.applied["final_diameter_cm"] == "30"


def test_round_diameter_band_boundaries():
    product = _round_product()
    at_thirty = calculate_quote(
        product,
        _request(product, quantity=1, round_column=_round_input(final_diameter_cm="30", capital="oddiy")),
    )
    just_below = calculate_quote(
        product,
        _request(product, quantity=1, round_column=_round_input(final_diameter_cm="29.999", capital="oddiy")),
    )
    assert next(item.amount for item in at_thirty.components if item.code == "capital") == "8000.00"
    assert next(item.amount for item in just_below.components if item.code == "capital") == "5000.00"

    with pytest.raises(PricingError) as upper:
        calculate_quote(
            product,
            _request(product, quantity=1, round_column=_round_input(final_diameter_cm="35", capital="oddiy")),
        )
    assert upper.value.code == "PRICE_NOT_CONFIGURED"

    overlapping = {
        "meter_price": "10000",
        "capitals": {
            "oddiy": [
                {"min_diameter_cm": "25", "max_diameter_cm": "31", "price": "5000"},
                {"min_diameter_cm": "30", "max_diameter_cm": "35", "price": "8000"},
            ]
        },
    }
    with pytest.raises(PricingError) as conflict:
        calculate_quote(
            _round_product(overlapping),
            _request(product, quantity=1, round_column=_round_input(final_diameter_cm="26", capital="oddiy")),
        )
    assert conflict.value.code == "CONFLICTING_RULES"


def test_cornice_width_proportional_formula():
    category = _category("shift-karnizlari", category_id=1)
    config = {"base_width_cm": "25", "base_meter_price": "30000", "coating_multiplier": "2"}
    product = _product(
        category,
        unit=StoreUnit.METER,
        rules=[_rule(StorePricingRuleType.WIDTH_PROPORTIONAL, config)],
    )
    quote = calculate_quote(
        product,
        _request(product, quantity=1, cornice=CorniceInput(width_cm="20", length_m="2")),
    )
    assert quote.applied["meter_price"] == "24000.00"
    assert quote.total == "48000.00"
    assert quote.applied["coating"] == "false"

    with pytest.raises(PricingError) as coating:
        calculate_quote(
            product,
            _request(product, quantity=1, cornice=CorniceInput(width_cm="20", length_m="2", coating=True)),
        )
    assert coating.value.code == "PRICE_NOT_CONFIGURED"

    narrow = _product(
        category,
        unit=StoreUnit.METER,
        rules=[_rule(StorePricingRuleType.WIDTH_PROPORTIONAL, {"base_width_cm": "8", "base_meter_price": "1"})],
    )
    rounded = calculate_quote(
        narrow,
        _request(narrow, quantity=1, cornice=CorniceInput(width_cm="1", length_m="3")),
    )
    assert rounded.applied["meter_price"] == "0.13"
    assert rounded.total == "0.39"


def test_shohona_requires_manual_quote():
    category = _category("shohona-karnizlar", category_id=1)
    priced_rule = _rule(StorePricingRuleType.MANUAL_QUOTE, {"price": "50000"}, rule_id=8)
    product = _product(category, rules=[priced_rule])
    quote = calculate_quote(
        product,
        _request(
            product,
            quantity=1,
            shohona=ShohonaInput(length_m="3.2", size_note="katta", coating=True, model="gul"),
            client_price="1",
        ),
    )
    assert quote.status == "MANUAL_QUOTE_REQUIRED"
    assert quote.requires_manual_quote is True
    assert quote.total is None
    assert quote.unit_price is None
    assert quote.subtotal is None
    assert quote.components == []
    assert quote.applied["length_m"] == "3.2"
    assert quote.applied["rule_id"] == "8"
    assert "50000" not in str(quote.applied.values())

    wrong_rule = _product(category, rules=[_rule(StorePricingRuleType.FIXED, {"price": "50000"})])
    with pytest.raises(PricingError) as conflict:
        calculate_quote(wrong_rule, _request(wrong_rule, quantity=1))
    assert conflict.value.code == "CONFLICTING_RULES"


def test_ready_made_price_and_stock():
    category = _category("tayyor-mahsulotlar", category_id=1)
    product = _product(
        category,
        product_type=StoreProductType.READY_MADE,
        unit=StoreUnit.PIECE,
        price="1500.50",
        stock=3,
        name="Tayyor karniz",
    )
    quote = calculate_quote(product, _request(product, quantity=2, client_price="1", total="1"))
    assert quote.total == "3001.00"
    assert quote.unit_price == "1500.50"
    assert quote.components[0].amount == "3001.00"
    assert product.available_quantity == 3

    with pytest.raises(PricingError) as stock:
        calculate_quote(product, _request(product, quantity=4))
    assert stock.value.code == "INSUFFICIENT_STOCK"
    assert product.available_quantity == 3

    free = _product(
        category,
        product_type=StoreProductType.READY_MADE,
        unit=StoreUnit.PIECE,
        price="0.00",
        stock=3,
    )
    with pytest.raises(PricingError) as missing:
        calculate_quote(free, _request(free, quantity=1))
    assert missing.value.code == "PRICE_NOT_CONFIGURED"


def test_inactive_rule_is_not_used():
    category = _category("pilastrlar", category_id=1)
    inactive = _rule(
        StorePricingRuleType.DIMENSION_COMBINATION,
        {"meter_prices": {"30": {"4": "99999"}}, "capitals": {}, "bases": {}},
        active=False,
        rule_id=1,
    )
    product = _product(category, unit=StoreUnit.PIECE, rules=[inactive])
    request = _request(product, quantity=1, pilaster=PilasterInput(width_cm="30", thickness_cm="4", length_m="2"))
    with pytest.raises(PricingError) as missing:
        calculate_quote(product, request)
    assert missing.value.code == "PRICE_NOT_CONFIGURED"

    active = _rule(StorePricingRuleType.DIMENSION_COMBINATION, PILASTER, rule_id=2)
    category.pricing_rules = [active]
    priced = calculate_quote(product, request)
    assert priced.total == "20000.00"
    assert priced.applied["rule_id"] == "2"

    product.pricing_rules = [
        _rule(StorePricingRuleType.DIMENSION_COMBINATION, PILASTER, rule_id=3),
        _rule(StorePricingRuleType.DIMENSION_COMBINATION, PILASTER, rule_id=4),
    ]
    with pytest.raises(PricingError) as conflict:
        calculate_quote(product, request)
    assert conflict.value.code == "CONFLICTING_RULES"

    hidden = _product(category, unit=StoreUnit.PIECE, rules=[active], active=False)
    with pytest.raises(PricingError) as inactive_product:
        calculate_quote(hidden, _request(hidden, quantity=1, pilaster=PilasterInput(width_cm="30", thickness_cm="4", length_m="1")))
    assert inactive_product.value.code == "PRODUCT_INACTIVE"


def test_invalid_measurements_are_rejected():
    category = _category("pilastrlar", category_id=1)
    product = _product(category, unit=StoreUnit.PIECE, rules=[_rule(StorePricingRuleType.DIMENSION_COMBINATION, PILASTER)])
    with pytest.raises(PricingError) as negative:
        calculate_quote(
            product,
            _request(product, quantity=1, pilaster=PilasterInput(width_cm="30", thickness_cm="4", length_m="-2")),
        )
    assert negative.value.code == "INVALID_INPUT"
    assert negative.value.status_code == 422

    with pytest.raises(PricingError) as zero_length:
        calculate_quote(
            product,
            _request(product, quantity=1, pilaster=PilasterInput(width_cm="30", thickness_cm="4", length_m="0")),
        )
    assert zero_length.value.code == "INVALID_INPUT"

    with pytest.raises(PricingError) as width:
        calculate_quote(
            product,
            _request(product, quantity=1, pilaster=PilasterInput(width_cm="32", thickness_cm="4", length_m="1")),
        )
    assert width.value.code == "INVALID_INPUT"

    with pytest.raises(ValidationError):
        PricingCalculateRequest(product_id=product.id, quantity=0)

    with pytest.raises(ValidationError):
        TrimInput(size="XL", components=["cornice"])


def test_config_float_is_rejected():
    category = _category("pilastrlar", category_id=1)
    config = {"meter_prices": {"30": {"4": 10000.0}}}
    product = _product(category, unit=StoreUnit.PIECE, rules=[_rule(StorePricingRuleType.DIMENSION_COMBINATION, config)])
    with pytest.raises(PricingError) as error:
        calculate_quote(
            product,
            _request(product, quantity=1, pilaster=PilasterInput(width_cm="30", thickness_cm="4", length_m="1")),
        )
    assert error.value.code == "PRICE_NOT_CONFIGURED"


def test_freight_routes_remain():
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/health" in paths
    assert any(path.startswith("/api/v1/cargos") for path in paths)
    assert any(path.startswith("/api/v1/auth") for path in paths)
    assert any(path.startswith("/api/v1/driver-offers") for path in paths)
    assert "/api/store/products/{slug}" in paths
    pricing = [route for route in app.routes if getattr(route, "path", "") == "/api/store/pricing/calculate"]
    assert pricing
    assert "POST" in (pricing[0].methods or set())
    versions = sorted(path.name for path in Path("alembic/versions").glob("*.py"))
    assert "a1b7c3d9e4f2_store_catalog_tables.py" in versions
    assert not any("drop" in name and "users" in name for name in versions)


@pytest.fixture()
def store_client(tmp_path: Path):
    database = tmp_path / "pricing.sqlite"
    url = f"sqlite+aiosqlite:///{database}"

    async def prepare() -> None:
        engine = create_async_engine(url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.run_sync(seed_store_categories)
        await engine.dispose()

    asyncio.run(prepare())
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_client_supplied_price_is_ignored(store_client):
    client, factory = store_client

    async def insert() -> tuple[int, str]:
        async with factory() as session:
            category = await session.scalar(select(StoreCategory).where(StoreCategory.slug == "tayyor-mahsulotlar"))
            assert category is not None
            product = StoreProduct(
                category_id=category.id,
                name="Tayyor karniz",
                slug="tayyor-karniz",
                sku="STK-9",
                images=[],
                product_type=StoreProductType.READY_MADE,
                unit=StoreUnit.PIECE,
                is_active=True,
                selling_price="1500.50",
                available_quantity=3,
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product.id, product.slug

    product_id, slug = asyncio.run(insert())
    response = client.post(
        "/api/store/pricing/calculate",
        json={
            "product_id": product_id,
            "quantity": 2,
            "client_price": "1",
            "total": "1",
            "quoted_total": "1",
            "unit_price": "1",
            "trim": {"size": "S", "components": ["cornice"]},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == "3001.00"
    assert body["unit_price"] == "1500.50"
    assert body["currency"] == "UZS"
    assert "1.00" not in {body["total"], body["unit_price"], body["subtotal"]}

    detail = client.get(f"/api/store/products/{slug}")
    assert detail.status_code == 200
    assert detail.json()["selling_price"] == "1500.50"
    assert detail.json()["available_quantity"] == 3
    assert "pricing_rules" not in detail.json()

    stock = client.post("/api/store/pricing/calculate", json={"product_id": product_id, "quantity": 4, "client_price": "0"})
    assert stock.status_code == 409
    assert stock.json()["detail"]["code"] == "INSUFFICIENT_STOCK"

    async def remaining() -> int:
        async with factory() as session:
            product = await session.get(StoreProduct, product_id)
            assert product is not None
            return int(product.available_quantity or 0)

    assert asyncio.run(remaining()) == 3

    missing = client.post("/api/store/pricing/calculate", json={"product_id": 999999, "quantity": 1})
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "PRODUCT_NOT_FOUND"

    zero = client.post("/api/store/pricing/calculate", json={"product_id": product_id, "quantity": 0})
    assert zero.status_code == 422
    assert zero.status_code != 500


def test_pricing_endpoint_rejects_bad_input_and_inactive_rules(store_client):
    client, factory = store_client

    async def insert() -> tuple[int, int]:
        async with factory() as session:
            pilaster = await session.scalar(select(StoreCategory).where(StoreCategory.slug == "pilastrlar"))
            shohona = await session.scalar(select(StoreCategory).where(StoreCategory.slug == "shohona-karnizlar"))
            assert pilaster is not None and shohona is not None
            inactive_product = StoreProduct(
                category_id=pilaster.id,
                name="Pilastr",
                slug="pilastr-model",
                images=[],
                product_type=StoreProductType.MADE_TO_ORDER,
                unit=StoreUnit.PIECE,
                is_active=True,
                selling_price=None,
                available_quantity=None,
            )
            active_product = StoreProduct(
                category_id=pilaster.id,
                name="Pilastr faol",
                slug="pilastr-faol",
                images=[],
                product_type=StoreProductType.MADE_TO_ORDER,
                unit=StoreUnit.PIECE,
                is_active=True,
                selling_price=None,
                available_quantity=None,
            )
            manual = StoreProduct(
                category_id=shohona.id,
                name="Shohona",
                slug="shohona-model",
                images=[],
                product_type=StoreProductType.MADE_TO_ORDER,
                unit=StoreUnit.PIECE,
                is_active=True,
                selling_price=None,
                available_quantity=None,
            )
            session.add_all([inactive_product, active_product, manual])
            await session.flush()
            session.add(
                StorePricingRule(
                    product_id=inactive_product.id,
                    rule_type=StorePricingRuleType.DIMENSION_COMBINATION,
                    name="Yopiq narx",
                    config={"meter_prices": {"30": {"4": "99999"}}},
                    is_active=False,
                )
            )
            session.add(
                StorePricingRule(
                    product_id=active_product.id,
                    rule_type=StorePricingRuleType.DIMENSION_COMBINATION,
                    name="Faol narx",
                    config={"meter_prices": {"30": {"4": "10000"}}},
                    is_active=True,
                )
            )
            session.add(
                StorePricingRule(
                    product_id=manual.id,
                    rule_type=StorePricingRuleType.MANUAL_QUOTE,
                    name="Qo‘lda",
                    config={"price": "50000"},
                    is_active=True,
                )
            )
            await session.commit()
            return inactive_product.id, active_product.id, manual.id

    pilaster_id, active_id, shohona_id = asyncio.run(insert())
    inactive = client.post(
        "/api/store/pricing/calculate",
        json={
            "product_id": pilaster_id,
            "quantity": 1,
            "pilaster": {"width_cm": "30", "thickness_cm": "4", "length_m": "2"},
            "client_price": "99999",
        },
    )
    assert inactive.status_code == 409
    assert inactive.json()["detail"]["code"] == "PRICE_NOT_CONFIGURED"

    negative = client.post(
        "/api/store/pricing/calculate",
        json={
            "product_id": active_id,
            "quantity": 1,
            "pilaster": {"width_cm": "30", "thickness_cm": "4", "length_m": "-2"},
        },
    )
    assert negative.status_code == 422
    assert negative.json()["detail"]["code"] == "INVALID_INPUT"

    manual = client.post(
        "/api/store/pricing/calculate",
        json={
            "product_id": shohona_id,
            "quantity": 1,
            "client_price": "0",
            "total": "0",
            "shohona": {"length_m": "4", "coating": True, "model": "gul"},
        },
    )
    assert manual.status_code == 200
    payload = manual.json()
    assert payload["status"] == "MANUAL_QUOTE_REQUIRED"
    assert payload["requires_manual_quote"] is True
    assert payload["total"] is None
    assert payload["unit_price"] is None
    assert payload["subtotal"] is None
    assert payload["components"] == []
    assert payload["currency"] == "UZS"
