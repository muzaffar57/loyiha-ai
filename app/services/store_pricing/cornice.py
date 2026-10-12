"""Shift karnizi va belbog‘.

Har bir karnizning o‘z balandligi va eni bor. 15×9 va 15×13 bir xil kub emas.
20 sm gacha en balandlik bilan proporsional o‘sadi.
20 sm dan keyin en to‘liq proporsiya bilan yo‘g‘onlashmaydi:
25 sm gacha +1 sm, undan keyin +2 sm.
1 metr kub = (balandlik sm / 100) × (en sm / 100) / 2.
1 kub narxi jadvaldagi base_meter_price. Qoplama shu narxni 2 baravar qiladi.
"""
from decimal import Decimal

from app.schemas.store_pricing import CorniceInput
from app.services.store_pricing.errors import invalid, not_configured
from app.services.store_pricing.money import (
    measure_text,
    money_text,
    parse_config_decimal,
    parse_request_decimal,
    quantize_money,
    read_money,
)
from app.services.store_pricing.quote import ComponentLine, Quote, priced_quote

MIN_SIZE_CM = Decimal("15")
PROPORTIONAL_LIMIT_CM = Decimal("20")
SMALL_EXTRA_LIMIT_CM = Decimal("25")
CM = Decimal("100")


def quote_cornice(config: dict, *, selection: CorniceInput, quantity: int) -> Quote:
    size = parse_size(selection.width_cm)
    length = parse_size(selection.length_m, field="Uzunlik", minimum=None)
    if "base_height_cm" not in config or "base_width_cm" not in config or "base_meter_price" not in config:
        raise not_configured("Karniz o‘lchami yoki 1 kub narxi kiritilmagan.")
    base_height = parse_config_decimal(config["base_height_cm"], field="base_height_cm")
    base_width = parse_config_decimal(config["base_width_cm"], field="base_width_cm")
    if base_height <= 0 or base_width <= 0:
        raise not_configured("Karniz balandligi yoki eni kiritilmagan.")
    kub_price = read_money(config["base_meter_price"], field="base_meter_price", positive=True)
    profile_width = profile_width_cm(size, base_height, base_width)
    kub = (size / CM) * (profile_width / CM) / Decimal("2")
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
            "base_height_cm": measure_text(base_height),
            "base_width_cm": measure_text(base_width),
            "profile_width_cm": measure_text(profile_width),
            "kub_per_meter": measure_text(kub),
            "kub_price": money_text(kub_price) or "",
            "meter_price": money_text(meter) or "",
            "length_m": measure_text(length),
            "quantity": str(quantity),
            "coating": "true" if selection.coating else "false",
            "unit": "meter",
        },
    )


def profile_width_cm(size: Decimal, base_height: Decimal, base_width: Decimal) -> Decimal:
    if size <= PROPORTIONAL_LIMIT_CM:
        return base_width * (size / base_height)
    width_at_20 = base_width * (PROPORTIONAL_LIMIT_CM / base_height)
    extra = Decimal("1") if size <= SMALL_EXTRA_LIMIT_CM else Decimal("2")
    return width_at_20 + extra


def parse_size(value: str, *, field: str = "Razmer", minimum: Decimal | None = MIN_SIZE_CM) -> Decimal:
    amount = parse_request_decimal(value, field=field)
    if minimum is not None and amount < minimum:
        raise invalid("Razmer kamida 15 sm bo‘lishi kerak.")
    return amount
