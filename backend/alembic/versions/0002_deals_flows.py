"""deals + fii_dii_flows

Revision ID: 0002_deals_flows
Revises: 0001_initial
Create Date: 2026-07-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_deals_flows"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "stock_id",
            sa.Integer,
            sa.ForeignKey("stocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("deal_type", sa.String(8), nullable=False),
        sa.Column("exchange", sa.String(4), nullable=False),
        sa.Column("client_name", sa.String(255)),
        sa.Column("buy_sell", sa.String(4), nullable=False),
        sa.Column("quantity", sa.BigInteger, nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=False),
        sa.Column("value_cr", sa.Numeric(18, 4)),
    )
    op.create_index("ix_deals_stock_id", "deals", ["stock_id"])
    op.create_index("ix_deals_trade_date", "deals", ["trade_date"])
    op.create_index("ix_deals_stock_date", "deals", ["stock_id", "trade_date"])
    op.create_index("ix_deals_date_type", "deals", ["trade_date", "deal_type"])
    # Natural dedupe key: same stock, date, type, client, side, qty, price
    op.create_unique_constraint(
        "uq_deals_natural",
        "deals",
        ["trade_date", "deal_type", "exchange", "stock_id", "client_name", "buy_sell", "quantity", "price"],
    )

    op.create_table(
        "fii_dii_flows",
        sa.Column("trade_date", sa.Date, primary_key=True),
        sa.Column("fii_cash_net_cr", sa.Numeric(14, 2)),
        sa.Column("dii_cash_net_cr", sa.Numeric(14, 2)),
        sa.Column("fii_index_futures_net_cr", sa.Numeric(14, 2)),
        sa.Column("fii_stock_futures_net_cr", sa.Numeric(14, 2)),
        sa.Column("fii_index_options_net_cr", sa.Numeric(14, 2)),
        sa.Column("fii_stock_options_net_cr", sa.Numeric(14, 2)),
        sa.Column("source", sa.String(32)),
    )


def downgrade() -> None:
    op.drop_table("fii_dii_flows")
    op.drop_constraint("uq_deals_natural", "deals", type_="unique")
    op.drop_index("ix_deals_date_type", table_name="deals")
    op.drop_index("ix_deals_stock_date", table_name="deals")
    op.drop_index("ix_deals_trade_date", table_name="deals")
    op.drop_index("ix_deals_stock_id", table_name="deals")
    op.drop_table("deals")
