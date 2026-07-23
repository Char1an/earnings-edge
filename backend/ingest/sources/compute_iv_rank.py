"""Compute rolling IV rank + percentile per stock from options_snapshots.

For each F&O stock we look at up to the last 252 daily snapshot rows
(one year of trading sessions). Rank formula:

    iv_rank_252 = (iv_current - iv_min) / (iv_max - iv_min) * 100
    iv_percentile_252 = share of prior sessions with iv <= iv_current * 100

Both are only computed once we have at least MIN_SESSIONS observations —
below that, the rank is unreliable and we skip the stock.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import IvRank, OptionsSnapshot, Stock
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

WINDOW_SESSIONS = 252
MIN_SESSIONS = 20  # need at least this many prior observations to bother


def _rank_and_percentile(current: float, history: list[float]) -> tuple[float, float]:
    if not history:
        return 0.0, 0.0
    lo, hi = min(history), max(history)
    rank = 0.0 if hi == lo else round((current - lo) / (hi - lo) * 100.0, 3)
    at_or_below = sum(1 for v in history if v <= current)
    percentile = round(at_or_below / len(history) * 100.0, 3)
    return max(0.0, min(100.0, rank)), percentile


def compute_iv_rank() -> int:
    with track_run("compute_iv_rank") as run:
        session = SessionLocal()
        try:
            stocks = session.execute(
                select(Stock.id, Stock.symbol).where(Stock.is_fno.is_(True))
            ).all()
        finally:
            session.close()

        total = 0
        session = SessionLocal()
        try:
            for stock_id, _sym in stocks:
                rows = session.execute(
                    select(OptionsSnapshot.snapshot_date, OptionsSnapshot.atm_iv)
                    .where(OptionsSnapshot.stock_id == stock_id)
                    .where(OptionsSnapshot.atm_iv.is_not(None))
                    .order_by(desc(OptionsSnapshot.snapshot_date))
                    .limit(WINDOW_SESSIONS)
                ).all()
                if len(rows) < MIN_SESSIONS:
                    continue
                current_date: date = rows[0][0]
                current_iv = float(rows[0][1])
                history = [float(r[1]) for r in rows[1:]]  # exclude the current point
                rank, percentile = _rank_and_percentile(current_iv, history)

                stmt = pg_insert(IvRank).values(
                    stock_id=stock_id,
                    as_of_date=current_date,
                    iv_current=round(current_iv, 3),
                    iv_rank_252=rank,
                    iv_percentile_252=percentile,
                    n_sessions=len(rows),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["stock_id", "as_of_date"],
                    set_={
                        "iv_current": stmt.excluded.iv_current,
                        "iv_rank_252": stmt.excluded.iv_rank_252,
                        "iv_percentile_252": stmt.excluded.iv_percentile_252,
                        "n_sessions": stmt.excluded.n_sessions,
                    },
                )
                session.execute(stmt)
                total += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        run.rows_written = total
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(levelname)s: %(message)s")
    n = compute_iv_rank()
    print(f"wrote {n} iv_rank rows")
