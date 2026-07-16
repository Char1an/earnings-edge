from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FiiDiiFlow(Base):
    """Market-wide daily FII/DII net cash + F&O positioning."""

    __tablename__ = "fii_dii_flows"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    fii_cash_net_cr: Mapped[float | None] = mapped_column(Numeric(14, 2))
    dii_cash_net_cr: Mapped[float | None] = mapped_column(Numeric(14, 2))
    fii_index_futures_net_cr: Mapped[float | None] = mapped_column(Numeric(14, 2))
    fii_stock_futures_net_cr: Mapped[float | None] = mapped_column(Numeric(14, 2))
    fii_index_options_net_cr: Mapped[float | None] = mapped_column(Numeric(14, 2))
    fii_stock_options_net_cr: Mapped[float | None] = mapped_column(Numeric(14, 2))
    source: Mapped[str | None] = mapped_column(String(32))
