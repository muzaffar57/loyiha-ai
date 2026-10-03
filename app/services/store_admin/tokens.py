"""Do‘kon administratori uchun alohida JWT.

Yuk tashish `SECRET_KEY` va `create_access_token` ishlatilmaydi.
"""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

STORE_ADMIN_ISSUER = "penodecor-store"
STORE_ADMIN_AUDIENCE = "penodecor-store"
STORE_ADMIN_TOKEN_HOURS = 12
_ALGORITHM = "HS256"


def store_admin_secret() -> str | None:
    secret = settings.STORE_ADMIN_JWT_SECRET.strip()
    if not secret or secret == settings.SECRET_KEY:
        return None
    return secret


def create_store_admin_token(admin_id: int) -> str | None:
    secret = store_admin_secret()
    if secret is None:
        return None
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "iss": STORE_ADMIN_ISSUER,
        "aud": STORE_ADMIN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=STORE_ADMIN_TOKEN_HOURS),
    }
    token = jwt.encode(payload, secret, algorithm=_ALGORITHM)
    if isinstance(token, bytes):
        return token.decode()
    return token


def read_store_admin_id(token: str) -> int | None:
    secret = store_admin_secret()
    if secret is None or not token:
        return None
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],
            audience=STORE_ADMIN_AUDIENCE,
            issuer=STORE_ADMIN_ISSUER,
        )
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    try:
        admin_id = int(subject)
    except (TypeError, ValueError):
        return None
    if admin_id < 1:
        return None
    return admin_id
