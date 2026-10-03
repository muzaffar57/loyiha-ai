"""store admins

Revision ID: c4e8a1b7d2f3
Revises: b7e2c9a4d1f0
Create Date: 2026-10-02 11:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1b7d2f3"
down_revision: Union[str, None] = "b7e2c9a4d1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_store_admins_email"),
    )
    op.create_index("ix_store_admins_email", "store_admins", ["email"])


def downgrade() -> None:
    op.drop_index("ix_store_admins_email", table_name="store_admins")
    op.drop_table("store_admins")
