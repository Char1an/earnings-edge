"""Backfill and daily update of OHLCV prices for the Nifty 500 universe.

Primary source: jugaad-data (NSE historical, adjusted for splits/bonuses).
Fallback: yfinance (append .NS suffix).

Idempotent: uses ON CONFLICT DO UPDATE keyed on (stock_id, trade_date).
"""
from __future__ import annotations

import logging
import signal
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from tqdm import tqdm

from app.db import SessionLocal
from app.models import Price, Stock
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

BATCH_SIZE = 5000
PER_STOCK_TIMEOUT_S = 60
SKIP_POPULATED_THRESHOLD = 500  # if a stock has ≥N rows already, treat as done


def _fetch_jugaad(symbol: str, start: date, end: date) -> pd.DataFrame | None:
    try:
        from jugaad_data.nse import stock_df

        df = stock_df(symbol=symbol, from_date=start, to_date=end, series="EQ")
        if df is None or df.empty:
            return None
        df = df.rename(
            columns={
                "DATE": "trade_date",
                "OPEN": "open",
                "HIGH": "high",
                "LOW": "low",
                "CLOSE": "close",
                "VOLUME": "volume",
                "NO OF TRADES": "trades",
            }
        )
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        return df[["trade_date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        log.warning("jugaad failed for %s: %s", symbol, e)
        return None


def _fetch_yfinance(symbol: str, start: date, end: date) -> pd.DataFrame | None:
    try:
        import yfinance as yf

        t = yf.Ticker(f"{symbol}.NS")
        df = t.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=False)
        if df is None or df.empty:
            return None
        df = df.reset_index().rename(
            columns={
                "Date": "trade_date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        return df[["trade_date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        log.warning("yfinance failed for %s: %s", symbol, e)
        return None


def _fetch_with_fallback(symbol: str, start: date, end: date) -> pd.DataFrame | None:
    """jugaad first, fall back to yfinance. Never raises."""
    df = _fetch_jugaad(symbol, start, end)
    if df is None or df.empty:
        df = _fetch_yfinance(symbol, start, end)
    return df


class _FetchTimeout(Exception):
    pass


def _fetch_with_timeout(
    symbol: str, start: date, end: date, timeout_s: int = PER_STOCK_TIMEOUT_S
) -> pd.DataFrame | None:
    """SIGALRM-based timeout that actually interrupts blocked socket reads.
    Unix-only, main-thread-only — fine for our single-threaded ingest CLI."""

    def _handler(signum, frame):
        raise _FetchTimeout()

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(int(timeout_s))
    try:
        return _fetch_with_fallback(symbol, start, end)
    except _FetchTimeout:
        log.warning("fetch timed out after %ss for %s", timeout_s, symbol)
        return None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _upsert_prices(stock_id: int, df: pd.DataFrame | None) -> int:
    if df is None or df.empty:
        return 0
    df = df.dropna(subset=["trade_date", "open", "high", "low", "close"])
    # jugaad-data occasionally returns overlapping chunks across long windows;
    # collapse any duplicate trade_dates so the ON CONFLICT UPSERT stays legal.
    df = df.drop_duplicates(subset=["trade_date"], keep="last")
    if df.empty:
        return 0

    rows = [
        {
            "stock_id": stock_id,
            "trade_date": r.trade_date,
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": int(r.volume) if pd.notna(r.volume) else None,
        }
        for r in df.itertuples(index=False)
    ]
    if not rows:
        return 0

    total = 0
    session = SessionLocal()
    try:
        for i in range(0, len(rows), BATCH_SIZE):
            chunk = rows[i : i + BATCH_SIZE]
            stmt = pg_insert(Price).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_id", "trade_date"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            session.execute(stmt)
            total += len(chunk)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return total


def _already_populated_ids(session) -> set[int]:
    """Return stock_ids whose prices row count already exceeds SKIP_POPULATED_THRESHOLD.
    Used to resume a partial backfill without redoing everything."""
    rows = session.execute(
        select(Price.stock_id, func.count(Price.trade_date))
        .group_by(Price.stock_id)
    ).all()
    return {sid for sid, n in rows if n >= SKIP_POPULATED_THRESHOLD}


def _run(
    job_name: str,
    years: int,
    only_symbols: list[str] | None,
    skip_populated: bool = False,
) -> int:
    end = date.today()
    start = end - timedelta(days=365 * years + 5) if years > 0 else end - timedelta(days=7)

    with track_run(job_name) as run:
        session = SessionLocal()
        try:
            q = select(Stock.id, Stock.symbol).where(Stock.in_nifty500.is_(True))
            if only_symbols:
                q = q.where(Stock.symbol.in_(only_symbols))
            stocks = session.execute(q).all()
            done_ids = _already_populated_ids(session) if skip_populated else set()
        finally:
            session.close()

        if skip_populated and done_ids:
            before = len(stocks)
            stocks = [s for s in stocks if s[0] not in done_ids]
            log.info("skipping %d already-populated stocks", before - len(stocks))

        total = 0
        failed = 0
        for stock_id, symbol in tqdm(stocks, desc=job_name):
            try:
                df = _fetch_with_timeout(symbol, start, end)
                total += _upsert_prices(stock_id, df)
            except Exception as e:
                failed += 1
                log.warning("upsert failed for %s: %s", symbol, e)

        run.rows_written = total
        if failed:
            run.status = "partial"
            run.error = f"{failed} symbol(s) failed"
        return total


def backfill(
    years: int = 10,
    only_symbols: list[str] | None = None,
    skip_populated: bool = False,
) -> int:
    return _run(
        "nse_prices_backfill",
        years=years,
        only_symbols=only_symbols,
        skip_populated=skip_populated,
    )


def daily_update() -> int:
    """Small window update used by nightly cron. Fetches last 7 days."""
    return _run("nse_prices_daily", years=0, only_symbols=None)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(levelname)s: %(message)s")

    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["backfill", "daily"], default="backfill")
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--symbols", nargs="*", help="restrict to these symbols (debug)")
    p.add_argument(
        "--skip-populated",
        action="store_true",
        help=f"skip stocks that already have ≥{SKIP_POPULATED_THRESHOLD} price rows",
    )
    args = p.parse_args()

    if args.mode == "backfill":
        n = backfill(
            years=args.years,
            only_symbols=args.symbols,
            skip_populated=args.skip_populated,
        )
    else:
        n = daily_update()
    print(f"wrote {n} price rows")
