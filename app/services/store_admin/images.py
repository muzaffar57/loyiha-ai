"""Do‘kon rasmlari.

Yuk tashish yuk rasmlaridan alohida katalog. Fayl avval yoziladi,
bazadagi maydon shundan keyin yangilanadi.
"""
import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.models.store import StoreCategory, StoreProduct
from app.services.store_admin.catalog import CatalogAdminError, category_out, product_out

_NAME = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")
_KINDS = {"products", "categories"}
MAX_PRODUCT_IMAGES = 8
_READ_CHUNK = 64 * 1024


def max_photo_bytes() -> int:
    return settings.MAX_PHOTO_SIZE_MB * 1024 * 1024


def detect_image(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff") and len(data) >= 4:
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 8:
        return "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def media_root() -> Path:
    root = Path(settings.MEDIA_ROOT).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def owner_directory(kind: str, owner_id: int) -> Path:
    if kind not in _KINDS or owner_id < 1:
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.")
    root = media_root()
    directory = (root / "store" / kind / str(owner_id)).resolve()
    if not _inside(directory, root):
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.")
    return directory


def owned_file(public_path: str, *, kind: str, owner_id: int) -> Path:
    prefix = f"/media/store/{kind}/{owner_id}/"
    if kind not in _KINDS or not public_path.startswith(prefix):
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.")
    name = public_path[len(prefix) :]
    if not _NAME.fullmatch(name):
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.")
    directory = owner_directory(kind, owner_id)
    candidate = directory / name
    try:
        resolved = candidate.resolve()
    except OSError:
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.") from None
    root = media_root()
    if not _inside(resolved, directory) or not _inside(resolved, root):
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.")
    return candidate


async def read_limited(upload: UploadFile) -> bytes:
    await upload.seek(0)
    limit = max_photo_bytes()
    chunks: list[bytes] = []
    total = 0
    while True:
        block = await upload.read(_READ_CHUNK)
        if not block:
            break
        total += len(block)
        if total > limit:
            raise CatalogAdminError(
                413,
                "FILE_TOO_LARGE",
                f"Rasm hajmi {settings.MAX_PHOTO_SIZE_MB}MB dan oshmasligi kerak.",
            )
        chunks.append(block)
    return b"".join(chunks)


async def add_product_image(db: AsyncSession, product_id: int, data: bytes):
    product = await _product(db, product_id)
    kind = _require_image(data)
    current = _image_list(product.images)
    if len(current) >= MAX_PRODUCT_IMAGES:
        raise CatalogAdminError(409, "IMAGE_LIMIT", "Mahsulotga ko‘pi bilan 8 ta rasm biriktirish mumkin.")
    path = write_image("products", product.id, kind, data)
    public = _public_url("products", product.id, path.name)
    product.images = [*current, public]
    flag_modified(product, "images")
    await _commit_keeping_file(db, path)
    await db.refresh(product)
    return product_out(product)


async def delete_product_image(db: AsyncSession, product_id: int, public_path: str):
    product = await _product(db, product_id)
    current = _image_list(product.images)
    if public_path not in current:
        raise CatalogAdminError(404, "IMAGE_NOT_FOUND", "Rasm topilmadi.")
    path = owned_file(public_path, kind="products", owner_id=product.id)
    product.images = [item for item in current if item != public_path]
    flag_modified(product, "images")
    await _commit_or_restore(db, product, "images", current, path)
    await db.refresh(product)
    return product_out(product)


async def set_category_image(db: AsyncSession, category_id: int, data: bytes):
    category = await _category(db, category_id)
    kind = _require_image(data)
    previous = category.image
    path = write_image("categories", category.id, kind, data)
    public = _public_url("categories", category.id, path.name)
    category.image = public
    await _commit_keeping_file(db, path)
    if isinstance(previous, str) and previous != public:
        _discard_owned(previous, kind="categories", owner_id=category.id)
    await db.refresh(category)
    return category_out(category)


async def delete_category_image(db: AsyncSession, category_id: int, public_path: str):
    category = await _category(db, category_id)
    if category.image != public_path:
        raise CatalogAdminError(404, "IMAGE_NOT_FOUND", "Rasm topilmadi.")
    path = owned_file(public_path, kind="categories", owner_id=category.id)
    category.image = None
    await _commit_or_restore(db, category, "image", public_path, path)
    await db.refresh(category)
    return category_out(category)


def write_image(kind: str, owner_id: int, extension: str, data: bytes) -> Path:
    directory = owner_directory(kind, owner_id)
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{extension}"
    target = directory / name
    partial = directory / f".{name}.part"
    try:
        partial.write_bytes(data)
        os.replace(partial, target)
    except OSError:
        partial.unlink(missing_ok=True)
        raise CatalogAdminError(503, "IMAGE_STORE_FAILED", "Rasm saqlanmadi.") from None
    resolved = target.resolve()
    if not _inside(resolved, directory) or not _inside(resolved, media_root()):
        _unlink(target)
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.")
    return target


def _require_image(data: bytes) -> str:
    kind = detect_image(data)
    if kind is None:
        raise CatalogAdminError(422, "INVALID_IMAGE", "Faqat JPEG, PNG yoki WebP rasm qabul qilinadi.")
    return kind


def _public_url(kind: str, owner_id: int, filename: str) -> str:
    if not _NAME.fullmatch(filename):
        raise CatalogAdminError(409, "IMAGE_NOT_OWNED", "Bu rasm shu yozuvga tegishli emas.")
    return f"/media/store/{kind}/{owner_id}/{filename}"


def _image_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


async def _product(db: AsyncSession, product_id: int) -> StoreProduct:
    product = await db.get(StoreProduct, product_id)
    if product is None:
        raise CatalogAdminError(404, "PRODUCT_NOT_FOUND", "Mahsulot topilmadi.")
    return product


async def _category(db: AsyncSession, category_id: int) -> StoreCategory:
    category = await db.get(StoreCategory, category_id)
    if category is None:
        raise CatalogAdminError(404, "CATEGORY_NOT_FOUND", "Kategoriya topilmadi.")
    return category


async def _commit_image(db: AsyncSession) -> None:
    await db.commit()


async def _commit_keeping_file(db: AsyncSession, path: Path) -> None:
    try:
        await _commit_image(db)
    except Exception:
        await db.rollback()
        try:
            _unlink(path)
        except OSError:
            pass
        raise CatalogAdminError(503, "IMAGE_STORE_FAILED", "Rasm saqlanmadi.") from None


async def _commit_or_restore(db: AsyncSession, row: object, field: str, previous: object, path: Path) -> None:
    try:
        await _commit_image(db)
    except Exception:
        await db.rollback()
        raise CatalogAdminError(503, "IMAGE_STORE_FAILED", "Rasm saqlanmadi.") from None
    try:
        _unlink(path)
    except OSError:
        try:
            await db.refresh(row)
        except Exception:
            await db.rollback()
        setattr(row, field, previous)
        if field == "images":
            flag_modified(row, "images")
        try:
            await _commit_image(db)
        except Exception:
            await db.rollback()
        raise CatalogAdminError(503, "IMAGE_STORE_FAILED", "Rasm o‘chirilmadi.") from None


def _discard_owned(public_path: str, *, kind: str, owner_id: int) -> None:
    try:
        path = owned_file(public_path, kind=kind, owner_id=owner_id)
    except CatalogAdminError:
        return
    try:
        _unlink(path)
    except OSError:
        return


def _unlink(path: Path) -> None:
    path.unlink(missing_ok=True)
