"""Shift karnizi va belbog‘.

Yangi metr narxi = tanlangan kenglik / bazaviy kenglik × bazaviy metr narxi.
Metr narxi avval yaxlitlanadi, so‘ng uzunlik va miqdorga ko‘payadi.
Qoplama koeffitsiyenti bu turga qo‘llanmaydi.
"""
from decimal import Decimal

from app.schemas.store_pricing import CorniceInput
from app.services.store_pricing.errors import not_configured
from app.services.store_pricing.money import measure_text, money_text, parse_config_decimal, parse_request_decimal, quantize_money, read_money
from app.services.store_pricing.quote import ComponentLine, Quote, priced_quote


def quote_cornice(config: dict, *, selection: CorniceInput, quantity: int) -> Quote:
    if selection.coating:
        raise not_configured("Shift karnizi uchun qoplama narxi kiritilmagan.")
    width = parse_request_decimal(selection.width_cm, field="Kenglik")
    length = parse_request_decimal(selection.length_m, field="Uzunlik")
    if "base_width_cm" not in config or "base_meter_price" not in config:
        raise not_configured("Bazaviy kenglik yoki metr narxi kiritilmagan.")
    base_width = parse_config_decimal(config["base_width_cm"], field="base_width_cm")
    base_price = read_money(config["base_meter_price"], field="base_meter_price", positive=True)
    if base_width <= 0:
        raise not_configured("Bazaviy kenglik kiritilmagan.")
    meter = quantize_money((width / base_width) * base_price)

    def build(qty: int) -> list[ComponentLine]:
        amount = quantize_money(meter * length * Decimal(qty))
        return [
            ComponentLine(
                code="body",
                label="Karniz",
                amount=amount,
                detail=f"{money_text(meter)} so‘m/m × {measure_text(length)} m × {qty} dona",
            )
        ]

    return priced_quote(
        lines=build(quantity),
        unit_lines=build(1),
        applied={
            "family": "cornice",
            "width_cm": measure_text(width),
            "base_width_cm": measure_text(base_width),
            "base_meter_price": money_text(base_price) or "",
            "meter_price": money_text(meter) or "",
            "length_m": measure_text(length),
            "quantity": str(quantity),
            "coating": "false",
            "unit": "meter",
        },
    )
