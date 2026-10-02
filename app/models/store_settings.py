"""Do‘konning umumiy sotuv foizi va Google Sheets sinxron holati.

Asl narxlar shu jadvalda saqlanmaydi. Foiz hisob paytida qo‘llanadi.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class StorePriceSettings(Base):
    __tablename__ = "store_price_settings"
    __table_args__ = (
        CheckConstraint(
            "global_price_adjustment_percent > -100 AND global_price_adjustment_percent <= 1000",
            name="ck_store_price_settings_percent",
        ),
        CheckConstraint(
            "status IN ('never', 'running', 'ok', 'error')",
            name="ck_store_price_settings_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    global_price_adjustment_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UZS", server_default="UZS")
    sheet_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="never", server_default="never")
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
