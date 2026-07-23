from datetime import date

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OptionsSnapshot(Base):
    """One nightly row per F&O stock. Raw chain kept for future reprocessing."""

    __tablename__ = "options_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    expiry_date: Mapped[date] = mapped_column(Date)
    days_to_expiry: Mapped[int] = mapped_column(Integer)

    spot: Mapped[float | None] = mapped_column(Numeric(18, 4))
    atm_strike: Mapped[float | None] = mapped_column(Numeric(18, 4))
    atm_call_iv: Mapped[float | None] = mapped_column(Numeric(8, 3))
    atm_put_iv: Mapped[float | None] = mapped_column(Numeric(8, 3))
    atm_iv: Mapped[float | None] = mapped_column(Numeric(8, 3))  # avg of the two

    atm_call_oi: Mapped[int | None] = mapped_column(BigInteger)
    atm_put_oi: Mapped[int | None] = mapped_column(BigInteger)
    total_call_oi: Mapped[int | None] = mapped_column(BigInteger)
    total_put_oi: Mapped[int | None] = mapped_column(BigInteger)
    total_call_volume: Mapped[int | None] = mapped_column(BigInteger)
    total_put_volume: Mapped[int | None] = mapped_column(BigInteger)

    pcr_oi: Mapped[float | None] = mapped_column(Numeric(8, 3))
    pcr_volume: Mapped[float | None] = mapped_column(Numeric(8, 3))
    implied_move_pct: Mapped[float | None] = mapped_column(Numeric(8, 3))

    raw_chain: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        UniqueConstraint(
            "stock_id", "snapshot_date", "expiry_date", name="uq_options_snapshot"
        ),
    )


class IvRank(Base):
    """Rolling 252-session IV rank and percentile per stock."""

    __tablename__ = "iv_rank"

    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), primary_key=True
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    iv_current: Mapped[float | None] = mapped_column(Numeric(8, 3))
    iv_rank_252: Mapped[float | None] = mapped_column(Numeric(6, 3))
    iv_percentile_252: Mapped[float | None] = mapped_column(Numeric(6, 3))
    n_sessions: Mapped[int] = mapped_column(Integer)
