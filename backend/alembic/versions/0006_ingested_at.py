"""prices.ingested_at — stamp of last ingest write (date-shift cleanup)

Revision ID: 0006_ingested_at
Revises: 0005_adj_close
Create Date: 2026-08-04

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_ingested_at"
down_revision: str | None = "0005_adj_close"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prices",
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prices", "ingested_at")
