"""PenodecorPro katalogi.

Yuk tashish jadvallariga bog‘lanmaydi. Narx qoidalari shu modellarda saqlanadi
va serverdagi pricing service orqali hisoblanadi.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.db.base_class import Base
from app.models.store_enums import StorePricingRuleType, StoreProductType, StoreUnit

_RULE_TYPES = ", ".join(f"'{item.value}'" for item in StorePricingRuleType)


class StoreCategory(Base):
    __tablename__ = "store_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("store_categories.id", ondelete="RESTRICT"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    parent: Mapped["StoreCategory | None"] = relationship(
        back_populates="children",
        remote_side="StoreCategory.id",
    )
    children: Mapped[list["StoreCategory"]] = relationship(
        back_populates="parent",
        order_by="StoreCategory.sort_order",
    )
    products: Mapped[list["StoreProduct"]] = relationship(back_populates="category")
    pricing_rules: Mapped[list["StorePricingRule"]] = relationship(back_populates="category")


class StoreProduct(Base):
    __tablename__ = "store_products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_store_products_sku"),
        CheckConstraint(
            "product_type IN ('made_to_order', 'ready_made')",
            name="ck_store_products_type",
        ),
        CheckConstraint(
            "unit IN ('piece', 'meter', 'set')",
            name="ck_store_products_unit",
        ),
        CheckConstraint(
            "("
            "product_type = 'ready_made' "
            "AND sku IS NOT NULL AND length(trim(sku)) > 0 "
            "AND selling_price IS NOT NULL AND selling_price >= 0 "
            "AND available_quantity IS NOT NULL AND available_quantity >= 0"
            ") OR ("
            "product_type = 'made_to_order' "
            "AND selling_price IS NULL AND available_quantity IS NULL"
            ")",
            name="ck_store_products_stock_fields",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("store_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    images: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    product_type: Mapped[StoreProductType] = mapped_column(String(32), nullable=False, index=True)
    unit: Mapped[StoreUnit] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dimensions: Mapped[str | None] = mapped_column(String(160), nullable=True)
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    available_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category: Mapped[StoreCategory] = relationship(back_populates="products")
    pricing_rules: Mapped[list["StorePricingRule"]] = relationship(back_populates="product")


class StorePricingRule(Base):
    """Administrator kiritadigan narx qoidasi. Hisobni pricing service bajaradi."""

    __tablename__ = "store_pricing_rules"
    __table_args__ = (
        CheckConstraint(
            f"rule_type IN ({_RULE_TYPES})",
            name="ck_store_pricing_rules_type",
        ),
        CheckConstraint(
            "(product_id IS NOT NULL AND category_id IS NULL) OR (product_id IS NULL AND category_id IS NOT NULL)",
            name="ck_store_pricing_rules_single_target",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("store_products.id", ondelete="CASCADE"),
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("store_categories.id", ondelete="CASCADE"),
        index=True,
    )
    rule_type: Mapped[StorePricingRuleType] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped[StoreProduct | None] = relationship(back_populates="pricing_rules")
    category: Mapped[StoreCategory | None] = relationship(back_populates="pricing_rules")
