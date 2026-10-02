"""Google Sheets varaq va ustun sxemasi.

Narxlar matn sifatida kiritiladi: o‘nlik nuqta `.`, valyuta belgisisiz.
Bo‘sh katak komponent yo‘q degani. `0` yozilmaydi. Jadvalga narx yozilmaydi.
"""

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

SETTINGS_SHEET = "Sozlamalar"
ROM_SHEET = "Rom_Eshik"
PILASTER_SHEET = "Pilastrlar"
ROUND_SHEET = "Yumaloq_Ustunlar"
CORNICE_SHEET = "Shift_Karnizlari"
SHOHONA_SHEET = "Shohona_Karnizlar"
READY_SHEET = "Tayyor_Mahsulotlar"

SHEET_ROOTS = {
    ROM_SHEET: "rom-va-eshik",
    PILASTER_SHEET: "pilastrlar",
    ROUND_SHEET: "yumaloq-ustunlar",
    CORNICE_SHEET: "shift-karnizlari",
    SHOHONA_SHEET: "shohona-karnizlar",
    READY_SHEET: "tayyor-mahsulotlar",
}

SETTINGS_COLUMNS = ("key", "value")
ROM_COLUMNS = (
    "product_slug",
    "model",
    "opening",
    "size",
    "cornice_price",
    "jamb_price",
    "sill_price",
    "extra_meter_cornice",
    "extra_meter_jamb",
    "extra_meter_sill",
    "addon_1_code",
    "addon_1_price",
    "addon_2_code",
    "addon_2_price",
    "is_active",
)
PILASTER_COLUMNS = (
    "product_slug",
    "model",
    "width_cm",
    "thickness_cm",
    "meter_price",
    "capital_model",
    "capital_price",
    "base_model",
    "base_price",
    "is_active",
)
ROUND_COLUMNS = (
    "product_slug",
    "model",
    "meter_price",
    "coating_multiplier",
    "capital_model",
    "capital_min_diameter_cm",
    "capital_max_diameter_cm",
    "capital_price",
    "base_model",
    "base_min_diameter_cm",
    "base_max_diameter_cm",
    "base_price",
    "is_active",
)
CORNICE_COLUMNS = (
    "product_slug",
    "model",
    "base_width_cm",
    "base_meter_price",
    "is_active",
)
SHOHONA_COLUMNS = (
    "product_slug",
    "model",
    "description",
    "size_requirements",
    "is_active",
)
READY_COLUMNS = (
    "product_slug",
    "sku",
    "selling_price",
    "available_quantity",
    "is_active",
)

SHEET_COLUMNS = {
    SETTINGS_SHEET: SETTINGS_COLUMNS,
    ROM_SHEET: ROM_COLUMNS,
    PILASTER_SHEET: PILASTER_COLUMNS,
    ROUND_SHEET: ROUND_COLUMNS,
    CORNICE_SHEET: CORNICE_COLUMNS,
    SHOHONA_SHEET: SHOHONA_COLUMNS,
    READY_SHEET: READY_COLUMNS,
}

REQUIRED_SETTINGS = ("global_price_adjustment_percent", "currency", "updated_at")
