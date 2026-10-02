"""Pul va o‘lcham yordamchilari.

Pul hisobi float ishlatmaydi. Yaxlitlash bitta joyda: 0.01, ROUND_HALF_UP.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

from app.services.store_pricing.errors import invalid, not_configured

TWOPLACES = Decimal("0.01")
PI = Decimal("3.14159265358979323846")
MAX_MEASURE = Decimal("1000")
MAX_MONEY = Decimal("9999999999.99")
CURRENCY: Literal["UZS"] = "UZS"


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def money_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(quantize_money(value), "f")


def measure_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _decimal_from_text(text: str) -> Decimal:
    cleaned = text.strip()
    if not cleaned or any(char in cleaned for char in "eE"):
        raise InvalidOperation
    return Decimal(cleaned)


def parse_request_decimal(value: str, *, field: str) -> Decimal:
    try:
        amount = _decimal_from_text(value)
    except (InvalidOperation, AttributeError):
        raise invalid(f"{field} noto‘g‘ri.") from None
    if not amount.is_finite() or amount <= 0 or amount > MAX_MEASURE:
        raise invalid(f"{field} musbat bo‘lishi kerak.")
    return amount


def parse_config_decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float) or value is None:
        raise not_configured(f"{field} matn ko‘rinishida kiritilishi kerak.")
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        try:
            amount = _decimal_from_text(value)
        except InvalidOperation:
            raise not_configured(f"{field} matn ko‘rinishida kiritilishi kerak.") from None
    else:
        raise not_configured(f"{field} matn ko‘rinishida kiritilishi kerak.")
    if not amount.is_finite():
        raise not_configured(f"{field} matn ko‘rinishida kiritilishi kerak.")
    return amount


def read_money(value: object, *, field: str, positive: bool = False) -> Decimal:
    amount = parse_config_decimal(value, field=field)
    if amount > MAX_MONEY or (positive and amount <= 0) or amount < 0:
        raise not_configured(f"{field} narxi kiritilmagan.")
    return amount


def money_from_column(value: object) -> Decimal:
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, bool) or value is None:
        raise not_configured("Mahsulot narxi kiritilmagan.")
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, float):
        amount = Decimal(format(value, ".2f"))
    elif isinstance(value, str):
        try:
            amount = _decimal_from_text(value)
        except InvalidOperation:
            raise not_configured("Mahsulot narxi kiritilmagan.") from None
    else:
        raise not_configured("Mahsulot narxi kiritilmagan.")
    if not amount.is_finite() or amount <= 0 or amount > MAX_MONEY:
        raise not_configured("Mahsulot narxi kiritilmagan.")
    return quantize_money(amount)
