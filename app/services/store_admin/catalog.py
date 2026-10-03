"""Administrator katalogi.

Narx, qoldiq va rasm yo‘li bu yerda yozilmaydi. Rasm yuklash endpointi
faylni o‘zi saqlaydi.
"""
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.store import contains_pattern
from app.models.store import StoreCategory, StorePricingRule, StoreProduct
from app.models.store_enums import StoreProductType, StoreUnit
from app.models.store_settings import StorePriceSettings
from app.schemas.store import money_to_text
from app.schemas.store_admin_catalog import (
    AdminCategoryCreate,
    AdminCategoryOut,
    AdminCategoryPatch,
    AdminProductCreate,
    AdminProductOut,
    AdminProductPatch,
    AdminStockPatch,
)


class CatalogAdminError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def category_out(category: StoreCategory) -> AdminCategoryOut:
    return AdminCategoryOut(
        id=category.id,
        parent_id=category.parent_id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        image=category.image,
        is_active=category.is_active,
        sort_order=category.sort_order,
    )


def product_out(product: StoreProduct) -> AdminProductOut:
    ready = StoreProductType(product.product_type) is StoreProductType.READY_MADE
    price = _positive_price(product.selling_price) if ready else None
    return AdminProductOut(
        id=product.id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        sku=product.sku,
        images=list(product.images or []),
        product_type=StoreProductType(product.product_type),
        unit=StoreUnit(product.unit),
        dimensions=product.dimensions,
        is_active=product.is_active,
        is_featured=product.is_featured,
        sort_order=product.sort_order,
        selling_price=price,
        available_quantity=product.available_quantity if ready else None,
    )


async def list_admin_categories(db: AsyncSession) -> list[AdminCategoryOut]:
    result = await db.scalars(select(StoreCategory).order_by(StoreCategory.sort_order, StoreCategory.id))
    return [category_out(category) for category in result.all()]


async def create_admin_category(db: AsyncSession, body: AdminCategoryCreate) -> AdminCategoryOut:
    await _require_parent(db, body.parent_id)
    await _require_unique_category_slug(db, body.slug)
    category = StoreCategory(
        name=body.name,
        slug=body.slug,
        description=body.description,
        image=None,
        is_active=body.is_active,
        sort_order=body.sort_order,
        parent_id=body.parent_id,
    )
    db.add(category)
    await _commit(db)
    await db.refresh(category)
    return category_out(category)


async def update_admin_category(db: AsyncSession, category_id: int, body: AdminCategoryPatch) -> AdminCategoryOut:
    category = await db.get(StoreCategory, category_id)
    if category is None:
        raise CatalogAdminError(404, "CATEGORY_NOT_FOUND", "Kategoriya topilmadi.")
    changes = body.model_dump(exclude_unset=True)
    _reject_direct_media(changes)
    if not changes:
        raise CatalogAdminError(422, "EMPTY_UPDATE", "O‘zgartirish yuborilmadi.")
    if "parent_id" in changes:
        await _require_parent(db, changes["parent_id"], category_id=category.id)
    if "slug" in changes and changes["slug"] != category.slug:
        await _require_unique_category_slug(db, changes["slug"], ignore_id=category.id)
    for key, value in changes.items():
        setattr(category, key, value)
    await _commit(db)
    await db.refresh(category)
    return category_out(category)


async def list_admin_products(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    category_id: int | None = None,
    query: str | None = None,
) -> tuple[list[AdminProductOut], int]:
    filters = []
    if category_id is not None:
        if await db.get(StoreCategory, category_id) is None:
            raise CatalogAdminError(404, "CATEGORY_NOT_FOUND", "Kategoriya topilmadi.")
        filters.append(StoreProduct.category_id == category_id)
    text = query.strip() if query else ""
    if text:
        pattern = contains_pattern(text)
        filters.append(
            or_(
                StoreProduct.name.ilike(pattern, escape="\\"),
                StoreProduct.slug.ilike(pattern, escape="\\"),
                StoreProduct.sku.ilike(pattern, escape="\\"),
            )
        )
    total = int(await db.scalar(select(func.count()).select_from(StoreProduct).where(*filters)) or 0)
    result = await db.scalars(
        select(StoreProduct)
        .where(*filters)
        .order_by(StoreProduct.sort_order, StoreProduct.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [product_out(product) for product in result.all()], total


async def get_admin_product(db: AsyncSession, product_id: int) -> AdminProductOut:
    product = await _product(db, product_id)
    return product_out(product)


async def create_admin_product(db: AsyncSession, body: AdminProductCreate) -> AdminProductOut:
    if await db.get(StoreCategory, body.category_id) is None:
        raise CatalogAdminError(404, "CATEGORY_NOT_FOUND", "Kategoriya topilmadi.")
    await _require_unique_product_slug(db, body.slug)
    ready = body.product_type is StoreProductType.READY_MADE
    if ready and not body.sku:
        raise CatalogAdminError(422, "SKU_REQUIRED", "Tayyor mahsulot uchun SKU kerak.")
    if ready and body.is_active:
        raise CatalogAdminError(409, "PRICE_OWNED_BY_SHEETS", "Narx Google Sheets dan kelmaguncha mahsulot katalogda ochilmaydi.")
    if body.sku:
        await _require_unique_sku(db, body.sku)
    product = StoreProduct(
        category_id=body.category_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        sku=body.sku,
        images=[],
        product_type=body.product_type,
        unit=body.unit,
        dimensions=body.dimensions,
        is_active=False if ready else body.is_active,
        is_featured=body.is_featured,
        sort_order=body.sort_order,
        selling_price=Decimal("0.00") if ready else None,
        available_quantity=0 if ready else None,
    )
    db.add(product)
    await _commit(db)
    await db.refresh(product)
    return product_out(product)


async def update_admin_product(db: AsyncSession, product_id: int, body: AdminProductPatch) -> AdminProductOut:
    product = await _product(db, product_id)
    changes = body.model_dump(exclude_unset=True)
    _reject_direct_media(changes)
    if not changes:
        raise CatalogAdminError(422, "EMPTY_UPDATE", "O‘zgartirish yuborilmadi.")
    ready = StoreProductType(product.product_type) is StoreProductType.READY_MADE
    if ready and "sku" in changes and changes["sku"] != product.sku:
        raise CatalogAdminError(409, "SKU_LOCKED", "Tayyor mahsulot SKU si Google Sheets qatori bilan bog‘langan va bu yerda o‘zgartirilmaydi.")
    if "category_id" in changes and await db.get(StoreCategory, changes["category_id"]) is None:
        raise CatalogAdminError(404, "CATEGORY_NOT_FOUND", "Kategoriya topilmadi.")
    if "slug" in changes and changes["slug"] != product.slug:
        await _require_unique_product_slug(db, changes["slug"], ignore_id=product.id)
    if not ready and "sku" in changes and changes["sku"] != product.sku and changes["sku"]:
        await _require_unique_sku(db, changes["sku"], ignore_id=product.id)
    if changes.get("is_active") is True and ready and _positive_price(product.selling_price) is None:
        raise CatalogAdminError(409, "PRICE_OWNED_BY_SHEETS", "Narx Google Sheets dan kelmaguncha mahsulot katalogda ochilmaydi.")
    price_before = product.selling_price
    quantity_before = product.available_quantity
    for key, value in changes.items():
        setattr(product, key, value)
    product.selling_price = price_before
    product.available_quantity = quantity_before
    await _commit(db)
    await db.refresh(product)
    return product_out(product)


async def update_admin_stock(db: AsyncSession, product_id: int, body: AdminStockPatch) -> AdminProductOut:
    product = await _product(db, product_id)
    if StoreProductType(product.product_type) is not StoreProductType.READY_MADE:
        raise CatalogAdminError(409, "STOCK_NOT_READY", "Qoldiq faqat tayyor mahsulot uchun yoziladi.")
    price_before = product.selling_price
    sku_before = product.sku
    active_before = product.is_active
    product.available_quantity = body.available_quantity
    product.selling_price = price_before
    product.sku = sku_before
    product.is_active = active_before
    await _commit(db)
    await db.refresh(product)
    return product_out(product)


def _reject_direct_media(changes: dict[str, object]) -> None:
    if "image" in changes or "images" in changes:
        raise CatalogAdminError(
            422,
            "IMAGE_PATH_LOCKED",
            "Rasm faqat yuklash va o‘chirish orqali o‘zgartiriladi.",
        )


def _positive_price(value: Decimal | None) -> str | None:
    if value is None:
        return None
    amount = Decimal(str(value))
    if amount <= 0:
        return None
    return money_to_text(amount)


async def _product(db: AsyncSession, product_id: int) -> StoreProduct:
    product = await db.scalar(select(StoreProduct).where(StoreProduct.id == product_id).options(selectinload(StoreProduct.category)))
    if product is None:
        raise CatalogAdminError(404, "PRODUCT_NOT_FOUND", "Mahsulot topilmadi.")
    return product


async def _require_parent(db: AsyncSession, parent_id: int | None, *, category_id: int | None = None) -> None:
    if parent_id is None:
        return
    if category_id is not None and parent_id == category_id:
        raise CatalogAdminError(422, "INVALID_PARENT", "Kategoriya o‘ziga bog‘lanmaydi.")
    seen: set[int] = set()
    current: int | None = parent_id
    while current is not None:
        if current in seen or current == category_id:
            raise CatalogAdminError(422, "INVALID_PARENT", "Kategoriya aylanasiga yo‘l qo‘yilmaydi.")
        seen.add(current)
        parent = await db.get(StoreCategory, current)
        if parent is None:
            raise CatalogAdminError(404, "CATEGORY_NOT_FOUND", "Kategoriya topilmadi.")
        current = parent.parent_id


async def _require_unique_category_slug(db: AsyncSession, slug: str, *, ignore_id: int | None = None) -> None:
    found = await db.scalar(select(StoreCategory.id).where(StoreCategory.slug == slug))
    if found is not None and found != ignore_id:
        raise CatalogAdminError(409, "DUPLICATE_SLUG", "Bu slug band.")


async def _require_unique_product_slug(db: AsyncSession, slug: str, *, ignore_id: int | None = None) -> None:
    found = await db.scalar(select(StoreProduct.id).where(StoreProduct.slug == slug))
    if found is not None and found != ignore_id:
        raise CatalogAdminError(409, "DUPLICATE_SLUG", "Bu slug band.")


async def _require_unique_sku(db: AsyncSession, sku: str, *, ignore_id: int | None = None) -> None:
    found = await db.scalar(select(StoreProduct.id).where(StoreProduct.sku == sku))
    if found is not None and found != ignore_id:
        raise CatalogAdminError(409, "DUPLICATE_SKU", "Bu SKU band.")


async def _commit(db: AsyncSession) -> None:
    if _price_rows_dirty(db):
        await db.rollback()
        raise CatalogAdminError(409, "PRICE_OWNED_BY_SHEETS", "Narx va foiz Google Sheets orqali boshqariladi.")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise CatalogAdminError(409, "DUPLICATE_SLUG", "Bu slug yoki SKU band.") from None


def _price_rows_dirty(db: AsyncSession) -> bool:
    for obj in (*db.new, *db.dirty):
        if isinstance(obj, (StorePricingRule, StorePriceSettings)):
            return True
    return False
