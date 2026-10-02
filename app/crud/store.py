from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.store import StoreCategory, StoreProduct
from app.models.store_enums import StoreProductType, StoreUnit
from app.schemas.store import (
    CategoryRef,
    StoreCategoryDetail,
    StoreCategoryOut,
    StoreProductOut,
    money_to_text,
)


def contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _public_category(category: StoreCategory, *, include_children: bool) -> StoreCategoryOut:
    children: list[StoreCategoryOut] = []
    if include_children:
        visible = [child for child in category.children if child.is_active]
        visible.sort(key=lambda child: (child.sort_order, child.id))
        children = [_public_category(child, include_children=False) for child in visible]
    return StoreCategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        image=category.image,
        sort_order=category.sort_order,
        children=children,
    )


def _is_public_category(category: StoreCategory) -> bool:
    if not category.is_active:
        return False
    parent = category.parent
    if parent is not None and not parent.is_active:
        return False
    return True


def _image_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def to_public_product(product: StoreProduct) -> StoreProductOut:
    product_type = StoreProductType(product.product_type)
    ready = product_type is StoreProductType.READY_MADE
    return StoreProductOut(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        sku=product.sku,
        images=_image_list(product.images),
        product_type=product_type,
        unit=StoreUnit(product.unit),
        is_featured=product.is_featured,
        category=CategoryRef(id=product.category.id, name=product.category.name, slug=product.category.slug),
        dimensions=product.dimensions if ready else None,
        selling_price=money_to_text(product.selling_price) if ready else None,
        available_quantity=product.available_quantity if ready else None,
    )


async def list_active_root_categories(db: AsyncSession) -> list[StoreCategoryOut]:
    result = await db.execute(
        select(StoreCategory)
        .where(StoreCategory.parent_id.is_(None), StoreCategory.is_active.is_(True))
        .order_by(StoreCategory.sort_order, StoreCategory.id)
        .options(selectinload(StoreCategory.children))
    )
    return [_public_category(category, include_children=True) for category in result.scalars().all()]


async def get_active_category(db: AsyncSession, slug: str) -> StoreCategoryDetail | None:
    result = await db.execute(
        select(StoreCategory)
        .where(StoreCategory.slug == slug)
        .options(selectinload(StoreCategory.children), selectinload(StoreCategory.parent))
    )
    category = result.scalar_one_or_none()
    if category is None or not _is_public_category(category):
        return None
    detail = StoreCategoryDetail(
        **_public_category(category, include_children=True).model_dump(),
        parent=None
        if category.parent is None
        else CategoryRef(id=category.parent.id, name=category.parent.name, slug=category.parent.slug),
    )
    return detail


def _public_product_query():
    parent = aliased(StoreCategory)
    return (
        select(StoreProduct)
        .join(StoreCategory, StoreProduct.category_id == StoreCategory.id)
        .outerjoin(parent, StoreCategory.parent_id == parent.id)
        .where(
            StoreProduct.is_active.is_(True),
            StoreCategory.is_active.is_(True),
            or_(StoreCategory.parent_id.is_(None), parent.is_active.is_(True)),
        )
    )


async def _category_ids_for_filter(db: AsyncSession, slug: str) -> list[int] | None:
    detail = await get_active_category(db, slug)
    if detail is None:
        return None
    return [detail.id, *[child.id for child in detail.children]]


async def list_active_products(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    category_slug: str | None = None,
    product_type: StoreProductType | None = None,
    featured: bool | None = None,
    query: str | None = None,
) -> tuple[list[StoreProductOut], int] | None:
    stmt = _public_product_query()
    if category_slug:
        ids = await _category_ids_for_filter(db, category_slug)
        if ids is None:
            return None
        stmt = stmt.where(StoreProduct.category_id.in_(ids))
    if product_type is not None:
        stmt = stmt.where(StoreProduct.product_type == product_type.value)
    if featured is not None:
        stmt = stmt.where(StoreProduct.is_featured.is_(featured))
    if query:
        pattern = contains_pattern(query)
        stmt = stmt.where(
            or_(
                StoreProduct.name.ilike(pattern, escape="\\"),
                StoreProduct.sku.ilike(pattern, escape="\\"),
                StoreProduct.description.ilike(pattern, escape="\\"),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(await db.scalar(count_stmt) or 0)
    result = await db.execute(
        stmt.options(selectinload(StoreProduct.category))
        .order_by(StoreProduct.sort_order, StoreProduct.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [to_public_product(product) for product in result.scalars().all()]
    return items, total


async def get_product_for_pricing(db: AsyncSession, product_id: int) -> StoreProduct | None:
    result = await db.execute(
        select(StoreProduct)
        .where(StoreProduct.id == product_id)
        .options(
            selectinload(StoreProduct.pricing_rules),
            selectinload(StoreProduct.category).selectinload(StoreCategory.pricing_rules),
            selectinload(StoreProduct.category).selectinload(StoreCategory.parent).selectinload(StoreCategory.pricing_rules),
            selectinload(StoreProduct.category)
            .selectinload(StoreCategory.parent)
            .selectinload(StoreCategory.parent)
            .selectinload(StoreCategory.pricing_rules),
        )
    )
    return result.scalar_one_or_none()


async def get_active_product(db: AsyncSession, slug: str) -> StoreProductOut | None:
    result = await db.execute(
        _public_product_query().where(StoreProduct.slug == slug).options(selectinload(StoreProduct.category))
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None
    return to_public_product(product)
