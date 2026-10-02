"""Do‘kon sinxronlash ruxsati.

Yuk tashish admin roli va JWT ishlatilmaydi. Kalit bo‘lmasa endpoint ochiq emas.
"""
import hmac

from fastapi import Header, HTTPException

from app.core.config import settings


def require_store_sync_token(authorization: str | None = Header(default=None)) -> None:
    expected = settings.STORE_SHEETS_SYNC_TOKEN
    if not expected:
        raise HTTPException(
            status_code=503,
            detail={"code": "SYNC_NOT_CONFIGURED", "message": "Do‘kon sinxronlash kaliti sozlanmagan."},
        )
    provided = ""
    if authorization and authorization.startswith("Bearer "):
        provided = authorization.removeprefix("Bearer ").strip()
    if not provided or len(provided) != len(expected) or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Sinxronlash uchun ruxsat yo‘q."},
        )
