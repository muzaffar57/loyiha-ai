import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token
from app.crud.store_admin import create_store_admin
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.store import StorePricingRule, StoreProduct
from app.models.store_enums import StorePricingRuleType, StoreProductType, StoreUnit
from app.models.store_settings import StorePriceSettings

STORE_SECRET = "store-admin-test-secret-value"
EMAIL = "admin@penodecor.test"
PASSWORD = "correct-password"


def test_catalog_routes_require_store_admin_and_do_not_price(catalog_client):
    client, _factory = catalog_client
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/store/admin/categories" in paths
    assert "/api/store/admin/categories/{category_id}" in paths
    assert "/api/store/admin/products" in paths
    assert "/api/store/admin/products/{product_id}" in paths
    assert "/api/store/admin/products/{product_id}/stock" in paths
    assert "/api/store/admin/pricing/sync-status" in paths
    assert "/api/store/admin/pricing/sync" in paths
    assert not any("selling-price" in path or "pricing-rules" in path for path in paths)

    missing = client.get("/api/store/admin/categories")
    assert missing.status_code == 401
    assert client.post("/api/store/admin/products", json={"name": "X"}).status_code == 401
    garbage = client.get("/api/store/admin/products/1", headers={"Authorization": "Bearer not-a-token"})
    assert garbage.status_code == 401
    assert garbage.json()["detail"] == missing.json()["detail"]
    freight = client.get("/api/store/admin/categories", headers=_bearer(create_access_token("1")))
    assert freight.status_code == 401
    stock = client.patch("/api/store/admin/products/1/stock", json={"available_quantity": 1})
    assert stock.status_code == 401
    assert stock.json()["detail"] == missing.json()["detail"]


def test_admin_creates_category_and_hides_inactive_product(catalog_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = catalog_client
    headers = _login(client, factory, monkeypatch)

    created = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={
            "name": "Romlar",
            "slug": "romlar",
            "description": "Fasad romlari",
            "sort_order": 3,
            "is_active": True,
        },
    )
    assert created.status_code == 201
    category = created.json()
    assert category["slug"] == "romlar"
    assert category["sort_order"] == 3
    assert category["image"] is None

    edited = client.patch(
        f"/api/store/admin/categories/{category['id']}",
        headers=headers,
        json={"description": "Yangilangan", "sort_order": 1, "is_active": True},
    )
    assert edited.status_code == 200
    assert edited.json()["description"] == "Yangilangan"
    assert edited.json()["sort_order"] == 1

    hidden = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Yashirin rom",
            "slug": "yashirin-rom",
            "description": "Nofaol",
            "sku": "ROM-HIDE",
            "category_id": category["id"],
            "dimensions": "120 sm",
            "product_type": "made_to_order",
            "unit": "set",
            "is_active": False,
            "is_featured": True,
            "sort_order": 4,
        },
    )
    assert hidden.status_code == 201
    product = hidden.json()
    assert product["is_active"] is False
    assert product["selling_price"] is None
    assert product["images"] == []
    assert "pricing_rules" not in product

    visible = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Ochiq rom",
            "slug": "ochiq-rom",
            "category_id": category["id"],
            "product_type": "made_to_order",
            "unit": "meter",
            "is_active": True,
        },
    )
    assert visible.status_code == 201

    public_list = client.get("/api/store/products")
    assert public_list.status_code == 200
    slugs = [item["slug"] for item in public_list.json()["items"]]
    assert "yashirin-rom" not in slugs
    assert "ochiq-rom" in slugs
    assert client.get("/api/store/products/yashirin-rom").status_code == 404
    assert client.get("/api/store/products/ochiq-rom").status_code == 200

    admin_list = client.get("/api/store/admin/products", headers=headers)
    assert admin_list.status_code == 200
    admin_slugs = [item["slug"] for item in admin_list.json()["items"]]
    assert "yashirin-rom" in admin_slugs
    assert "ochiq-rom" in admin_slugs
    detail = client.get(f"/api/store/admin/products/{product['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["sku"] == "ROM-HIDE"


def test_duplicate_slug_and_unknown_category_are_rejected(catalog_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = catalog_client
    headers = _login(client, factory, monkeypatch)
    first = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": "Pilastr", "slug": "pilastr"},
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": "Boshqa", "slug": "pilastr"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "DUPLICATE_SLUG"

    missing_category = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Yo‘q kategoriya",
            "slug": "yoq-kategoriya",
            "category_id": 99999,
            "product_type": "made_to_order",
            "unit": "piece",
        },
    )
    assert missing_category.status_code == 404
    assert missing_category.json()["detail"]["code"] == "CATEGORY_NOT_FOUND"

    product = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Birinchi",
            "slug": "birinchi",
            "category_id": first.json()["id"],
            "product_type": "made_to_order",
            "unit": "piece",
        },
    )
    assert product.status_code == 201
    again = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Ikkinchi",
            "slug": "birinchi",
            "category_id": first.json()["id"],
            "product_type": "made_to_order",
            "unit": "piece",
        },
    )
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "DUPLICATE_SLUG"
    assert client.get("/api/store/admin/products/99999", headers=headers).status_code == 404
    assert client.patch("/api/store/admin/categories/99999", headers=headers, json={"name": "Yo‘q"}).status_code == 404
    assert client.patch("/api/store/admin/products/99999", headers=headers, json={"name": "Yo‘q"}).status_code == 404


def test_admin_api_cannot_change_price_rules_or_percent(catalog_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = catalog_client
    headers = _login(client, factory, monkeypatch)
    category_id = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": "Tayyor", "slug": "tayyor-admin"},
    ).json()["id"]
    ready = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Tayyor blok",
            "slug": "tayyor-blok",
            "sku": "TB-1",
            "category_id": category_id,
            "product_type": "ready_made",
            "unit": "piece",
            "is_active": False,
        },
    )
    assert ready.status_code == 201
    body = ready.json()
    assert body["selling_price"] is None
    assert body["is_active"] is False
    product_id = body["id"]
    blocked = client.patch(f"/api/store/admin/products/{product_id}", headers=headers, json={"is_active": True})
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "PRICE_OWNED_BY_SHEETS"
    asyncio.run(_seed_price(factory, product_id))

    payloads = [
        {"selling_price": "150000.00"},
        {"available_quantity": 9},
        {"global_price_adjustment_percent": "12.5"},
        {"pricing_rules": [{"rule_type": "fixed", "config": {"amount": "1"}}]},
        {"name": "Boshqa", "selling_price": "1.00"},
    ]
    for payload in payloads:
        rejected = client.patch(f"/api/store/admin/products/{product_id}", headers=headers, json=payload)
        assert rejected.status_code == 422, payload
    created = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Narxli",
            "slug": "narxli",
            "category_id": category_id,
            "product_type": "made_to_order",
            "unit": "piece",
            "selling_price": "10.00",
        },
    )
    assert created.status_code == 422

    renamed = client.patch(
        f"/api/store/admin/products/{product_id}",
        headers=headers,
        json={"name": "Tayyor blok yangi", "dimensions": "40x40"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Tayyor blok yangi"
    assert renamed.json()["selling_price"] == "15000.00"
    assert renamed.json()["available_quantity"] == 4

    locked = client.patch(f"/api/store/admin/products/{product_id}", headers=headers, json={"sku": "TB-2"})
    assert locked.status_code == 409
    assert locked.json()["detail"]["code"] == "SKU_LOCKED"
    opened = client.patch(f"/api/store/admin/products/{product_id}", headers=headers, json={"is_active": True})
    assert opened.status_code == 200
    assert opened.json()["is_active"] is True
    assert opened.json()["selling_price"] == "15000.00"

    snapshot = asyncio.run(_price_snapshot(factory, product_id))
    assert snapshot["selling_price"] == Decimal("15000.00")
    assert snapshot["available_quantity"] == 4
    assert snapshot["sku"] == "TB-1"
    assert snapshot["rules"] == 1
    assert snapshot["percent"] == Decimal("7.50")


def test_admin_stock_updates_ready_quantity_only(catalog_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = catalog_client
    headers = _login(client, factory, monkeypatch)
    category_id = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": "Ombor", "slug": "ombor"},
    ).json()["id"]
    ready = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Tayyor qoldiq",
            "slug": "tayyor-qoldiq",
            "sku": "STK-Q",
            "category_id": category_id,
            "product_type": "ready_made",
            "unit": "piece",
            "is_active": False,
        },
    )
    assert ready.status_code == 201
    product_id = ready.json()["id"]
    custom = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Buyurtma",
            "slug": "buyurtma",
            "category_id": category_id,
            "product_type": "made_to_order",
            "unit": "meter",
        },
    )
    assert custom.status_code == 201
    asyncio.run(_seed_price(factory, product_id))
    opened = client.patch(f"/api/store/admin/products/{product_id}", headers=headers, json={"is_active": True})
    assert opened.status_code == 200

    rejected = client.patch(
        f"/api/store/admin/products/{product_id}/stock",
        headers=headers,
        json={"available_quantity": 9, "selling_price": "1.00"},
    )
    assert rejected.status_code == 422
    negative = client.patch(
        f"/api/store/admin/products/{product_id}/stock",
        headers=headers,
        json={"available_quantity": -1},
    )
    assert negative.status_code == 422

    updated = client.patch(
        f"/api/store/admin/products/{product_id}/stock",
        headers=headers,
        json={"available_quantity": 2},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["available_quantity"] == 2
    assert body["selling_price"] == "15000.00"
    assert body["sku"] == "STK-Q"
    assert body["is_active"] is True

    public = client.get("/api/store/products/tayyor-qoldiq")
    assert public.status_code == 200
    assert public.json()["available_quantity"] == 2
    assert public.json()["selling_price"] == "15000.00"
    too_many = client.post("/api/store/pricing/calculate", json={"product_id": product_id, "quantity": 3})
    assert too_many.status_code == 409
    assert too_many.json()["detail"]["code"] == "INSUFFICIENT_STOCK"
    priced = client.post("/api/store/pricing/calculate", json={"product_id": product_id, "quantity": 2})
    assert priced.status_code == 200
    assert priced.json()["subtotal"] == "30000.00"
    assert priced.json()["total"] == "32250.00"

    blocked = client.patch(
        f"/api/store/admin/products/{custom.json()['id']}/stock",
        headers=headers,
        json={"available_quantity": 5},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "STOCK_NOT_READY"
    assert client.get(f"/api/store/admin/products/{custom.json()['id']}", headers=headers).json()["available_quantity"] is None
    assert client.patch("/api/store/admin/products/99999/stock", headers=headers, json={"available_quantity": 1}).status_code == 404

    snapshot = asyncio.run(_price_snapshot(factory, product_id))
    assert snapshot["selling_price"] == Decimal("15000.00")
    assert snapshot["available_quantity"] == 2
    assert snapshot["sku"] == "STK-Q"
    assert snapshot["rules"] == 1
    assert snapshot["percent"] == Decimal("7.50")


def test_catalog_write_rejects_unowned_image_paths(catalog_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = catalog_client
    headers = _login(client, factory, monkeypatch)
    cargo = "/media/cargos/1/secret.jpg"
    missing = "/media/store/yashirin.jpg"
    traversal = "/media/store/../../etc/passwd"

    anonymous = client.post(
        "/api/store/admin/categories",
        json={"name": "Yopiq", "slug": "yopiq", "image": cargo},
    )
    assert anonymous.status_code == 401

    rejected_category = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": "Romlar", "slug": "romlar", "image": cargo},
    )
    assert rejected_category.status_code == 422
    assert client.get("/api/store/admin/categories", headers=headers).json()["items"] == []

    created = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": "Romlar", "slug": "romlar", "is_active": True},
    )
    assert created.status_code == 201
    category = created.json()
    assert category["image"] is None
    renamed = client.patch(
        f"/api/store/admin/categories/{category['id']}",
        headers=headers,
        json={"name": "Buzilgan", "image": missing},
    )
    assert renamed.status_code == 422
    stored = client.get("/api/store/admin/categories", headers=headers).json()["items"][0]
    assert stored["name"] == "Romlar"
    assert stored["image"] is None
    assert client.patch(
        f"/api/store/admin/categories/{category['id']}",
        headers=headers,
        json={"image": None},
    ).status_code == 422

    for images in ([cargo], [missing], [traversal], []):
        rejected_product = client.post(
            "/api/store/admin/products",
            headers=headers,
            json={
                "name": "Mahsulot",
                "slug": "mahsulot",
                "category_id": category["id"],
                "product_type": "made_to_order",
                "unit": "piece",
                "images": images,
            },
        )
        assert rejected_product.status_code == 422
    assert client.get("/api/store/admin/products", headers=headers).json()["total"] == 0

    product = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Mahsulot",
            "slug": "mahsulot",
            "category_id": category["id"],
            "product_type": "made_to_order",
            "unit": "piece",
            "is_active": True,
        },
    )
    assert product.status_code == 201
    assert product.json()["images"] == []
    product_id = product.json()["id"]
    edited = client.patch(
        f"/api/store/admin/products/{product_id}",
        headers=headers,
        json={"name": "Buzilgan mahsulot", "images": [cargo]},
    )
    assert edited.status_code == 422
    current = client.get(f"/api/store/admin/products/{product_id}", headers=headers).json()
    assert current["name"] == "Mahsulot"
    assert current["images"] == []
    assert cargo not in client.get("/api/store/products/mahsulot").text
    assert client.get("/api/store/categories/romlar").json()["image"] is None

    kept = client.patch(
        f"/api/store/admin/products/{product_id}",
        headers=headers,
        json={"description": "Matn"},
    )
    assert kept.status_code == 200
    assert kept.json()["images"] == []
    assert kept.json()["description"] == "Matn"


def test_admin_sync_status_hides_sheet_secrets(catalog_client, monkeypatch: pytest.MonkeyPatch):
    client, _factory = catalog_client
    headers = _login(client, _factory, monkeypatch)
    monkeypatch.setattr(settings, "STORE_SHEETS_SYNC_TOKEN", "sheet-secret-value")
    missing = client.get("/api/store/admin/pricing/sync-status")
    assert missing.status_code == 401
    status = client.get("/api/store/admin/pricing/sync-status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "never"
    assert body["global_price_adjustment_percent"] == "0"
    assert "sheet-secret-value" not in status.text
    assert "spreadsheet" not in status.text.lower()
    assert "private_key" not in status.text
    token_route = client.post("/api/store/pricing/sync", headers=headers)
    assert token_route.status_code == 401
    assert "sheet-secret-value" not in token_route.text
    started = client.post("/api/store/admin/pricing/sync", headers=headers)
    assert started.status_code == 503
    assert "sheet-secret-value" not in started.text


@pytest.fixture()
def catalog_client(tmp_path: Path):
    database = tmp_path / "store-admin-catalog.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(prepare())
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _login(client: TestClient, factory, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(settings, "STORE_ADMIN_JWT_SECRET", STORE_SECRET)
    asyncio.run(_add_admin(factory))
    token = client.post("/api/store/admin/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    return _bearer(token)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _add_admin(factory) -> None:
    async with factory() as session:
        await create_store_admin(session, email=EMAIL, full_name="Do‘kon admin", password=PASSWORD)


async def _seed_price(factory, product_id: int) -> None:
    async with factory() as session:
        product = await session.get(StoreProduct, product_id)
        assert product is not None
        product.selling_price = Decimal("15000.00")
        product.available_quantity = 4
        session.add(
            StorePricingRule(
                product_id=product_id,
                category_id=None,
                rule_type=StorePricingRuleType.FIXED,
                name="Sinov qoidasi",
                config={"amount": "1000.00"},
                is_active=True,
            )
        )
        session.add(
            StorePriceSettings(
                id=1,
                global_price_adjustment_percent=Decimal("7.50"),
                currency="UZS",
                status="ok",
            )
        )
        await session.commit()


async def _price_snapshot(factory, product_id: int) -> dict:
    async with factory() as session:
        product = await session.get(StoreProduct, product_id)
        assert product is not None
        rules = int(await session.scalar(select(func.count()).select_from(StorePricingRule)) or 0)
        settings = await session.get(StorePriceSettings, 1)
        assert settings is not None
        return {
            "selling_price": Decimal(str(product.selling_price)),
            "available_quantity": product.available_quantity,
            "sku": product.sku,
            "rules": rules,
            "percent": Decimal(str(settings.global_price_adjustment_percent)),
        }
