import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token
from app.crud.store_admin import create_store_admin
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.store import StoreProduct
from app.services.store_admin import images as image_service

STORE_SECRET = "store-admin-test-secret-value"
EMAIL = "admin@penodecor.test"
PASSWORD = "correct-password"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
WEBP = b"RIFF" + b"\x18\x00\x00\x00" + b"WEBP" + b"VP8 " + b"\x00" * 8


def test_image_module_does_not_touch_cargo_storage():
    text = Path("app/services/store_admin/images.py").read_text(encoding="utf-8")
    cargos = Path("app/api/v1/cargos.py").read_text(encoding="utf-8")
    assert "app.api.v1" not in text
    assert "media/cargos" not in text
    assert "store/products" not in cargos
    assert "store/categories" not in cargos


def test_image_routes_require_store_admin(image_client):
    client, _factory = image_client
    jpeg = {"file": ("a.jpg", JPEG, "image/jpeg")}
    missing = client.post("/api/store/admin/products/1/images", files=jpeg)
    assert missing.status_code == 401
    assert _delete(client, "/api/store/admin/products/1/images", None, "/media/store/products/1/a.jpg").status_code == 401
    assert client.post("/api/store/admin/categories/1/image", files=jpeg).status_code == 401
    assert _delete(client, "/api/store/admin/categories/1/image", None, "/media/store/categories/1/a.jpg").status_code == 401
    garbage = client.post(
        "/api/store/admin/products/1/images",
        headers={"Authorization": "Bearer not-a-token"},
        files={"file": ("a.jpg", JPEG, "image/jpeg")},
    )
    assert garbage.status_code == 401
    assert garbage.json()["detail"] == missing.json()["detail"]
    freight = client.post(
        "/api/store/admin/categories/1/image",
        headers={"Authorization": f"Bearer {create_access_token('1')}"},
        files={"file": ("a.jpg", JPEG, "image/jpeg")},
    )
    assert freight.status_code == 401


def test_uploads_real_images_and_rejects_fakes(image_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = image_client
    headers = _login(client, factory, monkeypatch)
    category_id, product_id = _create_product(client, headers)

    jpeg = _upload_product(client, headers, product_id, "evil/../../x.jpg", JPEG, "text/plain")
    assert jpeg.status_code == 200
    jpeg_path = jpeg.json()["images"][0]
    assert jpeg_path.startswith(f"/media/store/products/{product_id}/")
    assert jpeg_path.endswith(".jpg")
    assert ".." not in jpeg_path
    jpeg_file = _disk_path(jpeg_path)
    assert jpeg_file.is_file()
    assert jpeg_file.read_bytes() == JPEG
    assert _inside_owner(jpeg_file, "products", product_id)

    png = _upload_product(client, headers, product_id, "rasm.png", PNG, "image/png")
    webp = _upload_product(client, headers, product_id, "rasm.webp", WEBP, "image/webp")
    assert png.status_code == webp.status_code == 200
    assert png.json()["images"][1].endswith(".png")
    assert webp.json()["images"][2].endswith(".webp")

    category = _upload_category(client, headers, category_id, "kat.png", PNG, "image/png")
    assert category.status_code == 200
    category_path = category.json()["image"]
    assert category_path.startswith(f"/media/store/categories/{category_id}/")
    assert _disk_path(category_path).is_file()

    fake = _upload_product(client, headers, product_id, "rasm.jpg", b"this is not an image", "image/jpeg")
    assert fake.status_code == 422
    assert fake.json()["detail"]["code"] == "INVALID_IMAGE"
    assert len(client.get(f"/api/store/admin/products/{product_id}", headers=headers).json()["images"]) == 3

    missing_product = _upload_product(client, headers, 99999, "a.jpg", JPEG, "image/jpeg")
    missing_category = _upload_category(client, headers, 99999, "a.png", PNG, "image/png")
    assert missing_product.status_code == missing_category.status_code == 404

    monkeypatch.setattr(settings, "MAX_PHOTO_SIZE_MB", 1)
    oversized = JPEG + b"\x00" * (1024 * 1024)
    too_big = _upload_product(client, headers, product_id, "big.jpg", oversized, "image/jpeg")
    assert too_big.status_code == 413
    assert too_big.json()["detail"]["code"] == "FILE_TOO_LARGE"
    assert len(client.get(f"/api/store/admin/products/{product_id}", headers=headers).json()["images"]) == 3


def test_product_image_limit_and_owned_delete(image_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = image_client
    headers = _login(client, factory, monkeypatch)
    category_id, first_id = _create_product(client, headers, slug="birinchi", name="Birinchi")
    second = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": "Ikkinchi",
            "slug": "ikkinchi",
            "category_id": category_id,
            "product_type": "made_to_order",
            "unit": "piece",
        },
    )
    assert second.status_code == 201
    second_id = second.json()["id"]
    other_category = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": "Boshqa", "slug": "boshqa"},
    ).json()["id"]

    paths = []
    for index in range(8):
        uploaded = _upload_product(client, headers, first_id, f"{index}.png", PNG, "image/png")
        assert uploaded.status_code == 200
        paths = uploaded.json()["images"]
    assert len(paths) == 8
    ninth = _upload_product(client, headers, first_id, "9.png", PNG, "image/png")
    assert ninth.status_code == 409
    assert ninth.json()["detail"]["code"] == "IMAGE_LIMIT"
    assert len(list(_owner_dir("products", first_id).iterdir())) == 8

    other = _upload_product(client, headers, second_id, "b.png", PNG, "image/png")
    other_path = other.json()["images"][0]
    stolen = _delete(client, f"/api/store/admin/products/{first_id}/images", headers, other_path)
    assert stolen.status_code == 404
    assert _disk_path(other_path).is_file()
    assert other_path not in client.get(f"/api/store/admin/products/{first_id}", headers=headers).json()["images"]

    removed = _delete(client, f"/api/store/admin/products/{first_id}/images", headers, paths[0])
    assert removed.status_code == 200
    assert paths[0] not in removed.json()["images"]
    assert not _disk_path(paths[0]).exists()
    assert _disk_path(paths[1]).is_file()

    first_category = _upload_category(client, headers, category_id, "a.png", PNG, "image/png")
    second_category = _upload_category(client, headers, other_category, "b.webp", WEBP, "image/webp")
    first_image = first_category.json()["image"]
    second_image = second_category.json()["image"]
    cross = _delete(client, f"/api/store/admin/categories/{category_id}/image", headers, second_image)
    assert cross.status_code == 404
    assert _disk_path(second_image).is_file()
    assert client.get("/api/store/admin/categories", headers=headers).json()["items"]
    deleted = _delete(client, f"/api/store/admin/categories/{category_id}/image", headers, first_image)
    assert deleted.status_code == 200
    assert deleted.json()["image"] is None
    assert not _disk_path(first_image).exists()
    assert _disk_path(second_image).is_file()
    assert _delete(client, "/api/store/admin/categories/99999/image", headers, second_image).status_code == 404


def test_failed_store_keeps_database_and_files_together(image_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = image_client
    headers = _login(client, factory, monkeypatch)
    category_id, product_id = _create_product(client, headers)
    original = _upload_category(client, headers, category_id, "old.png", PNG, "image/png")
    original_path = original.json()["image"]
    assert _disk_path(original_path).is_file()

    async def fail_commit(_db) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(image_service, "_commit_image", fail_commit)
    failed = _upload_product(client, headers, product_id, "a.jpg", JPEG, "image/jpeg")
    assert failed.status_code == 503
    assert failed.json()["detail"]["code"] == "IMAGE_STORE_FAILED"
    assert client.get(f"/api/store/admin/products/{product_id}", headers=headers).json()["images"] == []
    product_dir = _owner_dir("products", product_id)
    assert not product_dir.exists() or list(product_dir.iterdir()) == []
    failed_category = _upload_category(client, headers, category_id, "new.png", PNG, "image/png")
    assert failed_category.status_code == 503
    assert _disk_path(original_path).is_file()
    stored = {item["image"] for item in client.get("/api/store/admin/categories", headers=headers).json()["items"]}
    assert original_path in stored


def test_unlink_failure_restores_database_record(image_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = image_client
    headers = _login(client, factory, monkeypatch)
    _category_id, product_id = _create_product(client, headers)
    uploaded = _upload_product(client, headers, product_id, "a.png", PNG, "image/png")
    public = uploaded.json()["images"][0]
    disk = _disk_path(public)

    def fail_unlink(_path: Path) -> None:
        raise OSError("disk busy")

    monkeypatch.setattr(image_service, "_unlink", fail_unlink)
    rejected = _delete(client, f"/api/store/admin/products/{product_id}/images", headers, public)
    assert rejected.status_code == 503
    assert disk.is_file()
    assert client.get(f"/api/store/admin/products/{product_id}", headers=headers).json()["images"] == [public]


def test_catalog_edit_cannot_replace_uploaded_image(image_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = image_client
    headers = _login(client, factory, monkeypatch)
    category_id, product_id = _create_product(client, headers, slug="ochiq-rom", name="Ochiq rom")
    uploaded = _upload_product(client, headers, product_id, "rasm.jpg", JPEG, "image/jpeg")
    assert uploaded.status_code == 200
    product_image = uploaded.json()["images"][0]
    category = _upload_category(client, headers, category_id, "kat.png", PNG, "image/png")
    assert category.status_code == 200
    category_image = category.json()["image"]

    cargo = "/media/cargos/9/secret.jpg"
    rejected_product = client.patch(
        f"/api/store/admin/products/{product_id}",
        headers=headers,
        json={"name": "Almashtirilgan", "images": [cargo]},
    )
    rejected_category = client.patch(
        f"/api/store/admin/categories/{category_id}",
        headers=headers,
        json={"name": "Almashtirilgan", "image": cargo},
    )
    assert rejected_product.status_code == rejected_category.status_code == 422

    stored_product = client.get(f"/api/store/admin/products/{product_id}", headers=headers).json()
    stored_category = client.get("/api/store/admin/categories", headers=headers).json()["items"][0]
    assert stored_product["name"] == "Ochiq rom"
    assert stored_product["images"] == [product_image]
    assert stored_category["name"] == "Ochiq rom"
    assert stored_category["image"] == category_image
    assert _disk_path(product_image).is_file()
    assert _disk_path(category_image).is_file()

    public_product = client.get("/api/store/products/ochiq-rom")
    public_category = client.get("/api/store/categories/ochiq-rom")
    assert public_product.status_code == public_category.status_code == 200
    assert public_product.json()["images"] == [product_image]
    assert public_category.json()["image"] == category_image
    assert "cargos" not in public_product.text
    assert "cargos" not in public_category.text

    renamed = client.patch(
        f"/api/store/admin/products/{product_id}",
        headers=headers,
        json={"description": "Saqlangan rasm"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["images"] == [product_image]

    removed_product = _delete(client, f"/api/store/admin/products/{product_id}/images", headers, product_image)
    removed_category = _delete(client, f"/api/store/admin/categories/{category_id}/image", headers, category_image)
    assert removed_product.status_code == removed_category.status_code == 200
    assert removed_product.json()["images"] == []
    assert removed_category.json()["image"] is None
    assert client.get("/api/store/products/ochiq-rom").json()["images"] == []
    assert client.get("/api/store/categories/ochiq-rom").json()["image"] is None
    assert not _disk_path(product_image).exists()
    assert not _disk_path(category_image).exists()


def test_symlink_outside_media_root_is_not_deleted(image_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = image_client
    headers = _login(client, factory, monkeypatch)
    _category_id, product_id = _create_product(client, headers)
    secret = Path(settings.MEDIA_ROOT) / "cargos" / "secret.jpg"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_bytes(b"cargo-secret")
    name = "a" * 32 + ".jpg"
    owner = _owner_dir("products", product_id)
    owner.mkdir(parents=True, exist_ok=True)
    link = owner / name
    link.symlink_to(secret)
    public = f"/media/store/products/{product_id}/{name}"
    asyncio.run(_set_images(factory, product_id, [public]))

    rejected = _delete(client, f"/api/store/admin/products/{product_id}/images", headers, public)
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "IMAGE_NOT_OWNED"
    assert secret.read_bytes() == b"cargo-secret"
    assert link.is_symlink()
    assert client.get(f"/api/store/admin/products/{product_id}", headers=headers).json()["images"] == [public]


@pytest.fixture()
def image_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    media = tmp_path / "media"
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(media))
    database = tmp_path / "store-admin-images.sqlite"
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
    return {"Authorization": f"Bearer {token}"}


async def _add_admin(factory) -> None:
    async with factory() as session:
        await create_store_admin(session, email=EMAIL, full_name="Do‘kon admin", password=PASSWORD)


def _create_product(client: TestClient, headers: dict[str, str], *, slug: str = "rom", name: str = "Rom") -> tuple[int, int]:
    category = client.post(
        "/api/store/admin/categories",
        headers=headers,
        json={"name": name, "slug": slug},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]
    product = client.post(
        "/api/store/admin/products",
        headers=headers,
        json={
            "name": name,
            "slug": slug,
            "category_id": category_id,
            "product_type": "made_to_order",
            "unit": "piece",
        },
    )
    assert product.status_code == 201
    return category_id, product.json()["id"]


def _delete(client: TestClient, url: str, headers: dict[str, str] | None, image: str):
    kwargs = {"json": {"image": image}}
    if headers is not None:
        kwargs["headers"] = headers
    return client.request("DELETE", url, **kwargs)


def _upload_product(client, headers, product_id: int, filename: str, payload: bytes, content_type: str):
    return client.post(
        f"/api/store/admin/products/{product_id}/images",
        headers=headers,
        files={"file": (filename, payload, content_type)},
    )


def _upload_category(client, headers, category_id: int, filename: str, payload: bytes, content_type: str):
    return client.post(
        f"/api/store/admin/categories/{category_id}/image",
        headers=headers,
        files={"file": (filename, payload, content_type)},
    )


def _disk_path(public: str) -> Path:
    assert public.startswith("/media/")
    return Path(settings.MEDIA_ROOT).resolve() / public.removeprefix("/media/")


def _owner_dir(kind: str, owner_id: int) -> Path:
    return Path(settings.MEDIA_ROOT).resolve() / "store" / kind / str(owner_id)


def _inside_owner(path: Path, kind: str, owner_id: int) -> bool:
    return path.resolve().is_relative_to(_owner_dir(kind, owner_id).resolve())


async def _set_images(factory, product_id: int, images: list[str]) -> None:
    async with factory() as session:
        product = await session.get(StoreProduct, product_id)
        assert product is not None
        product.images = images
        await session.commit()
