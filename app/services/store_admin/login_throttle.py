"""Do‘kon administratori login cheklovi.

Bir mijoz kaliti 15 daqiqa ichida 5 ta muvaffaqiyatsiz urinishdan keyin
vaqtincha to‘xtatiladi. Hisob umumiy bazada saqlanadi.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store_admin_throttle import StoreAdminLoginThrottle

LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_FAILURE_LIMIT = 5
_RETRY = "Juda ko‘p muvaffaqiyatsiz urinish. Birozdan so‘ng qayta urinib ko‘ring."


class LoginThrottled(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(_RETRY)
        self.retry_after = retry_after
        self.detail = _RETRY


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def consume_login_attempt(db: AsyncSession, client_key: str, *, now: datetime | None = None) -> None:
    """Urinishni parol tekshiruvidan oldin band qiladi.

    Limit allaqachon to‘lgan bo‘lsa, hisoblagich o‘zgarmaydi va LoginThrottled
    ko‘tariladi. Parallel so‘rovlar PostgreSQL da qator qulfi bilan navbatga turadi.
    """
    current = now or utcnow()
    for _ in range(2):
        try:
            await _consume_once(db, client_key, current)
            return
        except IntegrityError:
            await db.rollback()
    await _consume_once(db, client_key, current)


async def clear_login_failures(db: AsyncSession, client_key: str) -> None:
    row = await _row(db, client_key, lock=True)
    if row is None:
        return
    await db.delete(row)
    await db.commit()


async def _consume_once(db: AsyncSession, client_key: str, now: datetime) -> None:
    row = await _row(db, client_key, lock=True)
    if row is None:
        db.add(StoreAdminLoginThrottle(client_key=client_key, failures=1, window_started_at=now))
        await db.commit()
        return
    elapsed = now - _aware(row.window_started_at)
    if elapsed >= LOGIN_WINDOW:
        row.failures = 1
        row.window_started_at = now
        await db.commit()
        return
    if row.failures >= LOGIN_FAILURE_LIMIT:
        remaining = int((LOGIN_WINDOW - elapsed).total_seconds())
        await db.rollback()
        raise LoginThrottled(max(1, remaining))
    row.failures += 1
    await db.commit()


async def _row(db: AsyncSession, client_key: str, *, lock: bool):
    stmt = select(StoreAdminLoginThrottle).where(StoreAdminLoginThrottle.client_key == client_key)
    bind = db.bind
    if lock and bind is not None and bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    return await db.scalar(stmt)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
