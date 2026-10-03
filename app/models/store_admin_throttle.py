"""Do‘kon administratori login urinishlari.

Hisoblagich barcha workerlar uchun umumiy bazada turadi.
Email saqlanmaydi.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class StoreAdminLoginThrottle(Base):
    __tablename__ = "store_admin_login_throttles"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
