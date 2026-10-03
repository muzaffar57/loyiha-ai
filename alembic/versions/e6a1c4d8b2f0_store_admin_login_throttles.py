"""store admin login throttles

Revision ID: e6a1c4d8b2f0
Revises: c4e8a1b7d2f3
Create Date: 2026-10-02 13:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6a1c4d8b2f0"
down_revision: Union[str, None] = "c4e8a1b7d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_admin_login_throttles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_key", sa.String(length=64), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_key", name="uq_store_admin_login_throttles_client_key"),
    )
    op.create_index("ix_store_admin_login_throttles_client_key", "store_admin_login_throttles", ["client_key"])


def downgrade() -> None:
    op.drop_index("ix_store_admin_login_throttles_client_key", table_name="store_admin_login_throttles")
    op.drop_table("store_admin_login_throttles")
