import asyncio
from datetime import timedelta
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token
from app.crud.store_admin import StoreAdminWriteError, create_store_admin
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.store_admin import StoreAdmin
from app.services.store_admin.tokens import STORE_ADMIN_AUDIENCE, STORE_ADMIN_ISSUER, STORE_ADMIN_TOKEN_HOURS

STORE_SECRET = "store-admin-test-secret-value"
EMAIL = "admin@penodecor.test"
PASSWORD = "correct-password"
LOGIN_FAILED = "Email yoki parol noto‘g‘ri."


def test_migration_only_adds_store_admins():
    versions = {path.name for path in Path("alembic/versions").glob("*.py")}
    assert "c4e8a1b7d2f3_store_admins.py" in versions
    text = Path("alembic/versions/c4e8a1b7d2f3_store_admins.py").read_text(encoding="utf-8")
    upgrade, downgrade = text.split("def downgrade")
    assert 'down_revision: Union[str, None] = "b7e2c9a4d1f0"' in text
    assert 'op.create_table(\n        "store_admins"' in upgrade
    assert "users" not in upgrade
    assert "op.drop_table" not in upgrade
    assert 'op.drop_table("store_admins")' in downgrade
    assert "users" not in downgrade


def test_freight_auth_files_are_unchanged_for_store_admin():
    deps = Path("app/api/deps.py").read_text(encoding="utf-8")
    freight_script = Path("scripts/create_admin.py").read_text(encoding="utf-8")
    freight_jwt = Path("app/core/security.py").read_text(encoding="utf-8")
    store_script = Path("scripts/create_store_admin.py").read_text(encoding="utf-8")
    assert "store_admins" not in deps
    assert "STORE_ADMIN" not in deps
    assert "get_current_store_admin" not in deps
    assert "store_admins" not in freight_script
    assert "STORE_ADMIN" not in freight_script
    assert "penodecor-store" not in freight_jwt
    assert "STORE_ADMIN_JWT_SECRET" not in freight_jwt
    assert "app.models.user" not in store_script
    assert "get_current_admin" not in store_script
    assert "is_admin" not in store_script
    assert "create_admin" not in store_script


def test_store_secret_must_differ_from_freight_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "STORE_ADMIN_JWT_SECRET", settings.SECRET_KEY)
    with TestClient(app) as client:
        response_login = client.post("/api/store/admin/login", json={"email": EMAIL, "password": PASSWORD})
    assert response_login.status_code == 503
    assert settings.SECRET_KEY not in response_login.text
    assert PASSWORD not in response_login.text


def test_login_hides_unknown_email_and_rejects_bad_tokens(admin_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = admin_client
    monkeypatch.setattr(settings, "STORE_ADMIN_JWT_SECRET", STORE_SECRET)
    asyncio.run(_add_admin(factory))

    missing = client.get("/api/store/admin/me")
    assert missing.status_code == 401

    garbage = client.get("/api/store/admin/me", headers={"Authorization": "Bearer not-a-token"})
    assert garbage.status_code == 401
    assert garbage.json()["detail"] == missing.json()["detail"]

    unknown = client.post("/api/store/admin/login", json={"email": "nobody@penodecor.test", "password": PASSWORD})
    wrong = client.post("/api/store/admin/login", json={"email": EMAIL, "password": "wrong-password"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"] == LOGIN_FAILED
    assert EMAIL not in unknown.text

    freight = create_access_token("1")
    rejected = client.get("/api/store/admin/me", headers=_bearer(freight))
    assert rejected.status_code == 401

    logged_in = client.post("/api/store/admin/login", json={"email": EMAIL.upper(), "password": PASSWORD})
    assert logged_in.status_code == 200
    body = logged_in.json()
    assert body["token_type"] == "bearer"
    assert "password" not in body
    assert STORE_SECRET not in logged_in.text
    token = body["access_token"]
    claims = jwt.decode(token, STORE_SECRET, algorithms=["HS256"], audience=STORE_ADMIN_AUDIENCE, issuer=STORE_ADMIN_ISSUER)
    assert claims["iss"] == "penodecor-store"
    assert claims["aud"] == "penodecor-store"
    assert claims["exp"] - claims["iat"] == int(timedelta(hours=STORE_ADMIN_TOKEN_HOURS).total_seconds())

    me = client.get("/api/store/admin/me", headers=_bearer(token))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    assert "password_hash" not in me.json()

    freight_admin = client.post(
        "/api/v1/admin/users/1/subscription/extend",
        headers=_bearer(token),
        json={"days": 30},
    )
    assert freight_admin.status_code == 401


def test_inactive_store_admin_is_forbidden(admin_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = admin_client
    monkeypatch.setattr(settings, "STORE_ADMIN_JWT_SECRET", STORE_SECRET)
    asyncio.run(_add_admin(factory))
    token = client.post("/api/store/admin/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    asyncio.run(_deactivate(factory))

    login = client.post("/api/store/admin/login", json={"email": EMAIL, "password": PASSWORD})
    assert login.status_code == 403
    assert PASSWORD not in login.text

    me = client.get("/api/store/admin/me", headers=_bearer(token))
    assert me.status_code == 403

    wrong = client.post("/api/store/admin/login", json={"email": EMAIL, "password": "wrong-password"})
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == LOGIN_FAILED


def test_create_store_admin_stores_argon2_hash(admin_client):
    _client, factory = admin_client
    asyncio.run(_add_admin(factory, email="Second@Penodecor.test", full_name="Ikkinchi"))

    async def read() -> None:
        async with factory() as session:
            admin = await session.scalar(select(StoreAdmin).where(StoreAdmin.email == "second@penodecor.test"))
            assert admin is not None
            assert admin.password_hash != PASSWORD
            assert admin.password_hash.startswith("$argon2")

    asyncio.run(read())
    with pytest.raises(StoreAdminWriteError):
        asyncio.run(_add_admin(factory, email="second@penodecor.test", full_name="Ikkinchi"))


@pytest.fixture()
def admin_client(tmp_path: Path):
    database = tmp_path / "store-admin.sqlite"
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


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _add_admin(factory, *, email: str = EMAIL, full_name: str = "Do‘kon admin") -> None:
    async with factory() as session:
        await create_store_admin(session, email=email, full_name=full_name, password=PASSWORD)


async def _deactivate(factory) -> None:
    async with factory() as session:
        admin = await session.scalar(select(StoreAdmin).where(StoreAdmin.email == EMAIL))
        assert admin is not None
        admin.is_active = False
        await session.commit()
