"""Do‘kon administratori ruxsati.

Yuk tashish `get_current_admin` va `users.is_admin` ishlatilmaydi.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.store_admin import get_store_admin_by_id
from app.db.session import get_db
from app.models.store_admin import StoreAdmin
from app.services.store_admin.tokens import read_store_admin_id

store_admin_scheme = OAuth2PasswordBearer(tokenUrl="/api/store/admin/login", auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Kirish talab qilinadi.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_store_admin(
    token: str | None = Depends(store_admin_scheme),
    db: AsyncSession = Depends(get_db),
) -> StoreAdmin:
    if not token:
        raise _UNAUTHORIZED
    admin_id = read_store_admin_id(token)
    if admin_id is None:
        raise _UNAUTHORIZED
    admin = await get_store_admin_by_id(db, admin_id)
    if admin is None:
        raise _UNAUTHORIZED
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hisob faol emas.")
    return admin
