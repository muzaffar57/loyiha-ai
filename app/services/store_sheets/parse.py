"""Google Sheets qatorlarini narx konfiguratsiyasiga aylantiradi.

Float qabul qilinmaydi. Manfiy va nol narx, yaroqsiz foiz va ustma-ust
diametr oralig‘i butun sinxronni to‘xtatadi.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.models.store_enums import StorePricingRuleType
from app.services.store_pricing.money import quantize_money
from app.services.store_pricing.pilaster import THICKNESS, WIDTHS
from app.services.store_sheets.errors import SheetValidationError
from app.services.store_sheets.layout import (
    CORNICE_SHEET,
    PILASTER_SHEET,
    READY_SHEET,
    REQUIRED_SETTINGS,
    ROM_SHEET,
    ROUND_SHEET,
    SETTINGS_SHEET,
    SHEET_COLUMNS,
    SHOHONA_SHEET,
)

_ADDON_CODE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass
class RuleDraft:
    product_slug: str
    rule_type: StorePricingRuleType
    name: str
    config: dict
    is_active: bool


@dataclass
class StockDraft:
    product_slug: str
    sku: str
    selling_price: str
    available_quantity: int
    is_active: bool


@dataclass
class WorkbookDraft:
    percent: Decimal
    currency: str
    updated_at: datetime
    rules: list[RuleDraft] = field(default_factory=list)
    stock: list[StockDraft] = field(default_factory=list)


class _Errors:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, sheet: str, row: int | None, message: str) -> None:
        where = sheet if row is None else f"{sheet} qator {row}"
        self.items.append(f"{where}: {message}")


def parse_workbook(tables: dict[str, list[list[object]]]) -> WorkbookDraft:
    errors = _Errors()
    records = {name: _records(name, tables.get(name), errors) for name in SHEET_COLUMNS}
    percent, currency, updated_at = _settings(records[SETTINGS_SHEET], errors)
    rules: list[RuleDraft] = []
    rules.extend(_rom(records[ROM_SHEET], errors))
    rules.extend(_pilasters(records[PILASTER_SHEET], errors))
    rules.extend(_rounds(records[ROUND_SHEET], errors))
    rules.extend(_cornices(records[CORNICE_SHEET], errors))
    rules.extend(_shohona(records[SHOHONA_SHEET], errors))
    stock = _ready(records[READY_SHEET], errors)
    _unique_slugs(rules, stock, errors)
    if errors.items or percent is None or currency is None or updated_at is None:
        raise SheetValidationError(errors.items or ["Sozlamalar to‘liq emas."])
    return WorkbookDraft(percent=percent, currency=currency, updated_at=updated_at, rules=rules, stock=stock)


def _records(sheet: str, rows: list[list[object]] | None, errors: _Errors) -> list[tuple[int, dict[str, str]]]:
    if rows is None:
        errors.add(sheet, None, "varaq topilmadi.")
        return []
    expected = list(SHEET_COLUMNS[sheet])
    if not rows:
        errors.add(sheet, None, "ustun sarlavhasi yo‘q.")
        return []
    header_cells = rows[0]
    if any(not isinstance(cell, str) for cell in header_cells):
        errors.add(sheet, 1, "ustun nomi matn bo‘lishi kerak.")
        return []
    header = [cell.strip() for cell in header_cells]
    if len(header) != len(set(header)) or sorted(header) != sorted(expected):
        errors.add(sheet, 1, "ustunlar hujjatdagi sxemaga mos emas.")
        return []
    index = {name: header.index(name) for name in expected}
    found: list[tuple[int, dict[str, str]]] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if any(not isinstance(cell, str) for cell in row):
            errors.add(sheet, row_number, "qiymat matn bo‘lishi kerak.")
            continue
        if not any(cell.strip() for cell in row):
            continue
        if len(row) > len(header):
            errors.add(sheet, row_number, "ortiqcha ustun bor.")
            continue
        padded = list(row) + [""] * (len(header) - len(row))
        found.append((row_number, {name: padded[index[name]].strip() for name in expected}))
    return found


def _settings(rows: list[tuple[int, dict[str, str]]], errors: _Errors) -> tuple[Decimal | None, str | None, datetime | None]:
    values: dict[str, str] = {}
    for row_number, row in rows:
        key = row["key"]
        if not key:
            errors.add(SETTINGS_SHEET, row_number, "kalit bo‘sh.")
            continue
        if key in values:
            errors.add(SETTINGS_SHEET, row_number, "kalit takrorlangan.")
            continue
        values[key] = row["value"]
    allowed = set(REQUIRED_SETTINGS)
    for key in values:
        if key not in allowed:
            errors.add(SETTINGS_SHEET, None, f"{key} sozlamasi tanilmagan.")
    for key in REQUIRED_SETTINGS:
        if key not in values or not values[key]:
            errors.add(SETTINGS_SHEET, None, f"{key} kiritilmagan.")
    percent = _percent(values.get("global_price_adjustment_percent", ""), errors)
    currency = values.get("currency", "")
    if currency and currency != "UZS":
        errors.add(SETTINGS_SHEET, None, "valyuta UZS bo‘lishi kerak.")
        currency = None
    updated = _timestamp(values.get("updated_at", ""), errors)
    if percent is None or not currency or updated is None:
        return None, None, None
    return percent, currency, updated


def _percent(value: str, errors: _Errors) -> Decimal | None:
    text = value.strip().replace(" ", "")
    if text.endswith("%"):
        text = text[:-1]
    if text.startswith("+"):
        text = text[1:]
    if not text or any(char in text for char in "eE"):
        errors.add(SETTINGS_SHEET, None, "umumiy foiz yaroqsiz.")
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        errors.add(SETTINGS_SHEET, None, "umumiy foiz yaroqsiz.")
        return None
    if not amount.is_finite() or amount <= Decimal("-100") or amount > Decimal("1000"):
        errors.add(SETTINGS_SHEET, None, "umumiy foiz yaroqsiz.")
        return None
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _timestamp(value: str, errors: _Errors) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        errors.add(SETTINGS_SHEET, None, "updated_at yaroqsiz.")
        return None
    return parsed


def _rom(rows: list[tuple[int, dict[str, str]]], errors: _Errors) -> list[RuleDraft]:
    grouped: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for row_number, row in rows:
        grouped.setdefault(row["product_slug"], []).append((row_number, row))
    drafts: list[RuleDraft] = []
    for slug, group in grouped.items():
        if not _slug_ok(slug):
            errors.add(ROM_SHEET, group[0][0], "mahsulot identifikatori yaroqsiz.")
            continue
        openings = {row["opening"] for _, row in group}
        active_flags = {_bool_cell(row["is_active"], ROM_SHEET, number, errors) for number, row in group}
        models = {row["model"] for _, row in group}
        if openings != {"window"} and openings != {"door"}:
            errors.add(ROM_SHEET, group[0][0], "ochilish turi window yoki door bo‘lishi kerak.")
            continue
        if len(models) != 1 or not next(iter(models)).strip():
            errors.add(ROM_SHEET, group[0][0], "model bir xil bo‘lishi kerak.")
            continue
        if None in active_flags or len(active_flags) != 1:
            errors.add(ROM_SHEET, group[0][0], "faollik holati bir xil bo‘lishi kerak.")
            continue
        opening = next(iter(openings))
        sizes: dict[str, dict] = {}
        addons: dict[str, str] = {}
        seen_sizes: set[str] = set()
        broken = False
        for row_number, row in group:
            size = row["size"]
            if size not in {"S", "M", "L"} or size in seen_sizes:
                errors.add(ROM_SHEET, row_number, "o‘lcham S, M yoki L bo‘lib, takrorlanmasligi kerak.")
                broken = True
                break
            seen_sizes.add(size)
            prices: dict[str, str] = {}
            for code, column in (("cornice", "cornice_price"), ("jamb", "jamb_price"), ("sill", "sill_price")):
                if opening == "door" and code == "sill" and row[column]:
                    errors.add(ROM_SHEET, row_number, "eshik modelida podokonnik bo‘lmaydi.")
                    broken = True
                    break
                parsed = _price(row[column], ROM_SHEET, row_number, errors, required=False)
                if parsed == "":
                    broken = True
                    break
                if parsed is not None:
                    prices[code] = parsed
            if broken:
                break
            extra: dict[str, str] = {}
            for code, column in (
                ("cornice", "extra_meter_cornice"),
                ("jamb", "extra_meter_jamb"),
                ("sill", "extra_meter_sill"),
            ):
                if opening == "door" and code == "sill" and row[column]:
                    errors.add(ROM_SHEET, row_number, "eshik modelida podokonnik bo‘lmaydi.")
                    broken = True
                    break
                parsed = _price(row[column], ROM_SHEET, row_number, errors, required=False)
                if parsed == "":
                    broken = True
                    break
                if parsed is not None:
                    extra[code] = parsed
            if broken:
                break
            if not prices:
                errors.add(ROM_SHEET, row_number, "kamida bitta komponent narxi kerak.")
                broken = True
                break
            if extra:
                prices["extra_meter"] = extra
            sizes[size] = prices
            if not _merge_addons(row, addons, ROM_SHEET, row_number, errors):
                broken = True
                break
        if broken or not sizes:
            continue
        drafts.append(
            RuleDraft(
                product_slug=slug,
                rule_type=StorePricingRuleType.FIXED,
                name=next(iter(models)).strip()[:160],
                config={"family": "trim_set", "opening": opening, "sizes": sizes, "addons": addons},
                is_active=True in active_flags,
            )
        )
    return drafts


def _merge_addons(row: dict[str, str], addons: dict[str, str], sheet: str, row_number: int, errors: _Errors) -> bool:
    for code_key, price_key in (("addon_1_code", "addon_1_price"), ("addon_2_code", "addon_2_price")):
        code = row[code_key]
        price = row[price_key]
        if not code and not price:
            continue
        if not code or not price or not _ADDON_CODE.fullmatch(code):
            errors.add(sheet, row_number, "qo‘shimcha bezak kodi va narxi birga kiritilishi kerak.")
            return False
        parsed = _price(price, sheet, row_number, errors, required=True)
        if not parsed:
            return False
        previous = addons.get(code)
        if previous is not None and previous != parsed:
            errors.add(sheet, row_number, "qo‘shimcha bezak narxi takroriy qatorda boshqacha.")
            return False
        addons[code] = parsed
    return True


def _pilasters(rows: list[tuple[int, dict[str, str]]], errors: _Errors) -> list[RuleDraft]:
    return _grouped_dimension(PILASTER_SHEET, rows, errors, kind="pilaster")


def _grouped_dimension(sheet: str, rows: list[tuple[int, dict[str, str]]], errors: _Errors, *, kind: str) -> list[RuleDraft]:
    grouped: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for item in rows:
        grouped.setdefault(item[1]["product_slug"], []).append(item)
    drafts: list[RuleDraft] = []
    for slug, group in grouped.items():
        if not _slug_ok(slug):
            errors.add(sheet, group[0][0], "mahsulot identifikatori yaroqsiz.")
            continue
        draft = _one_pilaster(slug, group, errors) if kind == "pilaster" else None
        if draft is not None:
            drafts.append(draft)
    return drafts


def _one_pilaster(slug: str, group: list[tuple[int, dict[str, str]]], errors: _Errors) -> RuleDraft | None:
    models = {row["model"].strip() for _, row in group}
    active = {_bool_cell(row["is_active"], PILASTER_SHEET, number, errors) for number, row in group}
    if len(models) != 1 or not next(iter(models)) or None in active or len(active) != 1:
        errors.add(PILASTER_SHEET, group[0][0], "model va faollik bir xil bo‘lishi kerak.")
        return None
    meter_prices: dict[str, dict[str, str]] = {}
    capitals: dict[str, str] = {}
    bases: dict[str, str] = {}
    seen: set[tuple[str, str]] = set()
    for row_number, row in group:
        width = _choice(row["width_cm"], WIDTHS, PILASTER_SHEET, row_number, "en", errors)
        thickness = _choice(row["thickness_cm"], THICKNESS, PILASTER_SHEET, row_number, "qalinlik", errors)
        price = _price(row["meter_price"], PILASTER_SHEET, row_number, errors, required=True)
        if not width or not thickness or not price:
            return None
        pair = (width, thickness)
        if pair in seen:
            errors.add(PILASTER_SHEET, row_number, "en va qalinlik kombinatsiyasi takrorlangan.")
            return None
        seen.add(pair)
        meter_prices.setdefault(width, {})[thickness] = price
        if not _named_price(row["capital_model"], row["capital_price"], capitals, PILASTER_SHEET, row_number, errors):
            return None
        if not _named_price(row["base_model"], row["base_price"], bases, PILASTER_SHEET, row_number, errors):
            return None
    return RuleDraft(
        product_slug=slug,
        rule_type=StorePricingRuleType.DIMENSION_COMBINATION,
        name=next(iter(models))[:160],
        config={"family": "pilaster", "meter_prices": meter_prices, "capitals": capitals, "bases": bases},
        is_active=True in active,
    )


def _rounds(rows: list[tuple[int, dict[str, str]]], errors: _Errors) -> list[RuleDraft]:
    grouped: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for item in rows:
        grouped.setdefault(item[1]["product_slug"], []).append(item)
    drafts: list[RuleDraft] = []
    for slug, group in grouped.items():
        if not _slug_ok(slug):
            errors.add(ROUND_SHEET, group[0][0], "mahsulot identifikatori yaroqsiz.")
            continue
        draft = _one_round(slug, group, errors)
        if draft is not None:
            drafts.append(draft)
    return drafts


def _one_round(slug: str, group: list[tuple[int, dict[str, str]]], errors: _Errors) -> RuleDraft | None:
    models = {row["model"].strip() for _, row in group}
    active = {_bool_cell(row["is_active"], ROUND_SHEET, number, errors) for number, row in group}
    meters = {row["meter_price"] for _, row in group}
    coatings = {row["coating_multiplier"] for _, row in group}
    if len(models) != 1 or not next(iter(models)) or None in active or len(active) != 1 or len(meters) != 1 or len(coatings) != 1:
        errors.add(ROUND_SHEET, group[0][0], "model, metr narxi, qoplama va faollik bir xil bo‘lishi kerak.")
        return None
    meter = _price(next(iter(meters)), ROUND_SHEET, group[0][0], errors, required=True)
    coating_raw = next(iter(coatings))
    coating: str | None = None
    if coating_raw:
        coating = _multiplier(coating_raw, group[0][0], errors)
        if coating is None:
            return None
    if not meter:
        return None
    capitals: dict[str, list[dict[str, str]]] = {}
    bases: dict[str, list[dict[str, str]]] = {}
    for row_number, row in group:
        if not _band(row, "capital", capitals, row_number, errors):
            return None
        if not _band(row, "base", bases, row_number, errors):
            return None
    if not _bands_ok(capitals, "kapital", group[0][0], errors) or not _bands_ok(bases, "baza", group[0][0], errors):
        return None
    config: dict = {"family": "round_column", "meter_price": meter, "capitals": capitals, "bases": bases}
    if coating is not None:
        config["coating_multiplier"] = coating
    return RuleDraft(
        product_slug=slug,
        rule_type=StorePricingRuleType.ROUND_COLUMN,
        name=next(iter(models))[:160],
        config=config,
        is_active=True in active,
    )


def _cornices(rows: list[tuple[int, dict[str, str]]], errors: _Errors) -> list[RuleDraft]:
    seen: set[str] = set()
    drafts: list[RuleDraft] = []
    for row_number, row in rows:
        slug = row["product_slug"]
        if not _slug_ok(slug) or slug in seen:
            errors.add(CORNICE_SHEET, row_number, "mahsulot identifikatori yaroqsiz yoki takrorlangan.")
            continue
        seen.add(slug)
        active = _bool_cell(row["is_active"], CORNICE_SHEET, row_number, errors)
        width = _measure(row["base_width_cm"], CORNICE_SHEET, row_number, errors)
        price = _price(row["base_meter_price"], CORNICE_SHEET, row_number, errors, required=True)
        model = row["model"].strip()
        if active is None or width is None or not price or not model:
            if not model:
                errors.add(CORNICE_SHEET, row_number, "model kiritilmagan.")
            continue
        drafts.append(
            RuleDraft(
                product_slug=slug,
                rule_type=StorePricingRuleType.WIDTH_PROPORTIONAL,
                name=model[:160],
                config={"family": "cornice", "base_width_cm": width, "base_meter_price": price},
                is_active=active,
            )
        )
    return drafts


def _shohona(rows: list[tuple[int, dict[str, str]]], errors: _Errors) -> list[RuleDraft]:
    seen: set[str] = set()
    drafts: list[RuleDraft] = []
    for row_number, row in rows:
        slug = row["product_slug"]
        if not _slug_ok(slug) or slug in seen:
            errors.add(SHOHONA_SHEET, row_number, "mahsulot identifikatori yaroqsiz yoki takrorlangan.")
            continue
        seen.add(slug)
        active = _bool_cell(row["is_active"], SHOHONA_SHEET, row_number, errors)
        model = row["model"].strip()
        if active is None or not model:
            if not model:
                errors.add(SHOHONA_SHEET, row_number, "model kiritilmagan.")
            continue
        drafts.append(
            RuleDraft(
                product_slug=slug,
                rule_type=StorePricingRuleType.MANUAL_QUOTE,
                name=model[:160],
                config={
                    "family": "shohona",
                    "model": model[:160],
                    "description": row["description"].strip()[:500],
                    "size_requirements": row["size_requirements"].strip()[:500],
                },
                is_active=active,
            )
        )
    return drafts


def _ready(rows: list[tuple[int, dict[str, str]]], errors: _Errors) -> list[StockDraft]:
    seen: set[str] = set()
    drafts: list[StockDraft] = []
    for row_number, row in rows:
        slug = row["product_slug"]
        sku = row["sku"].strip()
        if not _slug_ok(slug) or slug in seen:
            errors.add(READY_SHEET, row_number, "mahsulot identifikatori yaroqsiz yoki takrorlangan.")
            continue
        seen.add(slug)
        active = _bool_cell(row["is_active"], READY_SHEET, row_number, errors)
        price = _price(row["selling_price"], READY_SHEET, row_number, errors, required=True)
        quantity = _quantity(row["available_quantity"], row_number, errors)
        if active is None or not price or quantity is None or not sku:
            if not sku:
                errors.add(READY_SHEET, row_number, "SKU kiritilmagan.")
            continue
        drafts.append(StockDraft(slug, sku, price, quantity, active))
    return drafts


def _unique_slugs(rules: list[RuleDraft], stock: list[StockDraft], errors: _Errors) -> None:
    seen: set[str] = set()
    for draft in [*rules, *stock]:
        if draft.product_slug in seen:
            errors.add("workbook", None, f"{draft.product_slug} bir nechta varaqda takrorlangan.")
        seen.add(draft.product_slug)


def _slug_ok(value: str) -> bool:
    return bool(_SLUG.fullmatch(value or ""))


def _bool_cell(value: str, sheet: str, row_number: int, errors: _Errors) -> bool | None:
    text = value.strip().lower().replace("ʻ", "'").replace("’", "'").replace("‘", "'")
    if text in {"true", "1", "ha", "yes"}:
        return True
    if text in {"false", "0", "yoq", "yo'q", "no"}:
        return False
    errors.add(sheet, row_number, "faollik holati yaroqsiz.")
    return None


def _price(value: str, sheet: str, row_number: int, errors: _Errors, *, required: bool) -> str | None:
    text = value.strip().replace(" ", "")
    if not text:
        return None if not required else ""
    if any(char in text for char in "eE,%") or text.count(".") > 1:
        errors.add(sheet, row_number, "narx matn ko‘rinishida va musbat bo‘lishi kerak.")
        return ""
    try:
        amount = Decimal(text)
    except InvalidOperation:
        errors.add(sheet, row_number, "narx matn ko‘rinishida va musbat bo‘lishi kerak.")
        return ""
    if not amount.is_finite() or amount <= 0:
        errors.add(sheet, row_number, "narx musbat bo‘lishi kerak.")
        return ""
    return format(quantize_money(amount), "f")


def _measure(value: str, sheet: str, row_number: int, errors: _Errors) -> str | None:
    text = value.strip()
    if not text or any(char in text for char in "eE"):
        errors.add(sheet, row_number, "o‘lcham yaroqsiz.")
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        errors.add(sheet, row_number, "o‘lcham yaroqsiz.")
        return None
    if not amount.is_finite() or amount <= 0 or amount > Decimal("1000"):
        errors.add(sheet, row_number, "o‘lcham yaroqsiz.")
        return None
    rendered = format(amount, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _choice(value: str, options: tuple[Decimal, ...], sheet: str, row_number: int, label: str, errors: _Errors) -> str | None:
    parsed = _measure(value, sheet, row_number, errors)
    if parsed is None:
        return None
    amount = Decimal(parsed)
    for item in options:
        if amount == item:
            text = format(item, "f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            return text
    errors.add(sheet, row_number, f"{label} ruxsat etilgan ro‘yxatda yo‘q.")
    return None


def _named_price(name: str, price: str, target: dict[str, str], sheet: str, row_number: int, errors: _Errors) -> bool:
    label = name.strip()
    if not label and not price.strip():
        return True
    parsed = _price(price, sheet, row_number, errors, required=True)
    if not label or not parsed:
        if not label:
            errors.add(sheet, row_number, "model nomi va narxi birga kiritilishi kerak.")
        return False
    previous = target.get(label)
    if previous is not None and previous != parsed:
        errors.add(sheet, row_number, "bir xil model narxi boshqacha kiritilgan.")
        return False
    target[label] = parsed
    return True


def _multiplier(value: str, row_number: int, errors: _Errors) -> str | None:
    text = value.strip()
    if not text or any(char in text for char in "eE"):
        errors.add(ROUND_SHEET, row_number, "qoplama koeffitsiyenti yaroqsiz.")
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        errors.add(ROUND_SHEET, row_number, "qoplama koeffitsiyenti yaroqsiz.")
        return None
    if not amount.is_finite() or amount <= 0 or amount > Decimal("100"):
        errors.add(ROUND_SHEET, row_number, "qoplama koeffitsiyenti yaroqsiz.")
        return None
    rendered = format(amount, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _band(row: dict[str, str], prefix: str, target: dict[str, list[dict[str, str]]], row_number: int, errors: _Errors) -> bool:
    model = row[f"{prefix}_model"].strip()
    minimum = row[f"{prefix}_min_diameter_cm"].strip()
    maximum = row[f"{prefix}_max_diameter_cm"].strip()
    price = row[f"{prefix}_price"].strip()
    if not model and not minimum and not maximum and not price:
        return True
    parsed_min = _measure(minimum, ROUND_SHEET, row_number, errors) if minimum else None
    parsed_max = _measure(maximum, ROUND_SHEET, row_number, errors) if maximum else None
    parsed_price = _price(price, ROUND_SHEET, row_number, errors, required=True) if price else ""
    if not model or not parsed_min or not parsed_max or not parsed_price:
        errors.add(ROUND_SHEET, row_number, f"{prefix} modeli, oralig‘i va narxi birga kiritilishi kerak.")
        return False
    if Decimal(parsed_max) <= Decimal(parsed_min):
        errors.add(ROUND_SHEET, row_number, "diametr oralig‘i noto‘g‘ri.")
        return False
    target.setdefault(model, []).append(
        {"min_diameter_cm": parsed_min, "max_diameter_cm": parsed_max, "price": parsed_price}
    )
    return True


def _bands_ok(groups: dict[str, list[dict[str, str]]], kind: str, row_number: int, errors: _Errors) -> bool:
    for model, bands in groups.items():
        ordered = sorted(bands, key=lambda item: (Decimal(item["min_diameter_cm"]), Decimal(item["max_diameter_cm"])))
        for previous, nxt in zip(ordered, ordered[1:]):
            if Decimal(nxt["min_diameter_cm"]) < Decimal(previous["max_diameter_cm"]):
                errors.add(ROUND_SHEET, row_number, f"{kind} {model} diametr oralig‘i ustma-ust tushadi.")
                return False
        groups[model] = ordered
    return True


def _quantity(value: str, row_number: int, errors: _Errors) -> int | None:
    text = value.strip()
    if not text.isdigit():
        errors.add(READY_SHEET, row_number, "qoldiq musbat butun son yoki nol bo‘lishi kerak.")
        return None
    amount = int(text)
    if amount > 1_000_000:
        errors.add(READY_SHEET, row_number, "qoldiq juda katta.")
        return None
    return amount
