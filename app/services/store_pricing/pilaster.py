"""Pilastr va to‘g‘ri ustun.

Tana = aniq en × qalinlik metr narxi × uzunlik × miqdor.
Kapital va baza har bir ustun uchun alohida qo‘shiladi. Interpolyatsiya yo‘q.
"""
from decimal import Decimal

from app.schemas.store_pricing import PilasterInput
from app.services.store_pricing.errors import conflict, invalid, not_configured
from app.services.store_pricing.money import measure_text, money_text, parse_config_decimal, parse_request_decimal, quantize_money, read_money
from app.services.store_pricing.quote import ComponentLine, Quote, priced_quote

WIDTHS = tuple(Decimal(item) for item in ("25", "30", "35", "40", "45", "50"))
THICKNESS = tuple(Decimal(item) for item in ("3", "3.5", "4", "4.5", "5", "5.5", "6"))


def quote_pilaster(config: dict, *, selection: PilasterInput, quantity: int) -> Quote:
    width = _allowed(
        parse_request_decimal(selection.width_cm, field="En"),
        WIDTHS,
        "En 25, 30, 35, 40, 45 yoki 50 sm bo‘lishi kerak.",
    )
    thickness = _allowed(
        parse_request_decimal(selection.thickness_cm, field="Qalinlik"),
        THICKNESS,
        "Qalinlik 3, 3.5, 4, 4.5, 5, 5.5 yoki 6 sm bo‘lishi kerak.",
    )
    length = parse_request_decimal(selection.length_m, field="Uzunlik")
    meter = _meter_price(config, width, thickness)
    capital = _optional_piece(selection.capital, config.get("capitals"), kind="Kapital")
    base = _optional_piece(selection.base, config.get("bases"), kind="Baza")

    def build(qty: int) -> list[ComponentLine]:
        count = Decimal(qty)
        lines = [
            ComponentLine(
                code="body",
                label="Tana",
                amount=quantize_money(meter * length * count),
                detail=f"{money_text(meter)} so‘m/m × {measure_text(length)} m × {qty} dona",
            )
        ]
        if capital is not None:
            lines.append(
                ComponentLine(
                    code="capital",
                    label="Kapital",
                    amount=quantize_money(capital * count),
                    detail=f"{money_text(capital)} so‘m × {qty} dona",
                )
            )
        if base is not None:
            lines.append(
                ComponentLine(
                    code="base",
                    label="Baza",
                    amount=quantize_money(base * count),
                    detail=f"{money_text(base)} so‘m × {qty} dona",
                )
            )
        return lines

    applied = {
        "family": "pilaster",
        "width_cm": measure_text(width),
        "thickness_cm": measure_text(thickness),
        "length_m": measure_text(length),
        "quantity": str(quantity),
        "meter_price": money_text(meter) or "",
        "unit": "piece",
    }
    if selection.capital:
        applied["capital"] = selection.capital
    if selection.base:
        applied["base"] = selection.base
    return priced_quote(lines=build(quantity), unit_lines=build(1), applied=applied)


def _allowed(value: Decimal, options: tuple[Decimal, ...], message: str) -> Decimal:
    for item in options:
        if value == item:
            return item
    raise invalid(message)


def _meter_price(config: dict, width: Decimal, thickness: Decimal) -> Decimal:
    table = config.get("meter_prices")
    if not isinstance(table, dict):
        raise not_configured("Bu en va qalinlik uchun metr narxi kiritilmagan.")
    nested = _match_key(table, width)
    if not isinstance(nested, dict):
        raise not_configured("Bu en va qalinlik uchun metr narxi kiritilmagan.")
    raw = _match_key(nested, thickness)
    if raw is None:
        raise not_configured("Bu en va qalinlik uchun metr narxi kiritilmagan.")
    return read_money(raw, field="meter_price", positive=True)


def _match_key(table: dict, target: Decimal) -> object | None:
    found: list[object] = []
    for key, value in table.items():
        if isinstance(key, bool) or isinstance(key, float):
            raise not_configured("O‘lcham kaliti matn ko‘rinishida kiritilishi kerak.")
        if parse_config_decimal(key, field="o‘lcham") == target:
            found.append(value)
    if len(found) > 1:
        raise conflict("Bir xil o‘lcham uchun bir nechta narx kiritilgan.")
    if not found:
        return None
    return found[0]


def _optional_piece(name: str | None, table: object, *, kind: str) -> Decimal | None:
    if name is None or name.strip() == "":
        return None
    if not isinstance(table, dict) or name not in table:
        raise not_configured(f"{kind} narxi kiritilmagan.")
    return read_money(table[name], field=kind)
