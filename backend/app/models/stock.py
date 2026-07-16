from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    isin: Mapped[str | None] = mapped_column(String(16), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(128))
    industry: Mapped[str | None] = mapped_column(String(128))
    market_cap_cr: Mapped[float | None] = mapped_column(Numeric(18, 2))

    in_nifty50: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    in_nifty500: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_fno: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    listed_date: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
