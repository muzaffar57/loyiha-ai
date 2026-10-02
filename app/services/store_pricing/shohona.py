"""Shohona karniz.

Avtomatik narx chiqarilmaydi. Javob keyingi administrator taklifi uchun parametrlarni saqlaydi.
"""
from app.schemas.store_pricing import ShohonaInput
from app.services.store_pricing.money import measure_text, parse_request_decimal
from app.services.store_pricing.quote import Quote


def quote_shohona(selection: ShohonaInput | None, quantity: int, *, rule_id: int | None) -> Quote:
    applied: dict[str, str] = {
        "family": "shohona",
        "quantity": str(quantity),
        "quote_mode": "manual",
        "unit": "piece",
    }
    if rule_id is not None:
        applied["rule_id"] = str(rule_id)
    if selection is not None:
        if selection.length_m is not None:
            length = parse_request_decimal(selection.length_m, field="Uzunlik")
            applied["length_m"] = measure_text(length)
        if selection.size_note is not None and selection.size_note.strip():
            applied["size_note"] = selection.size_note.strip()
        if selection.model is not None and selection.model.strip():
            applied["model"] = selection.model.strip()
        applied["coating"] = "true" if selection.coating else "false"
    return Quote(
        status="MANUAL_QUOTE_REQUIRED",
        unit_price=None,
        subtotal=None,
        total=None,
        components=[],
        requires_manual_quote=True,
        warnings=["Narx individual hisoblanadi."],
        applied=applied,
    )
