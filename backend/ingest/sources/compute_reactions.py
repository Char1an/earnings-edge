"""Compute earnings_reactions for each earnings_event.

Announcement date is inferred from price/volume signature in the window
[quarter_end + 10, quarter_end + 75] trading days: the candidate day with
the largest |return| × volume-ratio is selected. Confidence is the ratio
of that peak score to the window's mean score.

Once the announcement (reaction) day is fixed, we compute:
    pre_close        close of the trading day BEFORE the reaction day
    gap_open_pct     (open on reaction day    / pre_close - 1) * 100
    day1_close_pct   (close on reaction day   / pre_close - 1) * 100
    day3_close_pct   (close 2 days later      / pre_close - 1) * 100
    day5_close_pct   (close 4 days later      / pre_close - 1) * 100
    day1_high_pct    (high on reaction day    / pre_close - 1) * 100
    day1_low_pct     (low  on reaction day    / pre_close - 1) * 100
    volume_spike     volume on reaction day / 20-session avg volume

Idempotent: upserts on earnings_event_id.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import EarningsEvent, EarningsReaction, Price
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

WINDOW_START_DAYS = 10   # calendar days after quarter_end
WINDOW_END_DAYS = 75
VOL_LOOKBACK = 20        # sessions used for the volume-spike baseline
MIN_WINDOW_ROWS = 8      # skip events without enough surrounding data


def _load_prices(session, stock_id: int, start: date, end: date) -> pd.DataFrame:
    q = (
        select(
            Price.trade_date, Price.open, Price.high, Price.low, Price.close, Price.volume
        )
        .where(Price.stock_id == stock_id)
        .where(Price.trade_date >= start)
        .where(Price.trade_date <= end)
        .order_by(Price.trade_date.asc())
    )
    rows = session.execute(q).all()
    if not rows:
        return pd.DataFrame(
            columns=["trade_date", "open", "high", "low", "close", "volume"]
        )
    df = pd.DataFrame(rows, columns=["trade_date", "open", "high", "low", "close", "volume"])
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    df["volume"] = df["volume"].fillna(0).astype("int64")
    return df


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Return a reset copy of df with return + volume-baseline columns added."""
    df = df.reset_index(drop=True).copy()
    df["prev_close"] = df["close"].shift(1)
    df["ret_abs"] = (df["close"] / df["prev_close"] - 1.0).abs()
    df["vol_avg20"] = df["volume"].rolling(VOL_LOOKBACK, min_periods=5).mean()
    df["vol_ratio"] = df["volume"] / df["vol_avg20"]
    df["score"] = df["ret_abs"] * df["vol_ratio"]
    return df


def _detect(df_enriched: pd.DataFrame, quarter_end: date) -> tuple[int, float] | None:
    """Return (row_index_of_reaction_day, confidence) or None. df must be enriched."""
    win_lo = quarter_end + timedelta(days=WINDOW_START_DAYS)
    win_hi = quarter_end + timedelta(days=WINDOW_END_DAYS)

    mask = (df_enriched["trade_date"] >= win_lo) & (df_enriched["trade_date"] <= win_hi)
    cand = df_enriched[mask & df_enriched["score"].notna()]
    if len(cand) < MIN_WINDOW_ROWS:
        return None

    idx = cand["score"].idxmax()
    peak = float(cand.loc[idx, "score"])
    mean = float(cand["score"].mean())
    if peak <= 0 or mean <= 0:
        return None
    confidence = min(peak / mean, 99.999)  # clip for Numeric(5,3)
    return int(idx), round(confidence, 3)


def _reaction_row(df: pd.DataFrame, idx: int, event_id: int) -> dict | None:
    if idx - 1 < 0 or idx >= len(df):
        return None
    pre_close = float(df.loc[idx - 1, "close"])
    if pre_close <= 0:
        return None

    def pct(x: float | None) -> float | None:
        return None if x is None else round((x / pre_close - 1.0) * 100.0, 3)

    open_r = float(df.loc[idx, "open"])
    close_r = float(df.loc[idx, "close"])
    high_r = float(df.loc[idx, "high"])
    low_r = float(df.loc[idx, "low"])

    close_d3 = float(df.loc[idx + 2, "close"]) if idx + 2 < len(df) else None
    close_d5 = float(df.loc[idx + 4, "close"]) if idx + 4 < len(df) else None

    vol_avg20 = df.loc[idx, "vol_avg20"]
    vol_spike = None
    if pd.notna(vol_avg20) and vol_avg20 > 0:
        vol_spike = round(float(df.loc[idx, "volume"]) / float(vol_avg20), 3)

    return {
        "earnings_event_id": event_id,
        "pre_close": round(pre_close, 4),
        "gap_open_pct": pct(open_r),
        "day1_close_pct": pct(close_r),
        "day3_close_pct": pct(close_d3),
        "day5_close_pct": pct(close_d5),
        "day1_high_pct": pct(high_r),
        "day1_low_pct": pct(low_r),
        "volume_spike": vol_spike,
        "detection_method": "heuristic",
    }


def _upsert_reaction(session, row: dict, confidence: float, announcement_date: date, event_id: int):
    row = {**row, "detection_confidence": confidence}
    stmt = pg_insert(EarningsReaction).values(row)
    stmt = stmt.on_conflict_do_update(
        index_elements=["earnings_event_id"],
        set_={
            k: stmt.excluded[k]
            for k in row
            if k != "earnings_event_id"
        },
    )
    session.execute(stmt)
    session.execute(
        EarningsEvent.__table__.update()
        .where(EarningsEvent.id == event_id)
        .values(announcement_date=announcement_date)
    )


def compute_reactions(force: bool = False, only_stock_ids: list[int] | None = None) -> int:
    """Compute (or recompute) reactions.

    force=False: only process events that don't yet have a reaction row.
    Prices are loaded once per stock (full history) so per-event windows
    are always covered. Commits are per-stock so a mid-run failure keeps
    partial progress.
    """
    with track_run("compute_reactions") as run:
        session = SessionLocal()
        try:
            q = select(
                EarningsEvent.id,
                EarningsEvent.stock_id,
                EarningsEvent.quarter_end,
            ).order_by(EarningsEvent.stock_id.asc(), EarningsEvent.quarter_end.asc())
            if only_stock_ids:
                q = q.where(EarningsEvent.stock_id.in_(only_stock_ids))
            events = list(session.execute(q).all())
            if not force:
                existing = {
                    r[0]
                    for r in session.execute(select(EarningsReaction.earnings_event_id)).all()
                }
                events = [e for e in events if e[0] not in existing]
        finally:
            session.close()

        # Group by stock so we load prices once per stock and commit per stock.
        by_stock: dict[int, list[tuple[int, int, date]]] = {}
        for e in events:
            by_stock.setdefault(e[1], []).append(e)

        total = 0
        skipped = 0
        for stock_id, stock_events in by_stock.items():
            session = SessionLocal()
            try:
                # Cover the full range this stock's events touch, with margins
                # for the VOL_LOOKBACK baseline and post-event day5.
                qmin = min(e[2] for e in stock_events)
                qmax = max(e[2] for e in stock_events)
                df = _load_prices(
                    session,
                    stock_id,
                    start=qmin - timedelta(days=180),
                    end=qmax + timedelta(days=WINDOW_END_DAYS + 15),
                )
                if df.empty:
                    skipped += len(stock_events)
                    continue

                # Enrich once per stock; index labels are stable across per-event lookups.
                df_e = _enrich(df)
                for event_id, _sid, quarter_end in stock_events:
                    detected = _detect(df_e, quarter_end)
                    if detected is None:
                        skipped += 1
                        continue
                    idx, confidence = detected
                    announcement_date = df_e.loc[idx, "trade_date"]
                    row = _reaction_row(df_e, idx, event_id)
                    if row is None:
                        skipped += 1
                        continue
                    _upsert_reaction(session, row, confidence, announcement_date, event_id)
                    total += 1
                session.commit()
            except Exception as e:
                session.rollback()
                log.warning("reactions for stock_id=%s failed: %s", stock_id, e)
                skipped += len(stock_events)
            finally:
                session.close()

        run.rows_written = total
        if skipped:
            run.status = "partial" if total else "failed"
            run.error = f"{skipped} event(s) skipped (insufficient data / weak signal / stock error)"
        return total


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="recompute all events")
    args = p.parse_args()
    n = compute_reactions(force=args.force)
    print(f"computed {n} reactions")
