"""Sinxron holati va umumiy foizni o‘qish.

Hisoblash so‘rovi Google Sheets’ga chiqmaydi. Jadval hali yaratilmagan
bo‘lsa, asl narx ishlatiladi va narx nolga tushirilmaydi.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.store_settings import StorePriceSettings
from app.services.store_pricing.adjustment import percent_is_valid


def sheets_configured() -> bool:
    return bool(settings.STORE_SHEETS_SPREADSHEET_ID.strip() and settings.STORE_SHEETS_CREDENTIALS_FILE.strip())


def sheet_loop_enabled() -> bool:
    return settings.STORE_SHEETS_SYNC_INTERVAL_SECONDS > 0 and sheets_configured()


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def settings_are_stale(row: StorePriceSettings | None, *, now: datetime | None = None) -> bool:
    if row is None or row.last_success_at is None:
        return False
    if row.stale:
        return True
    stale_after = settings.STORE_SHEETS_STALE_AFTER_SECONDS
    success = aware(row.last_success_at)
    if sheets_configured() and stale_after > 0 and success is not None:
        current = now or datetime.now(timezone.utc)
        return current - success > timedelta(seconds=stale_after)
    return False


async def load_selling_adjustment(db: AsyncSession) -> tuple[Decimal, bool]:
    try:
        row = await db.scalar(select(StorePriceSettings).limit(1))
    except SQLAlchemyError:
        await db.rollback()
        return Decimal("0"), False
    if row is None:
        return Decimal("0"), False
    try:
        percent = Decimal(str(row.global_price_adjustment_percent))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0"), True
    if not percent_is_valid(percent):
        return Decimal("0"), True
    return percent, settings_are_stale(row)


async def get_or_create_settings(db: AsyncSession) -> StorePriceSettings:
    row = await db.get(StorePriceSettings, 1)
    if row is None:
        row = StorePriceSettings(
            id=1,
            global_price_adjustment_percent=Decimal("0"),
            currency="UZS",
            status="never",
            stale=False,
        )
        db.add(row)
        await db.flush()
    return row
