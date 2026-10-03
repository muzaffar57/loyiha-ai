"""Do‘kon admin login uchun mijoz manzili.

X-Forwarded-For faqat sozlangan ishonchli proxy ortidan o‘qiladi.
Manzil aniqlanmasa, umumiy cheklov kaliti qaytadi.
"""
import ipaddress

from fastapi import Request

from app.core.config import settings

UNKNOWN_CLIENT = "unknown"


def client_key(request: Request) -> str:
    try:
        peer = _host(request.client.host if request.client is not None else None)
        trusted = _trusted_proxies()
        if not trusted or peer not in trusted:
            return peer or UNKNOWN_CLIENT
        forwarded = request.headers.get("x-forwarded-for")
        if not forwarded:
            return UNKNOWN_CLIENT
        return _forwarded_client(forwarded, trusted) or UNKNOWN_CLIENT
    except Exception:
        return UNKNOWN_CLIENT


def _trusted_proxies() -> frozenset[str]:
    found: set[str] = set()
    for piece in settings.STORE_ADMIN_TRUSTED_PROXIES.split(","):
        host = _host(piece)
        if host is not None:
            found.add(host)
    return frozenset(found)


def _forwarded_client(header: str, trusted: frozenset[str]) -> str | None:
    hops: list[str] = []
    for piece in header.split(",")[:20]:
        host = _host(piece)
        if host is not None:
            hops.append(host)
    for hop in reversed(hops):
        if hop not in trusted:
            return hop
    return None


def _host(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if text.startswith("[") and "]" in text:
        text = text[1 : text.index("]")]
    elif text.count(":") == 1 and "." in text:
        text = text.split(":", 1)[0]
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return None
