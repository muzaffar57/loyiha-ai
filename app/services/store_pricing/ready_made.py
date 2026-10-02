"""Tayyor mahsulot.

Narx administrator kiritgan sotuv narxidan olinadi. Qoldiq tekshiriladi, lekin kamaytirilmaydi.
"""
from decimal import Decimal

from app.models.store import StoreProduct
from app.services.store_pricing.errors import PricingError, not_configured
from app.services.store_pricing.money import money_from_column, money_text, quantize_money
from app.services.store_pricing.quote import ComponentLine, Quote, priced_quote


def quote_ready_made(product: StoreProduct, quantity: int) -> Quote:
    price = money_from_column(product.selling_price)
    available = product.available_quantity
    if not isinstance(available, int) or isinstance(available, bool):
        raise not_configured("Ombordagi qoldiq kiritilmagan.")
    if quantity > available:
        raise PricingError("INSUFFICIENT_STOCK", "So‘ralgan miqdor ombordagi qoldiqdan oshadi.", 409)
    total = quantize_money(price * Decimal(quantity))
    unit_line = ComponentLine(
        code="item",
        label=product.name,
        amount=price,
        detail=f"{money_text(price)} so‘m × 1 dona",
    )
    line = ComponentLine(
        code="item",
        label=product.name,
        amount=total,
        detail=f"{money_text(price)} so‘m × {quantity} dona",
    )
    applied = {
        "family": "ready_made",
        "quantity": str(quantity),
        "available_quantity": str(available),
        "unit": "piece",
    }
    if product.sku:
        applied["sku"] = product.sku
    return priced_quote(lines=[line], unit_lines=[unit_line], applied=applied)
