"""earnings_events + earnings_reactions + upcoming_earnings

Revision ID: 0003_earnings
Revises: 0002_deals_flows
Create Date: 2026-07-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_earnings"
down_revision: str | None = "0002_deals_flows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "earnings_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "stock_id",
            sa.Integer,
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fiscal_period", sa.String(16), nullable=False),
        sa.Column("quarter_end", sa.Date, nullable=False),
        sa.Column("announcement_date", sa.Date),
        sa.Column("revenue_cr", sa.Numeric(18, 2)),
        sa.Column("pat_cr", sa.Numeric(18, 2)),
        sa.Column("eps", sa.Numeric(12, 4)),
        sa.Column("opm_pct", sa.Numeric(8, 3)),
        sa.Column("yoy_revenue_growth", sa.Numeric(10, 3)),
        sa.Column("yoy_pat_growth", sa.Numeric(10, 3)),
        sa.Column("qoq_revenue_growth", sa.Numeric(10, 3)),
        sa.Column("qoq_pat_growth", sa.Numeric(10, 3)),
        sa.Column("source", sa.String(32), nullable=False, server_default="screener"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("stock_id", "fiscal_period", name="uq_earnings_stock_period"),
    )
    op.create_index("ix_earnings_stock_id", "earnings_events", ["stock_id"])
    op.create_index("ix_earnings_announcement_date", "earnings_events", ["announcement_date"])
    op.create_index("ix_earnings_stock_qend", "earnings_events", ["stock_id", "quarter_end"])

    op.create_table(
        "earnings_reactions",
        sa.Column(
            "earnings_event_id",
            sa.Integer,
            sa.ForeignKey("earnings_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("pre_close", sa.Numeric(18, 4)),
        sa.Column("gap_open_pct", sa.Numeric(8, 3)),
        sa.Column("day1_close_pct", sa.Numeric(8, 3)),
        sa.Column("day3_close_pct", sa.Numeric(8, 3)),
        sa.Column("day5_close_pct", sa.Numeric(8, 3)),
        sa.Column("day1_high_pct", sa.Numeric(8, 3)),
        sa.Column("day1_low_pct", sa.Numeric(8, 3)),
        sa.Column("volume_spike", sa.Numeric(8, 3)),
        sa.Column("detection_method", sa.String(16), nullable=False, server_default="heuristic"),
        sa.Column("detection_confidence", sa.Numeric(5, 3)),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "upcoming_earnings",
        sa.Column(
            "stock_id",
            sa.Integer,
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("expected_date", sa.Date, primary_key=True),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("raw", sa.JSON),
    )


def downgrade() -> None:
    op.drop_table("upcoming_earnings")
    op.drop_table("earnings_reactions")
    op.drop_index("ix_earnings_stock_qend", table_name="earnings_events")
    op.drop_index("ix_earnings_announcement_date", table_name="earnings_events")
    op.drop_index("ix_earnings_stock_id", table_name="earnings_events")
    op.drop_table("earnings_events")
