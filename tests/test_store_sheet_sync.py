import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.store.router import get_sheet_source
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.store import StoreCategory, StorePricingRule, StoreProduct
from app.models.store_enums import StorePricingRuleType, StoreProductType, StoreUnit
from app.models.store_settings import StorePriceSettings
from app.schemas.store_pricing import PricingCalculateRequest, RoundColumnInput, ShohonaInput, TrimInput
from app.services.store_pricing.adjustment import adjusted_selling_amount
from app.services.store_pricing.errors import PricingError
from app.services.store_pricing.service import calculate_quote
from app.services.store_sheets.errors import SheetUnavailable, SheetValidationError
from app.services.store_sheets.google_source import GoogleSheetSource
from app.services.store_sheets.layout import (
    CORNICE_COLUMNS,
    CORNICE_SHEET,
    PILASTER_COLUMNS,
    PILASTER_SHEET,
    READY_COLUMNS,
    READY_SHEET,
    ROM_COLUMNS,
    ROM_SHEET,
    ROUND_COLUMNS,
    ROUND_SHEET,
    SETTINGS_COLUMNS,
    SETTINGS_SHEET,
    SHEET_COLUMNS,
    SHEETS_SCOPE,
    SHOHONA_COLUMNS,
    SHOHONA_SHEET,
)
from app.services.store_sheets.parse import parse_workbook
from app.services.store_sheets.repository import settings_are_stale
from app.services.store_sheets.sync import MemorySheetSource, _lock
from app.store.catalog_seed import seed_store_categories

TOKEN = "sync-token-secret"


def _category(slug: str, category_id: int, parent: StoreCategory | None = None) -> StoreCategory:
    category = StoreCategory(
        id=category_id,
        name=slug,
        slug=slug,
        sort_order=0,
        is_active=True,
        parent_id=None if parent is None else parent.id,
    )
    category.parent = parent
    category.pricing_rules = []
    return category


def _request(product: StoreProduct, **kwargs: object) -> PricingCalculateRequest:
    quantity = int(kwargs.pop("quantity", 1))
    return PricingCalculateRequest(product_id=product.id or 1, quantity=quantity, **kwargs)  # type: ignore[arg-type]


def _trim_product(extra: dict | None = None) -> StoreProduct:
    parent = _category("rom-va-eshik", 1)
    category = _category("deraza-romlari", 2, parent)
    config = {
        "family": "trim_set",
        "opening": "window",
        "sizes": {"M": {"cornice": "10000", "jamb": "8000", "sill": "5000"}},
        "addons": {},
    }
    config.update(extra or {})
    return _memory_product(category, StoreUnit.SET, StorePricingRuleType.FIXED, config)


def _round_product() -> StoreProduct:
    parent = _category("yumaloq-ustunlar", 3)
    category = _category("yumaloq-ustun-tanasi", 4, parent)
    config = {
        "family": "round_column",
        "meter_price": "10000",
        "coating_multiplier": "1.5",
        "capitals": {},
        "bases": {},
    }
    return _memory_product(category, StoreUnit.METER, StorePricingRuleType.ROUND_COLUMN, config, product_id=11)


def _shohona_product() -> StoreProduct:
    category = _category("shohona-karnizlar", 5)
    return _memory_product(
        category,
        StoreUnit.METER,
        StorePricingRuleType.MANUAL_QUOTE,
        {"family": "shohona"},
        product_id=12,
    )


def _ready_product() -> StoreProduct:
    category = _category("tayyor-mahsulotlar", 6)
    product = StoreProduct(
        id=13,
        category_id=category.id,
        name="Tayyor",
        slug="tayyor",
        sku="STK-9",
        images=[],
        product_type=StoreProductType.READY_MADE,
        unit=StoreUnit.PIECE,
        is_active=True,
        selling_price=Decimal("1500.50"),
        available_quantity=3,
    )
    product.category = category
    product.pricing_rules = []
    return product


def _memory_product(
    category: StoreCategory,
    unit: StoreUnit,
    rule_type: StorePricingRuleType,
    config: dict,
    product_id: int = 10,
) -> StoreProduct:
    product = StoreProduct(
        id=product_id,
        category_id=category.id,
        name="Model",
        slug=f"model-{product_id}",
        images=[],
        product_type=StoreProductType.MADE_TO_ORDER,
        unit=unit,
        is_active=True,
        selling_price=None,
        available_quantity=None,
    )
    product.category = category
    product.pricing_rules = [
        StorePricingRule(id=product_id, rule_type=rule_type, name="Narx", config=config, is_active=True)
    ]
    return product


def test_old_sheet_configuration_is_marked_stale(monkeypatch: pytest.MonkeyPatch):
    now = datetime(2026, 10, 2, tzinfo=timezone.utc)
    old = StorePriceSettings(
        id=1,
        global_price_adjustment_percent=Decimal("0"),
        currency="UZS",
        status="ok",
        stale=False,
        last_success_at=now - timedelta(hours=2),
    )
    monkeypatch.setattr(settings, "STORE_SHEETS_SPREADSHEET_ID", "sheet")
    monkeypatch.setattr(settings, "STORE_SHEETS_CREDENTIALS_FILE", "account.json")
    monkeypatch.setattr(settings, "STORE_SHEETS_STALE_AFTER_SECONDS", 60)
    assert settings_are_stale(old, now=now) is True
    fresh = StorePriceSettings(
        id=1,
        global_price_adjustment_percent=Decimal("10"),
        currency="UZS",
        status="ok",
        stale=False,
        last_success_at=now,
    )
    assert settings_are_stale(fresh, now=now) is False
    monkeypatch.setattr(settings, "STORE_SHEETS_SPREADSHEET_ID", "")
    assert settings_are_stale(old, now=now) is False


def test_percent_applies_once_from_the_base_price():
    base = Decimal("500000")
    assert adjusted_selling_amount(base, Decimal("0")) == Decimal("500000.00")
    assert adjusted_selling_amount(base, Decimal("10")) == Decimal("550000.00")
    assert adjusted_selling_amount(base, Decimal("-10")) == Decimal("450000.00")
    assert adjusted_selling_amount(Decimal("1.00"), Decimal("2.5")) == Decimal("1.03")
    with pytest.raises(PricingError):
        adjusted_selling_amount(base, Decimal("-100"))
    with pytest.raises(PricingError):
        adjusted_selling_amount(Decimal("-1"), Decimal("10"))


def test_adjustment_does_not_compound_or_touch_cost_or_coating():
    trim = _trim_product(extra={"manufacturing_cost": "1000", "cost_price": "2000"})
    request = _request(trim, trim=TrimInput(size="M", components=["cornice", "jamb", "sill"]))
    first = calculate_quote(trim, request, adjustment_percent=Decimal("10"))
    second = calculate_quote(trim, request, adjustment_percent=Decimal("10"))
    assert first.subtotal == "23000.00"
    assert first.total == second.total == "25300.00"
    assert [line.amount for line in first.components] == ["10000.00", "8000.00", "5000.00"]
    assert trim.pricing_rules[0].config["manufacturing_cost"] == "1000"
    assert trim.pricing_rules[0].config["cost_price"] == "2000"
    assert first.applied["global_price_adjustment_percent"] == "10"
    assert "manufacturing_cost" not in first.applied

    plain = calculate_quote(
        _round_product(),
        _request(
            _round_product(),
            round_column=RoundColumnInput(existing_diameter_cm="20", final_diameter_cm="25", height_m="2", coating=False),
            quantity=2,
        ),
        adjustment_percent=Decimal("10"),
    )
    coated = calculate_quote(
        _round_product(),
        _request(
            _round_product(),
            round_column=RoundColumnInput(existing_diameter_cm="20", final_diameter_cm="25", height_m="2", coating=True),
            quantity=2,
        ),
        adjustment_percent=Decimal("10"),
    )
    assert plain.total == "44000.00"
    assert "coating_multiplier" not in plain.applied
    assert coated.subtotal == "60000.00"
    assert coated.components[0].amount == "60000.00"
    assert coated.total == "66000.00"
    assert coated.applied["coating_multiplier"] == "1.5"
    assert coated.applied["global_price_adjustment_percent"] == "10"


def test_shohona_and_ready_stock_do_not_invent_prices():
    shohona = _shohona_product()
    quote = calculate_quote(
        shohona,
        _request(shohona, shohona=ShohonaInput(length_m="2", size_note="en 40")),
        adjustment_percent=Decimal("10"),
    )
    assert quote.total is None
    assert quote.unit_price is None
    assert quote.requires_manual_quote is True
    assert quote.applied["global_price_adjustment_percent"] == "10"
    assert "base_total" not in quote.applied

    ready = _ready_product()
    priced = calculate_quote(ready, _request(ready, quantity=2), adjustment_percent=Decimal("10"))
    assert priced.subtotal == "3001.00"
    assert priced.total == "3301.10"
    assert priced.unit_price == "1650.55"
    assert ready.available_quantity == 3
    assert ready.selling_price == Decimal("1500.50")
    with pytest.raises(PricingError) as error:
        calculate_quote(ready, _request(ready, quantity=4), adjustment_percent=Decimal("10"))
    assert error.value.code == "INSUFFICIENT_STOCK"
    assert ready.available_quantity == 3


def test_invalid_sheet_rows_are_rejected_before_activation():
    with pytest.raises(SheetValidationError):
        parse_workbook(_workbook(percent="-100"))
    with pytest.raises(SheetValidationError):
        parse_workbook(_workbook(percent="chegirma"))
    negative = _workbook()
    price_column = negative[ROM_SHEET][0].index("cornice_price")
    negative[ROM_SHEET][1][price_column] = "-10"
    with pytest.raises(SheetValidationError):
        parse_workbook(negative)
    floated = _workbook()
    floated[ROM_SHEET][1][price_column] = 10.0  # type: ignore[index]
    with pytest.raises(SheetValidationError):
        parse_workbook(floated)
    overlap = _workbook()
    overlap[ROUND_SHEET].append(
        ["ustun-1", "Silindr", "10000", "1.5", "oddiy", "25", "30", "5000", "", "", "", "", "true"]
    )
    overlap[ROUND_SHEET].append(
        ["ustun-1", "Silindr", "10000", "1.5", "oddiy", "28", "35", "7000", "", "", "", "", "true"]
    )
    with pytest.raises(SheetValidationError) as error:
        parse_workbook(overlap)
    assert "ustma-ust" in error.value.message
    missing = _workbook()
    del missing[SETTINGS_SHEET]
    with pytest.raises(SheetValidationError):
        parse_workbook(missing)


def test_google_source_does_not_call_network_or_write(tmp_path: Path):
    source_text = Path("app/services/store_sheets/google_source.py").read_text(encoding="utf-8")
    assert "batchUpdate" not in source_text
    assert "values.update" not in source_text
    assert SHEETS_SCOPE.endswith("/spreadsheets.readonly")
    delays: list[float] = []
    calls: list[str] = []

    def opener(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> tuple[int, bytes]:
        calls.append(url)
        return 503, b'{"private_key":"SUPERSECRET"}'

    source = GoogleSheetSource(
        spreadsheet_id="spreadsheet-id",
        credentials_file="unused.json",
        opener=opener,
        sleeper=delays.append,
    )
    with pytest.raises(SheetUnavailable) as failure:
        source._request("GET", "https://sheets.googleapis.com/example", {}, None)
    assert len(calls) == 3
    assert delays == [0.4, 0.8]
    assert "private_key" not in str(failure.value)
    assert "SUPERSECRET" not in str(failure.value)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    account = tmp_path / "account.json"
    account.write_text(
        json.dumps({"client_email": "sheet@example.iam.gserviceaccount.com", "private_key": pem.decode()}),
        encoding="utf-8",
    )
    seen: list[str] = []

    def local_opener(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> tuple[int, bytes]:
        seen.append(url)
        if "oauth2.googleapis.com" in url:
            return 200, b'{"access_token":"ya29.local-test-token"}'
        return 200, b'{"values":[["key","value"]]}'

    reader = GoogleSheetSource(
        spreadsheet_id="spreadsheet-id",
        credentials_file=str(account),
        opener=local_opener,
        sleeper=lambda _delay: None,
    )
    tables = reader.fetch()
    assert set(tables) == set(SHEET_COLUMNS)
    assert all("batchUpdate" not in url and "values:batchUpdate" not in url for url in seen)
    assert not any("BEGIN PRIVATE" in url or "private_key" in url for url in seen)
    missing = GoogleSheetSource(spreadsheet_id="spreadsheet-id", credentials_file=str(tmp_path / "missing.json"))
    with pytest.raises(SheetUnavailable) as missing_error:
        missing.fetch()
    assert "private_key" not in str(missing_error.value)


def test_sheet_contract_and_migration_do_not_touch_freight():
    router = Path("app/api/store/router.py").read_text(encoding="utf-8")
    assert "get_current_admin" not in router
    assert "get_current_user" not in router
    migration = Path("alembic/versions/b7e2c9a4d1f0_store_price_settings.py").read_text(encoding="utf-8")
    upgrade, downgrade = migration.split("def downgrade")
    assert "store_price_settings" in upgrade
    assert "op.drop_table" not in upgrade
    assert "users" not in upgrade
    assert "cargos" not in upgrade
    assert 'op.drop_table("store_price_settings")' in downgrade
    assert "users" not in downgrade
    assert "store_products" not in downgrade


def test_sync_requires_store_token_and_hides_secrets(sheet_client, monkeypatch: pytest.MonkeyPatch):
    client, _factory = sheet_client
    closed = client.get("/api/store/pricing/sync-status")
    assert closed.status_code == 503
    assert "private_key" not in closed.text
    monkeypatch.setattr(settings, "STORE_SHEETS_SYNC_TOKEN", TOKEN)
    denied = client.post("/api/store/pricing/sync", headers={"Authorization": "Bearer wrong-token"})
    assert denied.status_code == 401
    assert TOKEN not in denied.text
    assert "private_key" not in denied.text
    status = client.get("/api/store/pricing/sync-status", headers=_auth())
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "never"
    assert "spreadsheet" not in body
    assert TOKEN not in status.text


def test_valid_sheet_updates_base_prices_and_bad_sheet_keeps_them(sheet_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = sheet_client
    monkeypatch.setattr(settings, "STORE_SHEETS_SYNC_TOKEN", TOKEN)
    asyncio.run(_seed(factory))
    source = MemorySheetSource(_workbook(percent="10"))
    app.dependency_overrides[get_sheet_source] = lambda: source

    calls_before_page = source.calls
    assert client.get("/api/store/products/tayyor-1").status_code == 200
    assert source.calls == calls_before_page

    synced = client.post("/api/store/pricing/sync", headers=_auth())
    assert synced.status_code == 200
    assert synced.json()["updated_products"] == 7
    assert source.calls == 1
    _assert_base_prices(factory, ready="500000.00", stock="1500.50", percent=Decimal("10"))
    _assert_quotes(client, factory, percent="10")

    source.tables = _workbook(percent="-10")
    again = client.post("/api/store/pricing/sync", headers=_auth())
    assert again.status_code == 200
    _assert_base_prices(factory, ready="500000.00", stock="1500.50", percent=Decimal("-10"))
    ready_id = asyncio.run(_product_id(factory, "tayyor-1"))
    discounted = client.post("/api/store/pricing/calculate", json={"product_id": ready_id, "quantity": 1})
    assert discounted.json()["total"] == "450000.00"
    assert discounted.json()["subtotal"] == "500000.00"

    source.tables = _workbook(percent="0")
    restored = client.post("/api/store/pricing/sync", headers=_auth())
    assert restored.status_code == 200
    original = client.post("/api/store/pricing/calculate", json={"product_id": ready_id, "quantity": 1})
    assert original.json()["total"] == "500000.00"
    assert original.json()["applied"]["global_price_adjustment_percent"] == "0"

    unknown = _workbook(percent="5")
    unknown[READY_SHEET].append(["yoq-mahsulot", "STK-X", "10", "1", "true"])
    source.tables = unknown
    missing_product = client.post("/api/store/pricing/sync", headers=_auth())
    assert missing_product.status_code == 409
    _assert_base_prices(factory, ready="500000.00", stock="1500.50", percent=Decimal("0"))

    bad = _workbook(percent="25")
    bad[ROM_SHEET][1][bad[ROM_SHEET][0].index("cornice_price")] = "-1"
    source.tables = bad
    rejected = client.post("/api/store/pricing/sync", headers=_auth())
    assert rejected.status_code == 409
    assert "private_key" not in rejected.text
    _assert_base_prices(factory, ready="500000.00", stock="1500.50", percent=Decimal("0"))
    kept = client.post("/api/store/pricing/calculate", json={"product_id": ready_id, "quantity": 1})
    assert kept.json()["total"] == "500000.00"

    source.error = RuntimeError("private_key SUPERSECRET spreadsheet-id")
    unavailable = client.post("/api/store/pricing/sync", headers=_auth())
    assert unavailable.status_code == 503
    assert "SUPERSECRET" not in unavailable.text
    assert "private_key" not in unavailable.text
    _assert_base_prices(factory, ready="500000.00", stock="1500.50", percent=Decimal("0"))
    calls_before_calculate = source.calls
    stale = client.post("/api/store/pricing/calculate", json={"product_id": ready_id, "quantity": 1})
    assert source.calls == calls_before_calculate
    assert stale.json()["total"] == "500000.00"
    assert "Oxirgi tekshirilgan narx ishlatilmoqda." in stale.json()["warnings"]
    state = client.get("/api/store/pricing/sync-status", headers=_auth())
    assert state.status_code == 200
    assert state.json()["stale"] is True
    assert state.json()["status"] == "error"
    assert "SUPERSECRET" not in state.text
    assert "private_key" not in state.text
    assert TOKEN not in state.text

    assert _lock.acquire(blocking=False)
    try:
        busy = client.post("/api/store/pricing/sync", headers=_auth())
        assert busy.status_code == 409
        assert busy.json()["detail"]["code"] == "SYNC_IN_PROGRESS"
    finally:
        _lock.release()
    _assert_base_prices(factory, ready="500000.00", stock="1500.50", percent=Decimal("0"))


def test_ready_sync_updates_price_without_stock_or_product_active(sheet_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = sheet_client
    monkeypatch.setattr(settings, "STORE_SHEETS_SYNC_TOKEN", TOKEN)
    asyncio.run(_seed(factory))
    source = MemorySheetSource(_workbook(percent="10"))
    app.dependency_overrides[get_sheet_source] = lambda: source

    synced = client.post("/api/store/pricing/sync", headers=_auth())
    assert synced.status_code == 200
    asyncio.run(_set_ready_flags(factory, "tayyor-1", active=False, quantity=7))

    tables = _workbook(percent="10")
    tables[READY_SHEET][1] = ["tayyor-1", "STK-1", "750000", "1", "true"]
    rom_active = tables[ROM_SHEET][0].index("is_active")
    tables[ROM_SHEET][1][rom_active] = "false"
    source.tables = tables
    updated = client.post("/api/store/pricing/sync", headers=_auth())
    assert updated.status_code == 200
    state = asyncio.run(_ready_boundary(factory))
    assert state["price"] == Decimal("750000.00")
    assert state["quantity"] == 7
    assert state["product_active"] is False
    assert state["rule_active"] is False
    assert state["rom_product_active"] is True
    assert state["percent"] == Decimal("10")
    assert state["status"] == "ok"
    assert state["last_success_at"] is not None

    mismatch = _workbook(percent="25")
    mismatch[READY_SHEET][1] = ["tayyor-1", "STK-OTHER", "1", "0", "false"]
    source.tables = mismatch
    rejected = client.post("/api/store/pricing/sync", headers=_auth())
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "SHEET_VALIDATION_FAILED"
    assert "SKU mos emas" in rejected.json()["detail"]["message"]
    kept = asyncio.run(_ready_boundary(factory))
    assert kept["price"] == Decimal("750000.00")
    assert kept["quantity"] == 7
    assert kept["product_active"] is False
    assert kept["rule_active"] is False
    assert kept["rom_product_active"] is True
    assert kept["percent"] == Decimal("10")
    assert kept["last_success_at"] == state["last_success_at"]
    assert kept["status"] == "error"


@pytest.fixture()
def sheet_client(tmp_path: Path):
    database = tmp_path / "sheets.sqlite"
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


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def _workbook(percent: str = "10") -> dict[str, list[list[str]]]:
    return {
        SETTINGS_SHEET: [
            list(SETTINGS_COLUMNS),
            ["global_price_adjustment_percent", percent],
            ["currency", "UZS"],
            ["updated_at", "2026-10-02T10:00:00Z"],
        ],
        ROM_SHEET: [
            list(ROM_COLUMNS),
            ["rom-1", "Klassik", "window", "M", "10000", "8000", "5000", "", "2000", "", "kalvak", "3000", "", "", "true"],
        ],
        PILASTER_SHEET: [
            list(PILASTER_COLUMNS),
            ["pilastr-1", "Klassik", "30", "4", "10000", "klassik", "7000", "oddiy", "4000", "true"],
        ],
        ROUND_SHEET: [
            list(ROUND_COLUMNS),
            ["ustun-1", "Silindr", "10000", "1.5", "", "", "", "", "", "", "", "", "true"],
        ],
        CORNICE_SHEET: [
            list(CORNICE_COLUMNS),
            ["karniz-1", "Klassik", "25", "30000", "true"],
        ],
        SHOHONA_SHEET: [
            list(SHOHONA_COLUMNS),
            ["shohona-1", "Gul", "Individual o‘lcham", "balandlik va en", "true"],
        ],
        READY_SHEET: [
            list(READY_COLUMNS),
            ["tayyor-1", "STK-1", "500000", "3", "true"],
            ["tayyor-2", "STK-2", "1500.50", "3", "true"],
        ],
    }


async def _seed(factory) -> None:
    async with factory() as session:
        categories = {row.slug: row.id for row in (await session.scalars(select(StoreCategory))).all()}
        session.add_all(
            [
                _made("Rom", "rom-1", categories["deraza-romlari"], StoreUnit.SET),
                _made("Pilastr", "pilastr-1", categories["pilastr-tana"], StoreUnit.METER),
                _made("Ustun", "ustun-1", categories["yumaloq-ustun-tanasi"], StoreUnit.METER),
                _made("Karniz", "karniz-1", categories["shift-karnizi"], StoreUnit.METER),
                _made("Shohona", "shohona-1", categories["shohona-karnizlar"], StoreUnit.METER),
                _ready_row("Tayyor", "tayyor-1", "STK-1", categories["tayyor-mahsulotlar"], "100.00", 1, "tannarx 1000"),
                _ready_row("Kichik", "tayyor-2", "STK-2", categories["tayyor-mahsulotlar"], "100.00", 9, "tannarx 2000"),
                _made("Tashqari", "tashqari-rom", categories["deraza-romlari"], StoreUnit.SET),
            ]
        )
        await session.flush()
        outside = await session.scalar(select(StoreProduct).where(StoreProduct.slug == "tashqari-rom"))
        session.add(
            StorePricingRule(
                product_id=outside.id,
                rule_type=StorePricingRuleType.FIXED,
                name="Eski",
                config={"family": "trim_set", "manufacturing_cost": "1000", "cost_price": "2000", "sizes": {"S": {"cornice": "111.00"}}},
                is_active=True,
            )
        )
        await session.commit()


def _made(name: str, slug: str, category_id: int, unit: StoreUnit) -> StoreProduct:
    return StoreProduct(
        category_id=category_id,
        name=name,
        slug=slug,
        images=[],
        product_type=StoreProductType.MADE_TO_ORDER,
        unit=unit,
        is_active=True,
        selling_price=None,
        available_quantity=None,
    )


def _ready_row(name: str, slug: str, sku: str, category_id: int, price: str, quantity: int, description: str) -> StoreProduct:
    return StoreProduct(
        category_id=category_id,
        name=name,
        slug=slug,
        sku=sku,
        description=description,
        images=[],
        product_type=StoreProductType.READY_MADE,
        unit=StoreUnit.PIECE,
        is_active=True,
        selling_price=Decimal(price),
        available_quantity=quantity,
    )


def _assert_base_prices(factory, *, ready: str, stock: str, percent: Decimal) -> None:
    async def read() -> None:
        async with factory() as session:
            first = await session.scalar(select(StoreProduct).where(StoreProduct.slug == "tayyor-1"))
            second = await session.scalar(select(StoreProduct).where(StoreProduct.slug == "tayyor-2"))
            outside = await session.scalar(select(StoreProduct).where(StoreProduct.slug == "tashqari-rom"))
            rule = await session.scalar(select(StorePricingRule).where(StorePricingRule.product_id == outside.id))
            rom = await session.scalar(select(StoreProduct).where(StoreProduct.slug == "rom-1"))
            rom_rule = await session.scalar(select(StorePricingRule).where(StorePricingRule.product_id == rom.id))
            settings_row = await session.get(StorePriceSettings, 1)
            assert Decimal(str(first.selling_price)) == Decimal(ready)
            assert first.available_quantity == 1
            assert first.is_active is True
            assert first.description == "tannarx 1000"
            assert first.name == "Tayyor"
            assert Decimal(str(second.selling_price)) == Decimal(stock)
            assert second.available_quantity == 9
            assert second.is_active is True
            assert second.description == "tannarx 2000"
            assert rule.config["manufacturing_cost"] == "1000"
            assert rule.config["cost_price"] == "2000"
            assert rule.config["sizes"]["S"]["cornice"] == "111.00"
            assert rom_rule.config["sizes"]["M"]["cornice"] == "10000.00"
            assert "manufacturing_cost" not in rom_rule.config
            assert Decimal(str(settings_row.global_price_adjustment_percent)) == percent

    asyncio.run(read())


async def _set_ready_flags(factory, slug: str, *, active: bool, quantity: int) -> None:
    async with factory() as session:
        product = await session.scalar(select(StoreProduct).where(StoreProduct.slug == slug))
        assert product is not None
        product.is_active = active
        product.available_quantity = quantity
        await session.commit()


async def _ready_boundary(factory) -> dict:
    async with factory() as session:
        ready = await session.scalar(select(StoreProduct).where(StoreProduct.slug == "tayyor-1"))
        rom = await session.scalar(select(StoreProduct).where(StoreProduct.slug == "rom-1"))
        rom_rule = await session.scalar(select(StorePricingRule).where(StorePricingRule.product_id == rom.id))
        settings_row = await session.get(StorePriceSettings, 1)
        assert ready is not None and rom is not None and rom_rule is not None and settings_row is not None
        return {
            "price": Decimal(str(ready.selling_price)),
            "quantity": ready.available_quantity,
            "product_active": ready.is_active,
            "rule_active": rom_rule.is_active,
            "rom_product_active": rom.is_active,
            "percent": Decimal(str(settings_row.global_price_adjustment_percent)),
            "status": settings_row.status,
            "last_success_at": settings_row.last_success_at,
        }


async def _product_id(factory, slug: str) -> int:
    async with factory() as session:
        product = await session.scalar(select(StoreProduct).where(StoreProduct.slug == slug))
        return int(product.id)


def _assert_quotes(client: TestClient, factory, *, percent: str) -> None:
    ids = asyncio.run(_ids_from_factory(factory))
    rom = client.post(
        "/api/store/pricing/calculate",
        json={"product_id": ids["rom-1"], "quantity": 1, "trim": {"size": "M", "components": ["cornice", "jamb", "sill"]}},
    )
    assert rom.status_code == 200
    rom_body = rom.json()
    assert rom_body["subtotal"] == "23000.00"
    assert rom_body["total"] == "25300.00"
    assert [item["amount"] for item in rom_body["components"]] == ["10000.00", "8000.00", "5000.00"]
    assert rom_body["applied"]["global_price_adjustment_percent"] == percent
    assert TOKEN not in rom.text

    pilaster = client.post(
        "/api/store/pricing/calculate",
        json={
            "product_id": ids["pilastr-1"],
            "quantity": 1,
            "pilaster": {"width_cm": "30", "thickness_cm": "4", "length_m": "2"},
        },
    )
    assert pilaster.json()["subtotal"] == "20000.00"
    assert pilaster.json()["total"] == "22000.00"
    missing = client.post(
        "/api/store/pricing/calculate",
        json={
            "product_id": ids["pilastr-1"],
            "quantity": 1,
            "pilaster": {"width_cm": "30", "thickness_cm": "5", "length_m": "2"},
        },
    )
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "PRICE_NOT_CONFIGURED"

    column = client.post(
        "/api/store/pricing/calculate",
        json={
            "product_id": ids["ustun-1"],
            "quantity": 2,
            "round_column": {
                "existing_diameter_cm": "20",
                "final_diameter_cm": "25",
                "height_m": "2",
                "coating": True,
            },
        },
    )
    column_body = column.json()
    assert column_body["components"][0]["amount"] == "60000.00"
    assert column_body["subtotal"] == "60000.00"
    assert column_body["total"] == "66000.00"
    assert column_body["applied"]["coating_multiplier"] == "1.5"
    assert column_body["applied"]["global_price_adjustment_percent"] == "10"

    cornice = client.post(
        "/api/store/pricing/calculate",
        json={"product_id": ids["karniz-1"], "quantity": 1, "cornice": {"width_cm": "50", "length_m": "2", "coating": False}},
    )
    assert cornice.json()["subtotal"] == "120000.00"
    assert cornice.json()["total"] == "132000.00"
    assert "coating_multiplier" not in cornice.json()["applied"]

    shohona = client.post(
        "/api/store/pricing/calculate",
        json={"product_id": ids["shohona-1"], "quantity": 1, "shohona": {"length_m": "2", "size_note": "en 40"}},
    )
    assert shohona.json()["total"] is None
    assert shohona.json()["requires_manual_quote"] is True

    stock = client.post("/api/store/pricing/calculate", json={"product_id": ids["tayyor-2"], "quantity": 2})
    assert stock.json()["subtotal"] == "3001.00"
    assert stock.json()["total"] == "3301.10"
    too_many = client.post("/api/store/pricing/calculate", json={"product_id": ids["tayyor-2"], "quantity": 10})
    assert too_many.status_code == 409
    assert too_many.json()["detail"]["code"] == "INSUFFICIENT_STOCK"


async def _ids_from_factory(factory) -> dict[str, int]:
    async with factory() as session:
        rows = (await session.scalars(select(StoreProduct))).all()
        return {row.slug: int(row.id) for row in rows}
