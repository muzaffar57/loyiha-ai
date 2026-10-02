"""Yumaloq ustun.

Narx yakuniy tashqi diametrga bog‘lanadi. Qoplama koeffitsiyenti shu qoidadan olinadi.
Kapital va baza oralig‘i [min, max) — chegaralar ustma-ust tushmaydi.
"""
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.store_pricing import RoundColumnInput
from app.services.store_pricing.errors import conflict, invalid, not_configured
from app.services.store_pricing.money import PI, measure_text, money_text, parse_config_decimal, parse_request_decimal, quantize_money, read_money
from app.services.store_pricing.quote import ComponentLine, Quote, priced_quote

_DIAMETER_TOLERANCE = Decimal("0.05")


@dataclass(frozen=True)
class _Band:
    min_cm: Decimal
    max_cm: Decimal
    price: Decimal


def quote_round_column(config: dict, *, selection: RoundColumnInput, quantity: int) -> Quote:
    final_diameter = parse_request_decimal(selection.final_diameter_cm, field="Yakuniy diametr")
    existing, circumference = _existing_diameter(selection)
    height = parse_request_decimal(selection.height_m, field="Balandlik")
    if "meter_price" not in config:
        raise not_configured("Ustun tanasining metr narxi kiritilmagan.")
    meter = read_money(config["meter_price"], field="meter_price", positive=True)
    multiplier: Decimal | None = None
    if selection.coating:
        if "coating_multiplier" not in config:
            raise not_configured("Qoplama koeffitsiyenti kiritilmagan.")
        multiplier = parse_config_decimal(config["coating_multiplier"], field="coating_multiplier")
        if multiplier <= 0 or multiplier > Decimal("100"):
            raise not_configured("Qoplama koeffitsiyenti kiritilmagan.")
    capital = _piece_price(config.get("capitals"), selection.capital, final_diameter, kind="Kapital")
    base = _piece_price(config.get("bases"), selection.base, final_diameter, kind="Baza")

    def body_amount(qty: int) -> Decimal:
        amount = quantize_money(meter * height * Decimal(qty))
        if multiplier is not None:
            amount = quantize_money(amount * multiplier)
        return amount

    def build(qty: int) -> list[ComponentLine]:
        count = Decimal(qty)
        coating_note = f" × {measure_text(multiplier)}" if multiplier is not None else ""
        lines = [
            ComponentLine(
                code="body",
                label="Tana" if multiplier is None else "Qoplamali tana",
                amount=body_amount(qty),
                detail=f"{money_text(meter)} so‘m/m × {measure_text(height)} m × {qty} dona{coating_note}",
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
        "family": "round_column",
        "final_diameter_cm": measure_text(final_diameter),
        "existing_diameter_cm": measure_text(existing),
        "height_m": measure_text(height),
        "quantity": str(quantity),
        "meter_price": money_text(meter) or "",
        "coating": "true" if selection.coating else "false",
        "unit": "piece",
    }
    if circumference is not None:
        applied["circumference_cm"] = measure_text(circumference)
    if multiplier is not None:
        applied["coating_multiplier"] = measure_text(multiplier)
    if selection.capital:
        applied["capital"] = selection.capital
    if selection.base:
        applied["base"] = selection.base
    if selection.model:
        applied["model"] = selection.model.strip()
    return priced_quote(lines=build(quantity), unit_lines=build(1), applied=applied)


def _existing_diameter(selection: RoundColumnInput) -> tuple[Decimal, Decimal | None]:
    existing = (
        None
        if selection.existing_diameter_cm is None
        else parse_request_decimal(selection.existing_diameter_cm, field="Quvur diametri")
    )
    circumference = (
        None
        if selection.circumference_cm is None
        else parse_request_decimal(selection.circumference_cm, field="Aylana uzunligi")
    )
    if existing is None and circumference is None:
        raise invalid("Mavjud quvur diametri yoki aylana uzunligi kerak.")
    if existing is not None and circumference is not None:
        derived = circumference / PI
        if abs(derived - existing) > _DIAMETER_TOLERANCE:
            raise invalid("Aylana uzunligi va quvur diametri mos kelmaydi.")
    if existing is None and circumference is not None:
        existing = circumference / PI
    if existing is None:
        raise invalid("Mavjud quvur diametri yoki aylana uzunligi kerak.")
    return existing, circumference


def _piece_price(table: object, name: str | None, diameter: Decimal, *, kind: str) -> Decimal | None:
    if name is None or name.strip() == "":
        return None
    if not isinstance(table, dict) or name not in table:
        raise not_configured(f"{kind} narxi kiritilmagan.")
    return _band_price(_bands(table[name], field=name), diameter, kind=kind)


def _bands(raw: object, *, field: str) -> list[_Band]:
    if not isinstance(raw, list) or not raw:
        raise not_configured(f"{field} uchun diametr oralig‘i kiritilmagan.")
    bands: list[_Band] = []
    for item in raw:
        if not isinstance(item, dict):
            raise not_configured(f"{field} uchun diametr oralig‘i kiritilmagan.")
        minimum = parse_config_decimal(item.get("min_diameter_cm"), field="min_diameter_cm")
        maximum = parse_config_decimal(item.get("max_diameter_cm"), field="max_diameter_cm")
        price = read_money(item.get("price"), field=field)
        if minimum < 0 or maximum <= minimum:
            raise conflict("Diametr oralig‘i noto‘g‘ri.")
        bands.append(_Band(minimum, maximum, price))
    bands.sort(key=lambda band: (band.min_cm, band.max_cm))
    for previous, nxt in zip(bands, bands[1:]):
        if nxt.min_cm < previous.max_cm:
            raise conflict("Diametr oralig‘lari ustma-ust tushmasligi kerak.")
    return bands


def _band_price(bands: list[_Band], diameter: Decimal, *, kind: str) -> Decimal:
    matches = [band.price for band in bands if band.min_cm <= diameter < band.max_cm]
    if len(matches) != 1:
        raise not_configured(f"{kind} uchun bu diametr narxi kiritilmagan.")
    return matches[0]
