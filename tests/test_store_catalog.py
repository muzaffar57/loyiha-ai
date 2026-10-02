import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.crud.store import contains_pattern, to_public_product
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.store import StoreCategory, StorePricingRule, StoreProduct
from app.models.store_enums import StorePricingRuleType, StoreProductType, StoreUnit
from app.schemas.store import StoreProductOut
from app.store.catalog_seed import SEED_CATEGORIES, seed_store_categories


def test_seed_slugs_are_unique():
    slugs = []
    for root in SEED_CATEGORIES:
        slugs.append(root["slug"])
        slugs.extend(child["slug"] for child in root["children"])
    assert len(slugs) == len(set(slugs))
    assert "tayyor-mahsulotlar" in slugs
    assert "rustovka" not in slugs


def test_search_pattern_escapes_wildcards():
    assert contains_pattern("100%") == "%100\\%%"
    assert contains_pattern("a_b") == "%a\\_b%"


def test_public_product_hides_made_to_order_price():
    product = StoreProduct(
        id=1,
        category_id=1,
        name="Rom",
        slug="rom",
        description=None,
        sku=None,
        images=["/media/rom.jpg"],
        product_type=StoreProductType.MADE_TO_ORDER,
        unit=StoreUnit.SET,
        is_active=True,
        is_featured=False,
        sort_order=0,
        dimensions="120 sm",
        selling_price=None,
        available_quantity=None,
    )
    product.category = StoreCategory(id=1, name="Rom", slug="rom-va-eshik", sort_order=0)
    public = to_public_product(product)
    assert public.selling_price is None
    assert public.available_quantity is None
    assert public.dimensions is None
    assert "pricing_rules" not in StoreProductOut.model_fields


def test_store_migration_leaves_freight_tables_alone():
    text = Path("alembic/versions/a1b7c3d9e4f2_store_catalog_tables.py").read_text(encoding="utf-8")
    assert 'down_revision: Union[str, None] = "e9a1b2c3d4e6"' in text
    assert "op.drop_table(\"users\")" not in text
    assert "op.drop_table(\"cargos\")" not in text
    assert "op.drop_table(\"driver_offers\")" not in text
    assert "store_categories" in text
    assert "seed_store_categories" in text


def test_freight_and_store_routes_both_exist():
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/health" in paths
    assert any(path.startswith("/api/v1/cargos") for path in paths)
    assert any(path.startswith("/api/v1/auth") for path in paths)
    assert "/api/store/categories" in paths
    assert "/api/store/products" in paths
    assert "/api/store/stock" in paths
    assert "/api/store/config" in paths


@pytest.fixture()
def store_client(tmp_path: Path):
    database = tmp_path / "store.sqlite"
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


def test_public_config_has_no_secrets(store_client):
    client, _factory = store_client
    response = client.get("/api/store/config")
    assert response.status_code == 200
    assert response.json() == {"currency": "UZS", "company_phone": None, "checkout_enabled": False}


def test_categories_are_seeded_without_products(store_client):
    client, _factory = store_client
    response = client.get("/api/store/categories")
    assert response.status_code == 200
    items = response.json()["items"]
    slugs = [item["slug"] for item in items]
    assert slugs[:6] == [
        "rom-va-eshik",
        "pilastrlar",
        "yumaloq-ustunlar",
        "shift-karnizlari",
        "shohona-karnizlar",
        "tayyor-mahsulotlar",
    ]
    rom = items[0]
    assert [child["slug"] for child in rom["children"]] == [
        "deraza-romlari",
        "eshik-bezaklari",
        "alohida-elementlar",
    ]
    products = client.get("/api/store/products")
    assert products.status_code == 200
    assert products.json()["total"] == 0
    stock = client.get("/api/store/stock")
    assert stock.status_code == 200
    assert stock.json()["items"] == []


def test_unknown_category_and_bad_page(store_client):
    client, _factory = store_client
    missing = client.get("/api/store/categories/yoq")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Kategoriya topilmadi."
    invalid = client.get("/api/store/products", params={"page": 0})
    assert invalid.status_code == 422


def test_inactive_product_and_stock_rules(store_client):
    client, factory = store_client

    async def insert() -> None:
        async with factory() as session:
            category = await session.scalar(select(StoreCategory).where(StoreCategory.slug == "tayyor-mahsulotlar"))
            rom = await session.scalar(select(StoreCategory).where(StoreCategory.slug == "rom-va-eshik"))
            assert category is not None and rom is not None
            session.add_all(
                [
                    StoreProduct(
                        category_id=rom.id,
                        name="Alpha rom",
                        slug="alpha-rom",
                        sku="ROM-1",
                        images=[],
                        product_type=StoreProductType.MADE_TO_ORDER,
                        unit=StoreUnit.SET,
                        is_active=True,
                        is_featured=True,
                        selling_price=None,
                        available_quantity=None,
                    ),
                    StoreProduct(
                        category_id=rom.id,
                        name="Yashirin",
                        slug="yashirin",
                        images=[],
                        product_type=StoreProductType.MADE_TO_ORDER,
                        unit=StoreUnit.PIECE,
                        is_active=False,
                        selling_price=None,
                        available_quantity=None,
                    ),
                    StoreProduct(
                        category_id=category.id,
                        name="Tayyor karniz",
                        slug="tayyor-karniz",
                        sku="STK-1",
                        images=["/media/karniz.jpg"],
                        product_type=StoreProductType.READY_MADE,
                        unit=StoreUnit.PIECE,
                        is_active=True,
                        dimensions="100x20 sm",
                        selling_price="1500.50",
                        available_quantity=3,
                    ),
                ]
            )
            session.add(
                StorePricingRule(
                    category_id=rom.id,
                    rule_type=StorePricingRuleType.PER_METER,
                    name="Metr bahosi",
                    config={},
                )
            )
            await session.commit()

    asyncio.run(insert())

    listing = client.get("/api/store/products", params={"q": "Alpha"})
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["selling_price"] is None
    assert "pricing_rules" not in body["items"][0]

    hidden = client.get("/api/store/products/yashirin")
    assert hidden.status_code == 404

    wildcard = client.get("/api/store/products", params={"q": "%"})
    assert wildcard.json()["total"] == 0

    stock = client.get("/api/store/stock")
    assert stock.status_code == 200
    stock_item = stock.json()["items"][0]
    assert stock_item["sku"] == "STK-1"
    assert stock_item["selling_price"] == "1500.50"
    assert stock_item["available_quantity"] == 3
    assert stock_item["dimensions"] == "100x20 sm"

    featured = client.get("/api/store/products", params={"featured": True})
    assert [item["slug"] for item in featured.json()["items"]] == ["alpha-rom"]

    async def reject_incomplete_stock() -> None:
        async with factory() as session:
            category = await session.scalar(select(StoreCategory).where(StoreCategory.slug == "tayyor-mahsulotlar"))
            session.add(
                StoreProduct(
                    category_id=category.id,
                    name="Narxsiz",
                    slug="narxsiz",
                    sku="STK-2",
                    images=[],
                    product_type=StoreProductType.READY_MADE,
                    unit=StoreUnit.PIECE,
                    selling_price=None,
                    available_quantity=1,
                )
            )
            await session.commit()

    with pytest.raises(IntegrityError):
        asyncio.run(reject_incomplete_stock())
