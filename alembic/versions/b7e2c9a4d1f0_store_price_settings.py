"""store price settings

Revision ID: b7e2c9a4d1f0
Revises: a1b7c3d9e4f2
Create Date: 2026-10-02 10:50:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2c9a4d1f0"
down_revision: Union[str, None] = "a1b7c3d9e4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_price_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("global_price_adjustment_percent", sa.Numeric(8, 2), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="UZS", nullable=False),
        sa.Column("sheet_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="never", nullable=False),
        sa.Column("stale", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "global_price_adjustment_percent > -100 AND global_price_adjustment_percent <= 1000",
            name="ck_store_price_settings_percent",
        ),
        sa.CheckConstraint(
            "status IN ('never', 'running', 'ok', 'error')",
            name="ck_store_price_settings_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("store_price_settings")
