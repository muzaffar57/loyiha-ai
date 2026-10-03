import asyncio
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base_class import Base
from app.models.store_admin_throttle import StoreAdminLoginThrottle  # noqa: F401
from app.services.store_admin.login_throttle import LOGIN_FAILURE_LIMIT, LoginThrottled, consume_login_attempt
from scripts.staging_login_throttle_check import (
    TALLY_SQL,
    build_engine,
    checked_engine_url,
    normalize_postgres_url,
    prepare,
    redact,
    tally,
)

SECRET = "stage-secret"
STAGING = f"postgresql://stage-user:{SECRET}@staging.internal:5432/auditdb"
PRODUCTION = "postgresql://prod-user:prod-secret@production.internal/logistics_db"


def test_script_does_not_read_settings_database_url():
    source = Path("scripts/staging_login_throttle_check.py").read_text(encoding="utf-8")
    assert "settings.DATABASE_URL" not in source
    assert "app.core.config" not in source
    assert "app.db.session" not in source
    assert 'os.environ.get("DATABASE_URL"' not in source
    assert 'os.environ["DATABASE_URL"]' not in source


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://stage-user:stage-secret@staging.internal:5432/auditdb", "postgresql+asyncpg://stage-user:stage-secret@staging.internal:5432/auditdb"),
        ("postgresql://stage-user:stage-secret@staging.internal:5432/auditdb", "postgresql+asyncpg://stage-user:stage-secret@staging.internal:5432/auditdb"),
        ("postgresql+asyncpg://stage-user:stage-secret@staging.internal:5432/auditdb?ssl=require", "postgresql+asyncpg://stage-user:stage-secret@staging.internal:5432/auditdb?ssl=require"),
        ('"postgresql://stage-user:stage-secret@staging.internal/auditdb"', "postgresql+asyncpg://stage-user:stage-secret@staging.internal/auditdb"),
    ],
)
def test_supported_postgres_urls_normalize_without_corrupting_scheme(raw: str, expected: str):
    assert normalize_postgres_url(raw) == expected
    assert "postgresqlql://" not in normalize_postgres_url(raw)


def test_checked_url_is_the_engine_url_and_settings_are_ignored(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setenv("DATABASE_URL", PRODUCTION)
    import app.core.config as config

    monkeypatch.setattr(config.settings, "DATABASE_URL", "postgresql+asyncpg://prod-user:prod-secret@production.internal/logistics_db")
    seen: dict[str, object] = {}

    def factory(url, **kwargs):
        seen["url"] = url
        seen["kwargs"] = kwargs
        return "engine-object"

    engine, engine_url = prepare(STAGING, "staging.internal", factory)
    assert engine == "engine-object"
    assert engine_url == "postgresql+asyncpg://stage-user:stage-secret@staging.internal:5432/auditdb"
    assert seen["url"] == engine_url
    assert seen["kwargs"] == {"echo": False, "hide_parameters": True, "poolclass": NullPool}
    assert "production.internal" not in str(seen["url"])
    output = capsys.readouterr().out
    assert "host: staging.internal" in output
    assert "database: auditdb" in output
    assert SECRET not in output
    assert "postgresql" not in output
    assert "production.internal" not in output


def test_host_mismatch_stops_before_engine(capsys: pytest.CaptureFixture[str]):
    def factory(url, **kwargs):
        raise AssertionError(url)

    with pytest.raises(SystemExit, match="Engine yaratilmadi"):
        prepare("postgresql://stage-user:stage-secret@staging.internal/auditdb", "production.internal", factory)
    output = capsys.readouterr().out
    assert "host: staging.internal" in output
    assert SECRET not in output
    assert "postgresql://" not in output


def test_password_containing_expected_host_does_not_bypass_check():
    raw = "postgresql://stage-user:staging.internal@production.internal/auditdb"
    with pytest.raises(SystemExit, match="Engine yaratilmadi"):
        checked_engine_url(raw, "staging.internal")


def test_unsupported_scheme_stops_before_engine():
    def factory(url, **kwargs):
        raise AssertionError(url)

    with pytest.raises(SystemExit, match="Engine yaratilmadi"):
        prepare("mysql://stage-user:stage-secret@staging.internal/auditdb", "staging.internal", factory)
    with pytest.raises(SystemExit, match="Engine yaratilmadi"):
        prepare("postgresql+psycopg://stage-user:stage-secret@staging.internal/auditdb", "staging.internal", factory)


def test_redact_removes_url_password_and_user():
    engine_url = normalize_postgres_url(STAGING)
    message = redact(f"could not connect to {engine_url}", engine_url)
    assert SECRET not in message
    assert "stage-user" not in message
    assert "staging.internal" not in message


def test_build_engine_receives_exact_checked_string():
    engine_url = checked_engine_url(STAGING, "STAGING.INTERNAL")
    seen: list[str] = []

    def factory(url, **kwargs):
        seen.append(url)
        return url

    assert build_engine(engine_url, factory) == engine_url
    assert seen == [engine_url]


def test_committed_counter_stays_visible_to_later_sql(tmp_path: Path):
    database = tmp_path / "throttle-visibility.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)

    async def scenario():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for _ in range(LOGIN_FAILURE_LIMIT):
                await consume_login_attempt(session, "staging-parallel")
        async with factory() as session:
            with pytest.raises(LoginThrottled):
                await consume_login_attempt(session, "staging-parallel")
        async with factory() as session:
            rows = await tally(session)
        await engine.dispose()
        return rows

    rows = asyncio.run(scenario())
    assert rows == [("staging-parallel", LOGIN_FAILURE_LIMIT)]
    assert "store_admin_login_throttles" in TALLY_SQL
