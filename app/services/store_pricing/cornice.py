"""Shift karnizi va belbog‘.

Asosiy profil: 20 sm, 1 metrda 0,0138 kub.
Mijoz razmeri shu asosdan kvadrat bo‘yicha moslashadi, chunki en ham balandlik bilan o‘sadi.
1 kub narxi jadvaldagi base_meter_price. Qoplama shu narxni 2 baravar qiladi.
"""
from decimal import Decimal

from app.schemas.store_pricing import CorniceInput
from app.services.store_pricing.errors import invalid, not_configured
from app.services.store_pricing.money import measure_text, money_text, parse_request_decimal, quantize_money, read_money
from app.services.store_pricing.quote import ComponentLine, Quote, priced_quote

REFERENCE_CM = Decimal("20")
REFERENCE_KUB_PER_METER = Decimal("0.0138")
MIN_SIZE_CM = Decimal("15")


def quote_cornice(config: dict, *, selection: CorniceInput, quantity: int) -> Quote:
    size = parse_size(selection.width_cm)
    length = parse_size(selection.length_m, field="Uzunlik", minimum=None)
    if "base_meter_price" not in config:
        raise not_configured("1 kub narxi kiritilmagan.")
    kub_price = read_money(config["base_meter_price"], field="base_meter_price", positive=True)
    kub = REFERENCE_KUB_PER_METER * (size / REFERENCE_CM) ** 2
    meter = quantize_money(kub * kub_price)
    if selection.coating:
        meter = quantize_money(meter * Decimal("2"))

    def build(qty: int) -> list[ComponentLine]:
        amount = quantize_money(meter * length * Decimal(qty))
        coating = " × qoplama 2" if selection.coating else ""
        return [
            ComponentLine(
                code="body",
                label="Karniz",
                amount=amount,
                detail=f"{measure_text(kub)} kub/m × {money_text(kub_price)} so‘m × {measure_text(length)} m × {qty} dona{coating}",
            )
        ]

    return priced_quote(
        lines=build(quantity),
        unit_lines=build(1),
        applied={
            "family": "cornice",
            "width_cm": measure_text(size),
            "reference_width_cm": measure_text(REFERENCE_CM),
            "kub_per_meter": measure_text(kub),
            "kub_price": money_text(kub_price) or "",
            "meter_price": money_text(meter) or "",
            "length_m": measure_text(length),
            "quantity": str(quantity),
            "coating": "true" if selection.coating else "false",
            "unit": "meter",
        },
    )


def parse_size(value: str, *, field: str = "Razmer", minimum: Decimal | None = MIN_SIZE_CM) -> Decimal:
    amount = parse_request_decimal(value, field=field)
    if minimum is not None and amount < minimum:
        raise invalid("Razmer kamida 15 sm bo‘lishi kerak.")
    return amount
