"""Do‘kon administratori yozuvlari. Parol ochiq matnda saqlanmaydi."""
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.store_admin import StoreAdmin

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD = 8
_MAX_PASSWORD = 128


class StoreAdminWriteError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def normalize_email(value: str) -> str | None:
    text = value.strip().lower()
    if not text or len(text) > 255 or not _EMAIL.fullmatch(text):
        return None
    return text


def password_is_acceptable(password: str) -> bool:
    return _MIN_PASSWORD <= len(password) <= _MAX_PASSWORD


async def get_store_admin_by_email(db: AsyncSession, email: str) -> StoreAdmin | None:
    return await db.scalar(select(StoreAdmin).where(StoreAdmin.email == email))


async def get_store_admin_by_id(db: AsyncSession, admin_id: int) -> StoreAdmin | None:
    return await db.get(StoreAdmin, admin_id)


async def create_store_admin(db: AsyncSession, *, email: str, full_name: str, password: str) -> StoreAdmin:
    normalized = normalize_email(email)
    name = full_name.strip()
    if normalized is None:
        raise StoreAdminWriteError("Email noto‘g‘ri.")
    if not name or len(name) > 255:
        raise StoreAdminWriteError("Ism kiritilmagan.")
    if not password_is_acceptable(password):
        raise StoreAdminWriteError("Parol 8 dan 128 belgigacha bo‘lishi kerak.")
    if await get_store_admin_by_email(db, normalized) is not None:
        raise StoreAdminWriteError("Bu email allaqachon ro‘yxatdan o‘tgan.")
    admin = StoreAdmin(full_name=name, email=normalized, password_hash=hash_password(password), is_active=True)
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin
