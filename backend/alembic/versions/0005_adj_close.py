"""prices.adj_close for split/bonus adjustment

Revision ID: 0005_adj_close
Revises: 0004_options
Create Date: 2026-07-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_adj_close"
down_revision: str | None = "0004_options"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prices",
        sa.Column("adj_close", sa.Numeric(18, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prices", "adj_close")
