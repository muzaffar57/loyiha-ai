"""Do‘kon narxini hisoblash.

Qoidalar mahsulot turiga qarab tanlanadi. Frontend yuborgan narx ishlatilmaydi.
Bir oilada bir nechta faol qoida bo‘lsa, hisoblash to‘xtaydi.
"""
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.store import get_product_for_pricing
from app.models.store import StoreCategory, StorePricingRule, StoreProduct
from app.models.store_enums import StorePricingRuleType, StoreProductType
from app.schemas.store_pricing import (
    PricingCalculateRequest,
    PricingComponentOut,
    PricingQuoteOut,
)
from app.services.store_pricing.adjustment import apply_selling_adjustment
from app.services.store_pricing.cornice import quote_cornice
from app.services.store_pricing.errors import PricingError, conflict, invalid, not_configured
from app.services.store_pricing.money import CURRENCY, money_text
from app.services.store_pricing.pilaster import quote_pilaster
from app.services.store_pricing.quote import Quote
from app.services.store_pricing.ready_made import quote_ready_made
from app.services.store_pricing.round_column import quote_round_column
from app.services.store_pricing.shohona import quote_shohona
from app.services.store_sheets.repository import load_selling_adjustment
from app.services.store_pricing.trim import quote_trim

_FAMILY_BY_ROOT = {
    "rom-va-eshik": "trim_set",
    "pilastrlar": "pilaster",
    "yumaloq-ustunlar": "round_column",
    "shift-karnizlari": "cornice",
    "shohona-karnizlar": "shohona",
    "tayyor-mahsulotlar": "ready_made",
}
_EXPECTED_RULE = {
    "trim_set": StorePricingRuleType.FIXED,
    "pilaster": StorePricingRuleType.DIMENSION_COMBINATION,
    "round_column": StorePricingRuleType.ROUND_COLUMN,
    "cornice": StorePricingRuleType.WIDTH_PROPORTIONAL,
    "shohona": StorePricingRuleType.MANUAL_QUOTE,
}
_BLOCKS = ("trim", "pilaster", "round_column", "cornice", "shohona")


async def calculate_store_price(db: AsyncSession, payload: PricingCalculateRequest) -> PricingQuoteOut:
    percent, stale = await load_selling_adjustment(db)
    product = await get_product_for_pricing(db, payload.product_id)
    if product is None:
        raise PricingError("PRODUCT_NOT_FOUND", "Mahsulot topilmadi.", 404)
    return calculate_quote(product, payload, adjustment_percent=percent, price_stale=stale)


def calculate_quote(
    product: StoreProduct,
    payload: PricingCalculateRequest,
    *,
    adjustment_percent: Decimal | None = None,
    price_stale: bool = False,
) -> PricingQuoteOut:
    if not product.is_active or not _category_is_open(product.category):
        raise PricingError("PRODUCT_INACTIVE", "Mahsulot hisoblash uchun ochiq emas.", 404)
    family = _family_of(product)
    _check_blocks(family, payload)
    rule: StorePricingRule | None = None
    if family == "ready_made":
        quote = quote_ready_made(product, payload.quantity)
    elif family == "shohona":
        rule = _select_rule(product, StorePricingRuleType.MANUAL_QUOTE, required=False)
        quote = quote_shohona(payload.shohona, payload.quantity, rule_id=None if rule is None else rule.id)
    elif family == "unknown":
        raise not_configured("Bu mahsulot turi uchun narx hisoblash sozlanmagan.")
    else:
        rule = _select_rule(product, _EXPECTED_RULE[family], required=True)
        if rule is None:
            raise not_configured("Tanlangan model uchun narx kiritilmagan.")
        config = _config(rule, family)
        if family == "trim_set" and payload.trim is not None:
            quote = quote_trim(config, category_slug=product.category.slug, selection=payload.trim, quantity=payload.quantity)
        elif family == "pilaster" and payload.pilaster is not None:
            quote = quote_pilaster(config, selection=payload.pilaster, quantity=payload.quantity)
        elif family == "round_column" and payload.round_column is not None:
            quote = quote_round_column(config, selection=payload.round_column, quantity=payload.quantity)
        elif family == "cornice" and payload.cornice is not None:
            quote = quote_cornice(config, selection=payload.cornice, quantity=payload.quantity)
        else:
            raise invalid("Mahsulot turiga mos o‘lchamlar yuborilmadi.")
        if rule.id is not None and "rule_id" not in quote.applied:
            quote.applied["rule_id"] = str(rule.id)
    percent = Decimal("0") if adjustment_percent is None else adjustment_percent
    quote = apply_selling_adjustment(quote, percent, price_stale=price_stale)
    return _to_out(quote)


def _family_of(product: StoreProduct) -> str:
    if StoreProductType(product.product_type) is StoreProductType.READY_MADE:
        return "ready_made"
    return _FAMILY_BY_ROOT.get(_root_category(product.category).slug, "unknown")


def _root_category(category: StoreCategory) -> StoreCategory:
    current = category
    seen: set[int] = set()
    while current.parent_id is not None and current.parent is not None:
        if current.id is not None:
            if current.id in seen:
                break
            seen.add(current.id)
        current = current.parent
    return current


def _category_is_open(category: StoreCategory) -> bool:
    current: StoreCategory | None = category
    seen: set[int] = set()
    while current is not None:
        if current.id is not None:
            if current.id in seen:
                return False
            seen.add(current.id)
        if not current.is_active:
            return False
        if current.parent_id is not None and "parent" not in current.__dict__:
            return False
        current = current.parent
    return True


def _check_blocks(family: str, payload: PricingCalculateRequest) -> None:
    present = [name for name in _BLOCKS if getattr(payload, name) is not None]
    if family in ("ready_made", "unknown"):
        return
    if family == "shohona":
        if any(name != "shohona" for name in present):
            raise invalid("Shohona karniz uchun boshqa mahsulot o‘lchamlari yuborilmaydi.")
        return
    expected = {
        "trim_set": "trim",
        "pilaster": "pilaster",
        "round_column": "round_column",
        "cornice": "cornice",
    }.get(family)
    if expected is None or present != [expected]:
        raise invalid("Mahsulot turiga mos o‘lchamlar yuborilmadi.")


def _select_rule(product: StoreProduct, expected: StorePricingRuleType, *, required: bool) -> StorePricingRule | None:
    for owner in _scopes(product):
        active = [rule for rule in _rules(owner) if rule.is_active]
        if not active:
            continue
        if len(active) > 1:
            raise conflict("Bir xil parametrlar uchun bir nechta faol narx qoidasi bor.")
        rule = active[0]
        if StorePricingRuleType(rule.rule_type) is not expected:
            raise conflict("Narx qoidasi mahsulot turiga mos kelmaydi.")
        return rule
    if required:
        raise not_configured("Tanlangan model uchun narx kiritilmagan.")
    return None


def _scopes(product: StoreProduct) -> list[StoreProduct | StoreCategory]:
    scopes: list[StoreProduct | StoreCategory] = [product]
    category: StoreCategory | None = product.category
    seen: set[int] = set()
    while category is not None:
        if category.id is not None:
            if category.id in seen:
                break
            seen.add(category.id)
        scopes.append(category)
        if category.parent_id is not None and "parent" not in category.__dict__:
            break
        category = category.parent
    return scopes


def _rules(owner: StoreProduct | StoreCategory) -> Sequence[StorePricingRule]:
    loaded = owner.__dict__.get("pricing_rules")
    if not loaded:
        return []
    return list(loaded)


def _config(rule: StorePricingRule, family: str) -> dict:
    raw = rule.config
    if not isinstance(raw, dict):
        raise not_configured("Narx qoidasi to‘liq emas.")
    declared = raw.get("family")
    if declared is not None and declared != family:
        raise conflict("Narx qoidasi mahsulot turiga mos kelmaydi.")
    return raw


def _to_out(quote: Quote) -> PricingQuoteOut:
    status: Literal["PRICED", "MANUAL_QUOTE_REQUIRED"] = (
        "PRICED" if quote.status == "PRICED" else "MANUAL_QUOTE_REQUIRED"
    )
    return PricingQuoteOut(
        status=status,
        currency=CURRENCY,
        unit_price=money_text(quote.unit_price),
        subtotal=money_text(quote.subtotal),
        total=money_text(quote.total),
        components=[
            PricingComponentOut(code=line.code, label=line.label, amount=money_text(line.amount), detail=line.detail)
            for line in quote.components
        ],
        requires_manual_quote=quote.requires_manual_quote,
        warnings=list(quote.warnings),
        applied={key: str(value) for key, value in quote.applied.items()},
    )
