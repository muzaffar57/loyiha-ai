"""Do‘kon administratori kirishi.

Noma’lum email va noto‘g‘ri parol bir xil javob qaytaradi.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.store.admin_deps import get_current_store_admin
from app.core.security import verify_password
from app.crud.store_admin import get_store_admin_by_email, normalize_email, password_is_acceptable
from app.db.session import get_db
from app.models.store_admin import StoreAdmin
from app.schemas.store_admin import StoreAdminLogin, StoreAdminOut, StoreAdminToken
from app.services.store_admin.client_ip import client_key
from app.services.store_admin.login_throttle import LoginThrottled, clear_login_failures, consume_login_attempt
from app.services.store_admin.tokens import create_store_admin_token, store_admin_secret

router = APIRouter(prefix="/admin", tags=["Store admin (PenodecorPro)"])

_LOGIN_FAILED = "Email yoki parol noto‘g‘ri."
_dummy_hash: str | None = None


def _timing_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        from app.core.security import hash_password

        _dummy_hash = hash_password("store-admin-timing-check")
    return _dummy_hash


@router.post("/login", response_model=StoreAdminToken, summary="Do‘kon administratoriga kirish")
async def store_admin_login(
    body: StoreAdminLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StoreAdminToken:
    if store_admin_secret() is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Do‘kon administratori kirishi sozlanmagan.")
    source = client_key(request)
    try:
        await consume_login_attempt(db, source)
    except LoginThrottled as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.detail,
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    email = normalize_email(body.email)
    admin = None if email is None else await get_store_admin_by_email(db, email)
    password_ok = False
    if password_is_acceptable(body.password):
        try:
            password_ok = verify_password(body.password, admin.password_hash if admin is not None else _timing_hash())
        except Exception:
            password_ok = False
    if admin is None or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_LOGIN_FAILED)
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hisob faol emas.")
    token = create_store_admin_token(admin.id)
    if token is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Do‘kon administratori kirishi sozlanmagan.")
    await clear_login_failures(db, source)
    return StoreAdminToken(access_token=token)


@router.get("/me", response_model=StoreAdminOut, summary="Joriy do‘kon administratori")
async def store_admin_me(admin: StoreAdmin = Depends(get_current_store_admin)) -> StoreAdminOut:
    return StoreAdminOut(id=admin.id, full_name=admin.full_name, email=admin.email, is_active=admin.is_active)
