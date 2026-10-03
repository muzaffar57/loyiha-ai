"""Alembic uchun: barcha modellarni bir joyda import qilib, ularning
`Base.metadata`ga ro'yxatdan o'tishini ta'minlaydi.

Diqqat: modellarning o'zi Base klassini `app.db.base_class`dan import qiladi
(shu fayldan emas) -- aks holda circular import xatosi yuzaga keladi.
"""
from app.db.base_class import Base
from app.models.user import User  # noqa: F401
from app.models.cargo import Cargo  # noqa: F401
from app.models.cargo_photo import CargoPhoto  # noqa: F401
from app.models.driver_offer import DriverOffer  # noqa: F401
from app.models.store import StoreCategory, StorePricingRule, StoreProduct  # noqa: F401
from app.models.store_settings import StorePriceSettings  # noqa: F401
from app.models.store_admin import StoreAdmin  # noqa: F401
from app.models.store_admin_throttle import StoreAdminLoginThrottle  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Cargo",
    "CargoPhoto",
    "DriverOffer",
    "StoreCategory",
    "StoreProduct",
    "StorePricingRule",
    "StorePriceSettings",
    "StoreAdmin",
    "StoreAdminLoginThrottle",
]
