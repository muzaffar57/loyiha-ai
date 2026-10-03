"""Staging bazasida login hisoblagichini parallel tekshirish.

Ulanish manzili faqat STAGING_DATABASE_URL dan olinadi.
Sozlama obyekti va DATABASE_URL o‘qilmaydi.
To‘liq manzil terminalga chiqarilmaydi.

Ishlatish:
    STAGING_DATABASE_URL='postgresql://...' EXPECTED_STAGING_HOST='staging-host' \\
        python -m scripts.staging_login_throttle_check
"""
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.services.store_admin.login_throttle import LOGIN_FAILURE_LIMIT, LoginThrottled, consume_login_attempt

PARALLEL_KEY = "staging-parallel"
OTHER_KEY = "staging-other"
PARALLEL_CALLS = 30
TALLY_SQL = "SELECT client_key, failures FROM store_admin_login_throttles ORDER BY client_key"


def normalize_postgres_url(raw: str) -> str:
    """Ilova sozlamasidagi qoida: postgres va postgresql prefikslari asyncpg ga aylanadi."""
    text_url = raw.strip()
    if len(text_url) >= 2 and text_url[0] == text_url[-1] and text_url[0] in {'"', "'"}:
        text_url = text_url[1:-1].strip()
    if text_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + text_url[len("postgres://") :]
    if text_url.startswith("postgresql+asyncpg://"):
        return text_url
    if text_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + text_url[len("postgresql://") :]
    raise SystemExit("Qo‘llab-quvvatlanmaydigan PostgreSQL manzil formati. Engine yaratilmadi.")


def checked_engine_url(raw: str, expected_host: str) -> str:
    """Enginega beriladigan manzilni qaytaradi.

    Host mos kelmasa, funksiya engine yaratilishidan oldin to‘xtaydi.
    Qaytgan satr o‘zgartirilmasdan create_async_engine ga beriladi.
    """
    if not raw or not raw.strip():
        raise SystemExit("STAGING_DATABASE_URL yo‘q. Engine yaratilmadi.")
    if not expected_host or not expected_host.strip():
        raise SystemExit("EXPECTED_STAGING_HOST yo‘q. Engine yaratilmadi.")
    try:
        engine_url = normalize_postgres_url(raw)
        parsed = make_url(engine_url)
    except SystemExit:
        raise
    except ArgumentError:
        raise SystemExit("Ulanish manzili o‘qilmadi. Engine yaratilmadi.") from None
    except Exception:
        raise SystemExit("Ulanish manzili o‘qilmadi. Engine yaratilmadi.") from None
    host = parsed.host or ""
    database = parsed.database or ""
    print(f"host: {host}")
    print(f"database: {database}")
    if host.casefold() != expected_host.strip().casefold() or not database:
        raise SystemExit("host mos emas. Engine yaratilmadi.")
    confirmed = make_url(engine_url)
    if confirmed.host != host or confirmed.database != database:
        raise SystemExit("host mos emas. Engine yaratilmadi.")
    return engine_url


def build_engine(engine_url: str, factory=create_async_engine):
    return factory(engine_url, echo=False, hide_parameters=True, poolclass=NullPool)


def prepare(raw: str, expected_host: str, factory=create_async_engine):
    engine_url = checked_engine_url(raw, expected_host)
    return build_engine(engine_url, factory), engine_url


def redact(message: str, engine_url: str) -> str:
    try:
        parsed = make_url(engine_url)
        hidden = [engine_url, parsed.render_as_string(hide_password=False)]
        if parsed.password:
            hidden.append(parsed.password)
        if parsed.username:
            hidden.append(parsed.username)
        for secret in hidden:
            if secret:
                message = message.replace(secret, "***")
    except Exception:
        return "ulanish xatosi"
    return message


async def tally(session) -> list[tuple[str, int]]:
    result = await session.execute(text(TALLY_SQL))
    return [(str(key), int(failures)) for key, failures in result.all()]


async def _one(factory, key: str) -> str:
    async with factory() as session:
        try:
            await consume_login_attempt(session, key)
            return "ok"
        except LoginThrottled:
            return "throttled"


async def run(engine) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    parallel = await asyncio.gather(*[_one(factory, PARALLEL_KEY) for _ in range(PARALLEL_CALLS)])
    repeat = await _one(factory, PARALLEL_KEY)
    other = await _one(factory, OTHER_KEY)
    async with factory() as session:
        rows = await tally(session)
    print(f"parallel ok: {parallel.count('ok')}")
    print(f"parallel throttled: {parallel.count('throttled')}")
    print(f"repeat: {repeat}")
    print(f"other: {other}")
    for key, failures in rows:
        print(f"sql {key}: {failures}")
    print(f"kutilgan parallel ok: {LOGIN_FAILURE_LIMIT}")
    print("SQL: " + TALLY_SQL)


async def _guarded(engine_url: str) -> None:
    engine = build_engine(engine_url)
    try:
        await run(engine)
    finally:
        await engine.dispose()


def main() -> None:
    raw = os.environ.get("STAGING_DATABASE_URL", "")
    expected = os.environ.get("EXPECTED_STAGING_HOST", "")
    engine_url = checked_engine_url(raw, expected)
    try:
        asyncio.run(_guarded(engine_url))
    except Exception as exc:
        raise SystemExit(redact(str(exc), engine_url)) from None


if __name__ == "__main__":
    main()
