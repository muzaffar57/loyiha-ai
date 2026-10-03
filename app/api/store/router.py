from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.store.admin_catalog import router as store_admin_catalog_router
from app.api.store.admin_deps import get_current_store_admin
from app.api.store.admin_routes import router as store_admin_router
from app.api.store.sync_guard import require_store_sync_token
from app.crud.store import get_active_category, get_active_product, list_active_products, list_active_root_categories
from app.db.session import get_db
from app.models.store_admin import StoreAdmin
from app.models.store_enums import StoreProductType
from app.models.store_settings import StorePriceSettings
from app.schemas.store import StoreCategoryDetail, StoreCategoryList, StoreProductOut, StoreProductPage, StorePublicConfig
from app.schemas.store_pricing import PricingCalculateRequest, PricingQuoteOut
from app.schemas.store_sheets import SyncResultOut, SyncStatusOut
from app.services.store_pricing.adjustment import format_percent
from app.services.store_pricing.errors import PricingError
from app.services.store_pricing.service import calculate_store_price
from app.services.store_sheets.errors import SheetUnavailable, SheetValidationError, SyncBusy
from app.services.store_sheets.google_source import GoogleSheetSource
from app.services.store_sheets.repository import settings_are_stale
from app.services.store_sheets.sync import sync_from_source

router = APIRouter(tags=["Store (PenodecorPro)"])
router.include_router(store_admin_router)
router.include_router(store_admin_catalog_router)

_SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


@router.get("/config", response_model=StorePublicConfig, summary="Ochiq do‘kon sozlamasi")
async def store_config() -> StorePublicConfig:
    return StorePublicConfig(currency="UZS", company_phone=None, checkout_enabled=False)


@router.get("/categories", response_model=StoreCategoryList, summary="Faol katalog bo‘limlari")
async def list_categories(db: AsyncSession = Depends(get_db)) -> StoreCategoryList:
    return StoreCategoryList(items=await list_active_root_categories(db))


@router.get("/categories/{slug}", response_model=StoreCategoryDetail, summary="Bo‘lim tafsiloti")
async def category_detail(slug: str, db: AsyncSession = Depends(get_db)) -> StoreCategoryDetail:
    category = await get_active_category(db, slug)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategoriya topilmadi.")
    return category


@router.get("/products", response_model=StoreProductPage, summary="Faol mahsulotlar")
async def list_products(
    category: str | None = Query(default=None, max_length=80, pattern=_SLUG),
    product_type: StoreProductType | None = None,
    featured: bool | None = None,
    q: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> StoreProductPage:
    found = await list_active_products(
        db,
        page=page,
        page_size=page_size,
        category_slug=category,
        product_type=product_type,
        featured=featured,
        query=_clean_query(q),
    )
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategoriya topilmadi.")
    items, total = found
    return StoreProductPage(items=items, page=page, page_size=page_size, total=total)


@router.post("/pricing/calculate", response_model=PricingQuoteOut, summary="Mahsulot narxini serverda hisoblash")
async def calculate_price(body: PricingCalculateRequest, db: AsyncSession = Depends(get_db)) -> PricingQuoteOut:
    try:
        return await calculate_store_price(db, body)
    except PricingError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


def get_sheet_source() -> GoogleSheetSource:
    return GoogleSheetSource()


async def load_sync_status(db: AsyncSession) -> SyncStatusOut:
    row = await db.get(StorePriceSettings, 1)
    if row is None:
        return SyncStatusOut(
            status="never",
            stale=False,
            currency="UZS",
            global_price_adjustment_percent="0",
            last_success_at=None,
            last_attempt_at=None,
            last_error=None,
            sheet_updated_at=None,
        )
    percent = format_percent(Decimal(str(row.global_price_adjustment_percent)))
    return SyncStatusOut(
        status=row.status,
        stale=settings_are_stale(row),
        currency=row.currency,
        global_price_adjustment_percent=percent,
        last_success_at=row.last_success_at,
        last_attempt_at=row.last_attempt_at,
        last_error=row.last_error,
        sheet_updated_at=row.sheet_updated_at,
    )


async def run_pricing_sync(db: AsyncSession, source: GoogleSheetSource) -> SyncResultOut:
    try:
        result = await sync_from_source(db, source)
    except SyncBusy as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": exc.code, "message": exc.message}) from exc
    except SheetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": exc.code, "message": exc.message}) from exc
    except SheetUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": exc.code, "message": exc.message}) from exc
    return SyncResultOut(status="ok", updated_products=int(result["updated_products"]))


@router.get("/pricing/sync-status", response_model=SyncStatusOut, summary="Narx sinxron holati")
async def pricing_sync_status(
    _: None = Depends(require_store_sync_token),
    db: AsyncSession = Depends(get_db),
) -> SyncStatusOut:
    return await load_sync_status(db)


@router.post("/pricing/sync", response_model=SyncResultOut, summary="Narx jadvalini sinxronlash")
async def pricing_sync(
    _: None = Depends(require_store_sync_token),
    source: GoogleSheetSource = Depends(get_sheet_source),
    db: AsyncSession = Depends(get_db),
) -> SyncResultOut:
    return await run_pricing_sync(db, source)


@router.get("/admin/pricing/sync-status", response_model=SyncStatusOut, summary="Administrator uchun sinxron holati")
async def admin_pricing_sync_status(
    _admin: StoreAdmin = Depends(get_current_store_admin),
    db: AsyncSession = Depends(get_db),
) -> SyncStatusOut:
    return await load_sync_status(db)


@router.post("/admin/pricing/sync", response_model=SyncResultOut, summary="Administrator sinxronni boshlashi")
async def admin_pricing_sync(
    _admin: StoreAdmin = Depends(get_current_store_admin),
    source: GoogleSheetSource = Depends(get_sheet_source),
    db: AsyncSession = Depends(get_db),
) -> SyncResultOut:
    return await run_pricing_sync(db, source)


@router.get("/products/{slug}", response_model=StoreProductOut, summary="Mahsulot tafsiloti")
async def product_detail(slug: str, db: AsyncSession = Depends(get_db)) -> StoreProductOut:
    product = await get_active_product(db, slug)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mahsulot topilmadi.")
    return product


@router.get("/stock", response_model=StoreProductPage, summary="Tayyor ombor mahsulotlari")
async def list_stock(
    category: str | None = Query(default=None, max_length=80, pattern=_SLUG),
    q: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> StoreProductPage:
    found = await list_active_products(
        db,
        page=page,
        page_size=page_size,
        category_slug=category,
        product_type=StoreProductType.READY_MADE,
        query=_clean_query(q),
    )
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategoriya topilmadi.")
    items, total = found
    return StoreProductPage(items=items, page=page, page_size=page_size, total=total)


def _clean_query(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None
