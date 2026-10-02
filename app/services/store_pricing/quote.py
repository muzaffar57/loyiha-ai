from dataclasses import dataclass
from decimal import Decimal

from app.services.store_pricing.money import quantize_money


@dataclass(frozen=True)
class ComponentLine:
    code: str
    label: str
    amount: Decimal
    detail: str


@dataclass(frozen=True)
class Quote:
    status: str
    unit_price: Decimal | None
    subtotal: Decimal | None
    total: Decimal | None
    components: list[ComponentLine]
    requires_manual_quote: bool
    warnings: list[str]
    applied: dict[str, str]


def priced_quote(
    *,
    lines: list[ComponentLine],
    unit_lines: list[ComponentLine],
    applied: dict[str, str],
) -> Quote:
    total = quantize_money(sum((line.amount for line in lines), Decimal("0")))
    unit = quantize_money(sum((line.amount for line in unit_lines), Decimal("0")))
    return Quote(
        status="PRICED",
        unit_price=unit,
        subtotal=total,
        total=total,
        components=lines,
        requires_manual_quote=False,
        warnings=[],
        applied=applied,
    )
