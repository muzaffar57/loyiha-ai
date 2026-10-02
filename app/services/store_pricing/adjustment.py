"""Umumiy foiz faqat yakuniy sotuv narxiga qo‘llanadi.

Asl narxdan bir marta hisoblanadi. Tannarx, komponent narxi va qoplama
koeffitsiyenti o‘zgarmaydi. Narxi yo‘q natijaga foiz qo‘llab narx yaratilmaydi.
"""
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from app.services.store_pricing.errors import invalid
from app.services.store_pricing.money import quantize_money
from app.services.store_pricing.quote import Quote

STALE_PRICE_WARNING = "Oxirgi tekshirilgan narx ishlatilmoqda."
_MIN_PERCENT = Decimal("-100")
_MAX_PERCENT = Decimal("1000")


def percent_is_valid(percent: Decimal) -> bool:
    return percent.is_finite() and _MIN_PERCENT < percent <= _MAX_PERCENT


def format_percent(percent: Decimal) -> str:
    quantized = percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def adjusted_selling_amount(base: Decimal, percent: Decimal) -> Decimal:
    if not percent_is_valid(percent):
        raise invalid("Umumiy foiz sozlamasi yaroqsiz.")
    if base < 0:
        raise invalid("Asl sotuv narxi manfiy bo‘lishi mumkin emas.")
    if percent == 0:
        return quantize_money(base)
    factor = Decimal("1") + (percent / Decimal("100"))
    return quantize_money(base * factor)


def apply_selling_adjustment(quote: Quote, percent: Decimal, *, price_stale: bool = False) -> Quote:
    """Komponent qatorlarini o‘zgartirmaydi. Foiz faqat sotuv jami va dona narxiga tegadi."""
    if not percent_is_valid(percent):
        raise invalid("Umumiy foiz sozlamasi yaroqsiz.")
    applied = dict(quote.applied)
    applied["global_price_adjustment_percent"] = format_percent(percent)
    warnings = list(quote.warnings)
    if price_stale and STALE_PRICE_WARNING not in warnings:
        warnings.append(STALE_PRICE_WARNING)
    if quote.status != "PRICED" or quote.total is None or quote.requires_manual_quote:
        return replace(quote, warnings=warnings, applied=applied)
    base_total = quote.total
    base_unit = quote.unit_price
    applied["base_total"] = format(quantize_money(base_total), "f")
    if base_unit is not None:
        applied["base_unit_price"] = format(quantize_money(base_unit), "f")
    return replace(
        quote,
        unit_price=None if base_unit is None else adjusted_selling_amount(base_unit, percent),
        subtotal=base_total,
        total=adjusted_selling_amount(base_total, percent),
        components=list(quote.components),
        warnings=warnings,
        applied=applied,
    )
