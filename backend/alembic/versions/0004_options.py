"""options_snapshots + iv_rank

Revision ID: 0004_options
Revises: 0003_earnings
Create Date: 2026-07-19

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_options"
down_revision: str | None = "0003_earnings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "options_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "stock_id",
            sa.Integer,
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("expiry_date", sa.Date, nullable=False),
        sa.Column("days_to_expiry", sa.Integer, nullable=False),
        sa.Column("spot", sa.Numeric(18, 4)),
        sa.Column("atm_strike", sa.Numeric(18, 4)),
        sa.Column("atm_call_iv", sa.Numeric(8, 3)),
        sa.Column("atm_put_iv", sa.Numeric(8, 3)),
        sa.Column("atm_iv", sa.Numeric(8, 3)),
        sa.Column("atm_call_oi", sa.BigInteger),
        sa.Column("atm_put_oi", sa.BigInteger),
        sa.Column("total_call_oi", sa.BigInteger),
        sa.Column("total_put_oi", sa.BigInteger),
        sa.Column("total_call_volume", sa.BigInteger),
        sa.Column("total_put_volume", sa.BigInteger),
        sa.Column("pcr_oi", sa.Numeric(8, 3)),
        sa.Column("pcr_volume", sa.Numeric(8, 3)),
        sa.Column("implied_move_pct", sa.Numeric(8, 3)),
        sa.Column("raw_chain", sa.JSON),
        sa.UniqueConstraint(
            "stock_id", "snapshot_date", "expiry_date", name="uq_options_snapshot"
        ),
    )
    op.create_index("ix_options_stock_id", "options_snapshots", ["stock_id"])
    op.create_index("ix_options_snapshot_date", "options_snapshots", ["snapshot_date"])

    op.create_table(
        "iv_rank",
        sa.Column(
            "stock_id",
            sa.Integer,
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("as_of_date", sa.Date, primary_key=True),
        sa.Column("iv_current", sa.Numeric(8, 3)),
        sa.Column("iv_rank_252", sa.Numeric(6, 3)),
        sa.Column("iv_percentile_252", sa.Numeric(6, 3)),
        sa.Column("n_sessions", sa.Integer, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("iv_rank")
    op.drop_index("ix_options_snapshot_date", table_name="options_snapshots")
    op.drop_index("ix_options_stock_id", table_name="options_snapshots")
    op.drop_table("options_snapshots")
