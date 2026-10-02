"""PenodecorPro do‘koni uchun qat’iy ro‘yxatlar.

Yuk tashish enumlaridan alohida. Narx formulalari service qatlamida.
"""
import enum


class StoreProductType(str, enum.Enum):
    MADE_TO_ORDER = "made_to_order"
    READY_MADE = "ready_made"


class StoreUnit(str, enum.Enum):
    PIECE = "piece"
    METER = "meter"
    SET = "set"


class StorePricingRuleType(str, enum.Enum):
    FIXED = "fixed"
    PER_METER = "per_meter"
    WIDTH_PROPORTIONAL = "width_proportional"
    DIMENSION_COMBINATION = "dimension_combination"
    ROUND_COLUMN = "round_column"
    ADDON = "addon"
    MANUAL_QUOTE = "manual_quote"
