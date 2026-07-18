from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EarningsEvent(Base):
    """One row per quarterly result. fiscal_period like 'Q1FY26' or 'Jun 2024'."""

    __tablename__ = "earnings_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), index=True
    )
    fiscal_period: Mapped[str] = mapped_column(String(16))
    quarter_end: Mapped[date] = mapped_column(Date)
    announcement_date: Mapped[date | None] = mapped_column(Date, index=True)

    revenue_cr: Mapped[float | None] = mapped_column(Numeric(18, 2))
    pat_cr: Mapped[float | None] = mapped_column(Numeric(18, 2))
    eps: Mapped[float | None] = mapped_column(Numeric(12, 4))
    opm_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))

    yoy_revenue_growth: Mapped[float | None] = mapped_column(Numeric(10, 3))
    yoy_pat_growth: Mapped[float | None] = mapped_column(Numeric(10, 3))
    qoq_revenue_growth: Mapped[float | None] = mapped_column(Numeric(10, 3))
    qoq_pat_growth: Mapped[float | None] = mapped_column(Numeric(10, 3))

    source: Mapped[str] = mapped_column(String(32), default="screener")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("stock_id", "fiscal_period", name="uq_earnings_stock_period"),
        Index("ix_earnings_stock_qend", "stock_id", "quarter_end"),
    )


class EarningsReaction(Base):
    """Derived price behavior around each earnings event."""

    __tablename__ = "earnings_reactions"

    earnings_event_id: Mapped[int] = mapped_column(
        ForeignKey("earnings_events.id", ondelete="CASCADE"), primary_key=True
    )
    pre_close: Mapped[float | None] = mapped_column(Numeric(18, 4))
    gap_open_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))
    day1_close_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))
    day3_close_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))
    day5_close_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))
    day1_high_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))
    day1_low_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))
    volume_spike: Mapped[float | None] = mapped_column(Numeric(8, 3))
    detection_method: Mapped[str] = mapped_column(String(16), default="heuristic")
    detection_confidence: Mapped[float | None] = mapped_column(Numeric(5, 3))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UpcomingEarnings(Base):
    """Calendar of expected upcoming results (best-effort)."""

    __tablename__ = "upcoming_earnings"

    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), primary_key=True
    )
    expected_date: Mapped[date] = mapped_column(Date, primary_key=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    source: Mapped[str] = mapped_column(String(32))
    raw: Mapped[dict | None] = mapped_column(JSON)
