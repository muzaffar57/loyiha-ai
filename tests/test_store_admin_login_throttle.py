import asyncio
import contextvars
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import _TestClientTransport

from app.api.v1 import auth as freight_auth
from app.core.config import settings
from app.crud.store_admin import create_store_admin
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.store_admin.client_ip import UNKNOWN_CLIENT, client_key
from app.services.store_admin.login_throttle import LOGIN_FAILURE_LIMIT, LOGIN_WINDOW

_PEER: contextvars.ContextVar[str] = contextvars.ContextVar("store_admin_test_peer", default="198.51.100.10")

STORE_SECRET = "store-admin-test-secret-value"
EMAIL = "admin@penodecor.test"
PASSWORD = "correct-password"
LOGIN_FAILED = "Email yoki parol noto‘g‘ri."
THROTTLED = "Juda ko‘p muvaffaqiyatsiz urinish. Birozdan so‘ng qayta urinib ko‘ring."


def test_freight_login_is_not_throttled_by_store_admin():
    text = Path(freight_auth.__file__).read_text(encoding="utf-8")
    assert "login_throttle" not in text
    assert "STORE_ADMIN_TRUSTED_PROXIES" not in text


def test_missing_or_broken_client_address_stays_limited():
    class Bare:
        client = None
        headers: dict[str, str] = {}

    class Boom:
        @property
        def client(self):
            raise RuntimeError("peer missing")

        headers: dict[str, str] = {}

    assert client_key(Bare()) == UNKNOWN_CLIENT  # type: ignore[arg-type]
    assert client_key(Boom()) == UNKNOWN_CLIENT  # type: ignore[arg-type]


def test_five_failures_then_block_and_window_reopens(throttle_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = throttle_client
    clock = {"now": datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr("app.services.store_admin.login_throttle.utcnow", lambda: clock["now"])
    monkeypatch.setattr(settings, "STORE_ADMIN_TRUSTED_PROXIES", "")
    asyncio.run(_add_admin(factory))
    for _ in range(LOGIN_FAILURE_LIMIT):
        failed = _login(client, "198.51.100.10", EMAIL, "wrong-password")
        assert failed.status_code == 401
        assert failed.json()["detail"] == LOGIN_FAILED
        assert EMAIL not in failed.text
    unknown = _login(client, "198.51.100.10", "nobody@penodecor.test", PASSWORD)
    assert unknown.status_code == 429
    assert unknown.json()["detail"] == THROTTLED
    assert EMAIL not in unknown.text
    assert "nobody@penodecor.test" not in unknown.text
    assert int(unknown.headers["retry-after"]) > 0

    clock["now"] = clock["now"] + LOGIN_WINDOW + timedelta(seconds=1)
    reopened = _login(client, "198.51.100.10", EMAIL, "wrong-password")
    assert reopened.status_code == 401
    assert reopened.json()["detail"] == LOGIN_FAILED


def test_success_clears_counter_for_that_client_only(throttle_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = throttle_client
    monkeypatch.setattr(settings, "STORE_ADMIN_TRUSTED_PROXIES", "")
    asyncio.run(_add_admin(factory))
    for _ in range(3):
        assert _login(client, "198.51.100.20", EMAIL, "wrong-password").status_code == 401
    success = _login(client, "198.51.100.20", EMAIL, PASSWORD)
    assert success.status_code == 200
    assert success.json()["token_type"] == "bearer"
    assert EMAIL not in success.text

    for _ in range(LOGIN_FAILURE_LIMIT):
        assert _login(client, "198.51.100.20", EMAIL, "wrong-password").status_code == 401
    assert _login(client, "198.51.100.20", EMAIL, PASSWORD).status_code == 429
    other = _login(client, "198.51.100.21", EMAIL, "wrong-password")
    assert other.status_code == 401
    assert other.json()["detail"] == LOGIN_FAILED


def test_forwarded_header_is_ignored_unless_proxy_is_trusted(throttle_client, monkeypatch: pytest.MonkeyPatch):
    client, factory = throttle_client
    monkeypatch.setattr(settings, "STORE_ADMIN_TRUSTED_PROXIES", "not-a-proxy")
    asyncio.run(_add_admin(factory))
    for index in range(LOGIN_FAILURE_LIMIT):
        failed = _login(client, "198.51.100.30", EMAIL, "wrong-password", forwarded=f"203.0.113.{index + 1}")
        assert failed.status_code == 401
    blocked = _login(client, "198.51.100.30", EMAIL, "wrong-password", forwarded="203.0.113.99")
    assert blocked.status_code == 429
    other = _login(client, "198.51.100.31", EMAIL, "wrong-password", forwarded="203.0.113.99")
    assert other.status_code == 401

    monkeypatch.setattr(settings, "STORE_ADMIN_TRUSTED_PROXIES", "192.0.2.10")
    for _ in range(LOGIN_FAILURE_LIMIT):
        failed = _login(client, "192.0.2.10", EMAIL, "wrong-password", forwarded="1.2.3.4, 203.0.113.8")
        assert failed.status_code == 401
    assert _login(client, "192.0.2.10", EMAIL, PASSWORD, forwarded="203.0.113.8").status_code == 429
    spoofed_only = _login(client, "192.0.2.10", EMAIL, "wrong-password", forwarded="1.2.3.4")
    assert spoofed_only.status_code == 401
    garbage = _login(client, "192.0.2.10", "nobody@penodecor.test", PASSWORD, forwarded="not-an-ip, <bad>")
    assert garbage.status_code == 401
    assert "nobody@penodecor.test" not in garbage.text
    for _ in range(LOGIN_FAILURE_LIMIT - 1):
        assert _login(client, "192.0.2.10", EMAIL, "wrong-password", forwarded="%%%").status_code == 401
    assert _login(client, "192.0.2.10", EMAIL, PASSWORD, forwarded="").status_code == 429


@pytest.fixture()
def throttle_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "STORE_ADMIN_JWT_SECRET", STORE_SECRET)
    monkeypatch.setattr(settings, "STORE_ADMIN_TRUSTED_PROXIES", "")
    database = tmp_path / "store-admin-throttle.sqlite"
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
    _patch_testclient_peer(monkeypatch)
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _patch_testclient_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Starlette TestClient peer manzilini doim 'testclient' qiladi.

    Sinovda haqiqiy IP shu qatlamda scope ga yoziladi. Ishlab chiqarish kodi o‘zgarmaydi.
    """
    original = _TestClientTransport.handle_request

    def handle_request(self, request):
        app_callable = self.app
        address = _PEER.get()

        async def asgi(scope, receive, send):
            if scope.get("type") == "http":
                scope = dict(scope)
                scope["client"] = (address, 50000)
            await app_callable(scope, receive, send)

        self.app = asgi
        try:
            return original(self, request)
        finally:
            self.app = app_callable

    monkeypatch.setattr(_TestClientTransport, "handle_request", handle_request)


def _login(client: TestClient, address: str, email: str, password: str, forwarded: str | None = None):
    headers = {} if forwarded is None else {"X-Forwarded-For": forwarded}
    token = _PEER.set(address)
    try:
        return client.post("/api/store/admin/login", headers=headers, json={"email": email, "password": password})
    finally:
        _PEER.reset(token)


async def _add_admin(factory) -> None:
    async with factory() as session:
        await create_store_admin(session, email=EMAIL, full_name="Do‘kon admin", password=PASSWORD)
