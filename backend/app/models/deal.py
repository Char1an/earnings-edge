from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Deal(Base):
    """Bulk or block deal reported by NSE/BSE end-of-day."""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), index=True
    )
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    deal_type: Mapped[str] = mapped_column(String(8))          # 'bulk' | 'block'
    exchange: Mapped[str] = mapped_column(String(4))           # 'NSE' | 'BSE'
    client_name: Mapped[str | None] = mapped_column(String(255))
    buy_sell: Mapped[str] = mapped_column(String(4))           # 'BUY' | 'SELL'
    quantity: Mapped[int] = mapped_column(BigInteger)
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    value_cr: Mapped[float | None] = mapped_column(Numeric(18, 4))

    __table_args__ = (
        Index("ix_deals_stock_date", "stock_id", "trade_date"),
        Index("ix_deals_date_type", "trade_date", "deal_type"),
    )
