"""Kategoriya va mahsulot boshqaruvi. Narx endpointi yo‘q."""
from typing import NoReturn

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.store.admin_deps import get_current_store_admin
from app.db.session import get_db
from app.models.store_admin import StoreAdmin
from app.schemas.store_admin_catalog import (
    AdminCategoryCreate,
    AdminCategoryList,
    AdminCategoryOut,
    AdminCategoryPatch,
    AdminImageDelete,
    AdminProductCreate,
    AdminProductOut,
    AdminProductPage,
    AdminProductPatch,
    AdminStockPatch,
)
from app.services.store_admin.catalog import (
    CatalogAdminError,
    create_admin_category,
    create_admin_product,
    get_admin_product,
    list_admin_categories,
    list_admin_products,
    update_admin_category,
    update_admin_product,
    update_admin_stock,
)
from app.services.store_admin.images import (
    add_product_image,
    delete_category_image,
    delete_product_image,
    read_limited,
    set_category_image,
)

router = APIRouter(
    prefix="/admin",
    tags=["Store admin catalog (PenodecorPro)"],
    dependencies=[Depends(get_current_store_admin)],
)


def _raise(exc: CatalogAdminError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/categories", response_model=AdminCategoryList, summary="Barcha kategoriyalar")
async def admin_categories(
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminCategoryList:
    return AdminCategoryList(items=await list_admin_categories(db))


@router.post("/categories", response_model=AdminCategoryOut, status_code=201, summary="Kategoriya yaratish")
async def admin_create_category(
    body: AdminCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminCategoryOut:
    try:
        return await create_admin_category(db, body)
    except CatalogAdminError as exc:
        _raise(exc)


@router.patch("/categories/{category_id}", response_model=AdminCategoryOut, summary="Kategoriyani tahrirlash")
async def admin_update_category(
    category_id: int,
    body: AdminCategoryPatch,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminCategoryOut:
    try:
        return await update_admin_category(db, category_id, body)
    except CatalogAdminError as exc:
        _raise(exc)


@router.get("/products", response_model=AdminProductPage, summary="Faol va nofaol mahsulotlar")
async def admin_products(
    category_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminProductPage:
    try:
        items, total = await list_admin_products(db, page=page, page_size=page_size, category_id=category_id, query=q)
    except CatalogAdminError as exc:
        _raise(exc)
    return AdminProductPage(items=items, page=page, page_size=page_size, total=total)


@router.post("/products", response_model=AdminProductOut, status_code=201, summary="Mahsulot yaratish")
async def admin_create_product(
    body: AdminProductCreate,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminProductOut:
    try:
        return await create_admin_product(db, body)
    except CatalogAdminError as exc:
        _raise(exc)


@router.get("/products/{product_id}", response_model=AdminProductOut, summary="Mahsulot tafsiloti")
async def admin_get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminProductOut:
    try:
        return await get_admin_product(db, product_id)
    except CatalogAdminError as exc:
        _raise(exc)


@router.post("/products/{product_id}/images", response_model=AdminProductOut, summary="Mahsulot rasmini yuklash")
async def admin_add_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminProductOut:
    try:
        data = await read_limited(file)
        return await add_product_image(db, product_id, data)
    except CatalogAdminError as exc:
        _raise(exc)


@router.delete("/products/{product_id}/images", response_model=AdminProductOut, summary="Mahsulot rasmini o‘chirish")
async def admin_delete_product_image(
    product_id: int,
    body: AdminImageDelete,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminProductOut:
    try:
        return await delete_product_image(db, product_id, body.image)
    except CatalogAdminError as exc:
        _raise(exc)


@router.post("/categories/{category_id}/image", response_model=AdminCategoryOut, summary="Kategoriya rasmini yuklash")
async def admin_set_category_image(
    category_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminCategoryOut:
    try:
        data = await read_limited(file)
        return await set_category_image(db, category_id, data)
    except CatalogAdminError as exc:
        _raise(exc)


@router.delete("/categories/{category_id}/image", response_model=AdminCategoryOut, summary="Kategoriya rasmini o‘chirish")
async def admin_delete_category_image(
    category_id: int,
    body: AdminImageDelete,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminCategoryOut:
    try:
        return await delete_category_image(db, category_id, body.image)
    except CatalogAdminError as exc:
        _raise(exc)


@router.patch("/products/{product_id}/stock", response_model=AdminProductOut, summary="Tayyor mahsulot qoldig‘i")
async def admin_update_stock(
    product_id: int,
    body: AdminStockPatch,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminProductOut:
    try:
        return await update_admin_stock(db, product_id, body)
    except CatalogAdminError as exc:
        _raise(exc)


@router.patch("/products/{product_id}", response_model=AdminProductOut, summary="Mahsulotni tahrirlash")
async def admin_update_product(
    product_id: int,
    body: AdminProductPatch,
    db: AsyncSession = Depends(get_db),
    _admin: StoreAdmin = Depends(get_current_store_admin),
) -> AdminProductOut:
    try:
        return await update_admin_product(db, product_id, body)
    except CatalogAdminError as exc:
        _raise(exc)
