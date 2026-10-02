"""store catalog tables

Revision ID: a1b7c3d9e4f2
Revises: e9a1b2c3d4e6
Create Date: 2026-10-02 09:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.store.catalog_seed import seed_store_categories

revision: str = "a1b7c3d9e4f2"
down_revision: Union[str, None] = "e9a1b2c3d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["store_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_store_categories_slug"),
    )
    op.create_index("ix_store_categories_parent_id", "store_categories", ["parent_id"])
    op.create_index("ix_store_categories_slug", "store_categories", ["slug"])

    op.create_table(
        "store_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("images", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dimensions", sa.String(length=160), nullable=True),
        sa.Column("selling_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("available_quantity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "product_type IN ('made_to_order', 'ready_made')",
            name="ck_store_products_type",
        ),
        sa.CheckConstraint("unit IN ('piece', 'meter', 'set')", name="ck_store_products_unit"),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(["category_id"], ["store_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_store_products_slug"),
        sa.UniqueConstraint("sku", name="uq_store_products_sku"),
    )
    op.create_index("ix_store_products_category_id", "store_products", ["category_id"])
    op.create_index("ix_store_products_slug", "store_products", ["slug"])
    op.create_index("ix_store_products_product_type", "store_products", ["product_type"])
    op.create_index("ix_store_products_is_active", "store_products", ["is_active"])
    op.create_index("ix_store_products_is_featured", "store_products", ["is_featured"])

    op.create_table(
        "store_pricing_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("rule_type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("config", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "rule_type IN ('fixed', 'per_meter', 'width_proportional', 'dimension_combination', 'round_column', 'addon', 'manual_quote')",
            name="ck_store_pricing_rules_type",
        ),
        sa.CheckConstraint(
            "(product_id IS NOT NULL AND category_id IS NULL) OR (product_id IS NULL AND category_id IS NOT NULL)",
            name="ck_store_pricing_rules_single_target",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["store_categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["store_products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_store_pricing_rules_product_id", "store_pricing_rules", ["product_id"])
    op.create_index("ix_store_pricing_rules_category_id", "store_pricing_rules", ["category_id"])
    op.create_index("ix_store_pricing_rules_rule_type", "store_pricing_rules", ["rule_type"])

    seed_store_categories(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_store_pricing_rules_rule_type", table_name="store_pricing_rules")
    op.drop_index("ix_store_pricing_rules_category_id", table_name="store_pricing_rules")
    op.drop_index("ix_store_pricing_rules_product_id", table_name="store_pricing_rules")
    op.drop_table("store_pricing_rules")
    op.drop_index("ix_store_products_is_featured", table_name="store_products")
    op.drop_index("ix_store_products_is_active", table_name="store_products")
    op.drop_index("ix_store_products_product_type", table_name="store_products")
    op.drop_index("ix_store_products_slug", table_name="store_products")
    op.drop_index("ix_store_products_category_id", table_name="store_products")
    op.drop_table("store_products")
    op.drop_index("ix_store_categories_slug", table_name="store_categories")
    op.drop_index("ix_store_categories_parent_id", table_name="store_categories")
    op.drop_table("store_categories")
