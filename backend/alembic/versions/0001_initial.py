"""initial: stocks, prices, ingest_runs

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False, unique=True),
        sa.Column("isin", sa.String(16)),
        sa.Column("name", sa.String(255)),
        sa.Column("sector", sa.String(128)),
        sa.Column("industry", sa.String(128)),
        sa.Column("market_cap_cr", sa.Numeric(18, 2)),
        sa.Column("in_nifty50", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("in_nifty500", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_fno", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("listed_date", sa.Date),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_stocks_symbol", "stocks", ["symbol"])
    op.create_index("ix_stocks_isin", "stocks", ["isin"])

    op.create_table(
        "prices",
        sa.Column(
            "stock_id",
            sa.Integer,
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("trade_date", sa.Date, primary_key=True),
        sa.Column("open", sa.Numeric(18, 4), nullable=False),
        sa.Column("high", sa.Numeric(18, 4), nullable=False),
        sa.Column("low", sa.Numeric(18, 4), nullable=False),
        sa.Column("close", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.BigInteger),
        sa.Column("turnover_cr", sa.Numeric(18, 4)),
        sa.Column("delivery_qty", sa.BigInteger),
        sa.Column("delivery_pct", sa.Numeric(6, 3)),
    )
    op.create_index("ix_prices_stock_date_desc", "prices", ["stock_id", "trade_date"])

    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_name", sa.String(64), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("rows_written", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text),
    )
    op.create_index("ix_ingest_runs_job_name", "ingest_runs", ["job_name"])


def downgrade() -> None:
    op.drop_index("ix_ingest_runs_job_name", table_name="ingest_runs")
    op.drop_table("ingest_runs")
    op.drop_index("ix_prices_stock_date_desc", table_name="prices")
    op.drop_table("prices")
    op.drop_index("ix_stocks_isin", table_name="stocks")
    op.drop_index("ix_stocks_symbol", table_name="stocks")
    op.drop_table("stocks")
