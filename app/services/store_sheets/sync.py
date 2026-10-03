"""Tekshirilgan Sheets konfiguratsiyasini aktiv narxlarning o‘rniga yozadi.

Xato bo‘lsa oxirgi muvaffaqiyatli narx va foiz saqlanadi. Bir vaqtning
o‘zida ikkinchi sinxron ishga tushmaydi.
"""
import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.store import StoreCategory, StorePricingRule, StoreProduct
from app.models.store_enums import StoreProductType
from app.models.store_settings import StorePriceSettings
from app.services.store_sheets.errors import SheetSyncError, SheetUnavailable, SheetValidationError, SyncBusy, redact
from app.services.store_sheets.google_source import GoogleSheetSource
from app.services.store_sheets.layout import READY_SHEET, SHEET_ROOTS
from app.services.store_sheets.parse import RuleDraft, StockDraft, WorkbookDraft, parse_workbook
from app.services.store_sheets.repository import aware, get_or_create_settings, sheet_loop_enabled

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_RUNNING_GRACE = timedelta(minutes=15)
_DOOR_CATEGORY = "eshik-bezaklari"
_WINDOW_CATEGORY = "deraza-romlari"


class MemorySheetSource:
    def __init__(self, tables: dict[str, list[list[str]]] | None = None, error: Exception | None = None) -> None:
        self.tables = tables or {}
        self.error = error
        self.calls = 0

    def fetch(self) -> dict[str, list[list[str]]]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.tables


async def sync_from_source(db: AsyncSession, source: object) -> dict[str, int | str]:
    if not _lock.acquire(blocking=False):
        raise SyncBusy()
    try:
        return await _sync_locked(db, source)
    finally:
        _lock.release()


async def _sync_locked(db: AsyncSession, source: object) -> dict[str, int | str]:
    await _reject_if_running(db)
    await _mark_running(db)
    try:
        tables = await asyncio.to_thread(source.fetch)  # type: ignore[attr-defined]
        draft = parse_workbook(tables)
        updated = await _apply(db, draft)
    except SheetSyncError as exc:
        await db.rollback()
        await _mark_error(db, exc.message)
        raise
    except Exception as exc:
        await db.rollback()
        await _mark_error(db, redact(str(exc)))
        raise SheetUnavailable() from None
    return {"status": "ok", "updated_products": updated}


async def sheet_sync_loop() -> None:
    interval = max(settings.STORE_SHEETS_SYNC_INTERVAL_SECONDS, 60)
    while True:
        await asyncio.sleep(interval)
        if not sheet_loop_enabled():
            continue
        try:
            async with AsyncSessionLocal() as session:
                await sync_from_source(session, GoogleSheetSource())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("store sheet interval sync failed: %s", redact(str(exc)))


async def _reject_if_running(db: AsyncSession) -> None:
    row = await db.get(StorePriceSettings, 1)
    if row is None or row.status != "running":
        return
    started = aware(row.last_attempt_at)
    if started is not None and datetime.now(timezone.utc) - started < _RUNNING_GRACE:
        raise SyncBusy()


async def _mark_running(db: AsyncSession) -> None:
    row = await get_or_create_settings(db)
    row.status = "running"
    row.last_attempt_at = datetime.now(timezone.utc)
    await db.commit()


async def _mark_error(db: AsyncSession, message: str) -> None:
    row = await get_or_create_settings(db)
    row.status = "error"
    row.last_attempt_at = datetime.now(timezone.utc)
    row.last_error = redact(message)
    row.stale = row.last_success_at is not None
    await db.commit()


async def _apply(db: AsyncSession, draft: WorkbookDraft) -> int:
    slugs = [item.product_slug for item in draft.rules] + [item.product_slug for item in draft.stock]
    products = await _load_products(db, slugs)
    errors: list[str] = []
    resolved_rules: list[tuple[StoreProduct, RuleDraft]] = []
    for rule in draft.rules:
        product = products.get(rule.product_slug)
        product_errors = _check_rule_product(product, rule)
        errors.extend(product_errors)
        if product is not None and not product_errors:
            resolved_rules.append((product, rule))
    resolved_stock: list[tuple[StoreProduct, StockDraft]] = []
    for stock in draft.stock:
        product = products.get(stock.product_slug)
        product_errors = _check_stock_product(product, stock)
        errors.extend(product_errors)
        if product is not None and not product_errors:
            resolved_stock.append((product, stock))
    if errors:
        raise SheetValidationError(errors)
    for product, rule in resolved_rules:
        await db.execute(delete(StorePricingRule).where(StorePricingRule.product_id == product.id))
        db.add(
            StorePricingRule(
                name=rule.name,
                product_id=product.id,
                category_id=None,
                rule_type=rule.rule_type,
                config=rule.config,
                is_active=rule.is_active,
            )
        )
    for product, stock in resolved_stock:
        # Qoldiq va mahsulot faolligi do‘kon ma’lumoti. Jadval faqat asl sotuv narxini yangilaydi.
        product.selling_price = Decimal(stock.selling_price)
    row = await get_or_create_settings(db)
    now = datetime.now(timezone.utc)
    row.global_price_adjustment_percent = draft.percent
    row.currency = draft.currency
    row.sheet_updated_at = draft.updated_at
    row.last_success_at = now
    row.last_attempt_at = now
    row.last_error = None
    row.status = "ok"
    row.stale = False
    await db.commit()
    return len(resolved_rules) + len(resolved_stock)


async def _load_products(db: AsyncSession, slugs: list[str]) -> dict[str, StoreProduct]:
    if not slugs:
        return {}
    result = await db.scalars(
        select(StoreProduct)
        .where(StoreProduct.slug.in_(slugs))
        .options(selectinload(StoreProduct.category).selectinload(StoreCategory.parent))
    )
    return {product.slug: product for product in result}


def _root_slug(product: StoreProduct) -> str | None:
    category = product.category
    if category is None:
        return None
    if category.parent is not None:
        return category.parent.slug
    return category.slug


def _check_rule_product(product: StoreProduct | None, rule: RuleDraft) -> list[str]:
    if product is None:
        return [f"{rule.product_slug}: mahsulot topilmadi."]
    if product.product_type != StoreProductType.MADE_TO_ORDER:
        return [f"{rule.product_slug}: tayyor mahsulot formulaga bog‘lanmaydi."]
    expected = _expected_root(rule)
    if _root_slug(product) != expected:
        return [f"{rule.product_slug}: mahsulot toifasi {expected} emas."]
    category_slug = product.category.slug if product.category is not None else ""
    opening = str(rule.config.get("opening") or "")
    if category_slug == _DOOR_CATEGORY and opening != "door":
        return [f"{rule.product_slug}: eshik modeli window bo‘la olmaydi."]
    if category_slug == _WINDOW_CATEGORY and opening != "window":
        return [f"{rule.product_slug}: deraza modeli door bo‘la olmaydi."]
    return []


def _expected_root(rule: RuleDraft) -> str:
    family = str(rule.config.get("family") or "")
    mapping = {
        "trim_set": SHEET_ROOTS["Rom_Eshik"],
        "pilaster": SHEET_ROOTS["Pilastrlar"],
        "round_column": SHEET_ROOTS["Yumaloq_Ustunlar"],
        "cornice": SHEET_ROOTS["Shift_Karnizlari"],
        "shohona": SHEET_ROOTS["Shohona_Karnizlar"],
    }
    return mapping.get(family, "")


def _check_stock_product(product: StoreProduct | None, stock: StockDraft) -> list[str]:
    if product is None:
        return [f"{READY_SHEET}: {stock.product_slug} mahsuloti topilmadi."]
    if product.product_type != StoreProductType.READY_MADE:
        return [f"{stock.product_slug}: tayyor mahsulot turi emas."]
    if _root_slug(product) != SHEET_ROOTS[READY_SHEET]:
        return [f"{stock.product_slug}: mahsulot tayyor mahsulotlar toifasida emas."]
    if product.sku != stock.sku:
        return [f"{stock.product_slug}: SKU mos emas."]
    return []
