"""Rom va eshik bezagi.

Komplekt = tanlangan komponentlar. Avtomatik chegirma yo‘q.
Qo‘shimcha metr faqat shu komponentning metr narxiga ko‘payadi.
"""
import re
from decimal import Decimal

from app.schemas.store_pricing import TrimInput
from app.services.store_pricing.errors import invalid, not_configured
from app.services.store_pricing.money import measure_text, money_text, parse_request_decimal, quantize_money, read_money
from app.services.store_pricing.quote import ComponentLine, Quote, priced_quote

_ORDER = ("cornice", "jamb", "sill")
_LABELS = {
    "cornice": "Yuqori karniz",
    "jamb": "Yon nalichniklar",
    "sill": "Pastki tokcha",
}
_ADDON_LABELS = {
    "kalvak": "Kalvak",
    "karona": "Karona",
}
_ADDON_CODE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def quote_trim(config: dict, *, category_slug: str, selection: TrimInput, quantity: int) -> Quote:
    opening = _opening(config, category_slug)
    components = list(selection.components)
    if len(components) != len(set(components)):
        raise invalid("Komponent takrorlanmasligi kerak.")
    addons = list(selection.addons)
    if len(addons) != len(set(addons)):
        raise invalid("Qo‘shimcha bezak takrorlanmasligi kerak.")
    if opening == "door" and ("sill" in components or "sill" in selection.extra_meters):
        raise invalid("Eshik modelida podokonnik bo‘lmaydi.")
    if not components:
        raise invalid("Kamida bitta komponent tanlanishi kerak.")

    extra: dict[str, Decimal] = {}
    for key, raw in selection.extra_meters.items():
        if key not in _ORDER:
            raise invalid("Qo‘shimcha uzunlik komponenti noto‘g‘ri.")
        if key not in components:
            raise invalid("Qo‘shimcha metr faqat tanlangan komponent uchun kiritiladi.")
        extra[key] = parse_request_decimal(raw, field="Qo‘shimcha uzunlik")

    size_row = _size_row(config, selection.size)
    extra_table = size_row.get("extra_meter")
    rates: dict[str, Decimal] = {}
    for code in _ORDER:
        if code not in components:
            continue
        if code not in size_row:
            raise not_configured("Tanlangan komponent uchun narx kiritilmagan.")
        rates[code] = read_money(size_row[code], field=code)
    extra_rates: dict[str, Decimal] = {}
    for code in _ORDER:
        if code not in extra:
            continue
        if not isinstance(extra_table, dict) or code not in extra_table:
            raise not_configured("Qo‘shimcha metr narxi kiritilmagan.")
        extra_rates[code] = read_money(extra_table[code], field=f"{code}_meter", positive=True)

    addon_table = config.get("addons") if addons else {}
    addon_rates: list[tuple[str, Decimal]] = []
    for code in addons:
        if not _ADDON_CODE.fullmatch(code):
            raise invalid("Qo‘shimcha bezak kodi noto‘g‘ri.")
        if not isinstance(addon_table, dict) or code not in addon_table:
            raise not_configured("Qo‘shimcha bezak narxi kiritilmagan.")
        addon_rates.append((code, read_money(addon_table[code], field=code)))

    selected = [code for code in _ORDER if code in rates]

    def build(qty: int) -> list[ComponentLine]:
        lines: list[ComponentLine] = []
        count = Decimal(qty)
        for code in selected:
            rate = rates[code]
            lines.append(
                ComponentLine(
                    code=code,
                    label=_LABELS[code],
                    amount=quantize_money(rate * count),
                    detail=f"{money_text(rate)} so‘m × {qty} dona",
                )
            )
        for code in selected:
            if code not in extra_rates:
                continue
            rate = extra_rates[code]
            meters = extra[code]
            lines.append(
                ComponentLine(
                    code=f"extra_{code}",
                    label=f"{_LABELS[code]} — qo‘shimcha uzunlik",
                    amount=quantize_money(rate * meters * count),
                    detail=f"{measure_text(meters)} m × {money_text(rate)} so‘m/m × {qty} dona",
                )
            )
        for code, rate in addon_rates:
            lines.append(
                ComponentLine(
                    code=f"addon_{code}",
                    label=_ADDON_LABELS.get(code, code),
                    amount=quantize_money(rate * count),
                    detail=f"{money_text(rate)} so‘m × {qty} dona",
                )
            )
        return lines

    return priced_quote(
        lines=build(quantity),
        unit_lines=build(1),
        applied={
            "family": "trim_set",
            "opening": opening,
            "size": selection.size,
            "quantity": str(quantity),
            "unit": "set",
            "components": ",".join(selected),
            **({"addons": ",".join(code for code, _rate in addon_rates)} if addon_rates else {}),
        },
    )


def _opening(config: dict, category_slug: str) -> str:
    if category_slug == "eshik-bezaklari":
        return "door"
    opening = config.get("opening")
    if opening not in ("window", "door"):
        raise not_configured("Rom turi, deraza yoki eshik, kiritilmagan.")
    return str(opening)


def _size_row(config: dict, size: str) -> dict:
    sizes = config.get("sizes")
    if not isinstance(sizes, dict):
        raise not_configured("O‘lcham narxlari kiritilmagan.")
    row = sizes.get(size)
    if not isinstance(row, dict):
        raise not_configured("Tanlangan o‘lcham uchun narx kiritilmagan.")
    return row
