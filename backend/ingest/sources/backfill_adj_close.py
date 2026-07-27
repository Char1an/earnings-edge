"""Backfill prices.adj_close from yfinance's `Adj Close`.

yfinance auto-adjusts for both splits and cash dividends. For our reaction-
computation use case only splits matter, but the dividend adjustment is
harmless — it shifts prices by tiny amounts (~0.5% for TCS, imperceptible
at the reaction-window level) and never introduces a discontinuity that
would fake a reaction.

For each stock:
  1. Fetch full history from yfinance (auto_adjust=False so we get both cols)
  2. Bulk UPDATE prices for that stock via VALUES join, matching on trade_date
  3. Skip stocks yfinance has no data for — adj_close stays NULL and downstream
     code (compute_reactions, timelines endpoint) COALESCEs to raw close.

Parallelized with ThreadPoolExecutor since yfinance is I/O-bound.

Usage:
    python -m ingest.sources.backfill_adj_close
    python -m ingest.sources.backfill_adj_close --symbols COCHINSHIP,TCS
    python -m ingest.sources.backfill_adj_close --workers 12
"""
from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import yfinance as yf
from sqlalchemy import select, text
from tqdm import tqdm

from app.db import SessionLocal
from app.models import Stock
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)


def _fetch_adj(symbol: str) -> pd.DataFrame | None:
    """Return DataFrame with columns [trade_date, adj_close], or None on failure."""
    try:
        t = yf.Ticker(f"{symbol}.NS")
        # 15 years covers our full backfill (10y prices + margin).
        hist = t.history(period="15y", auto_adjust=False, actions=False)
    except Exception as e:
        log.warning("yfinance history for %s failed: %s", symbol, e)
        return None
    if hist is None or hist.empty or "Adj Close" not in hist.columns:
        return None
    df = pd.DataFrame({
        "trade_date": hist.index.date,
        "adj_close": hist["Adj Close"].astype(float).values,
    })
    df = df.dropna(subset=["adj_close"])
    return df if not df.empty else None


def _bulk_update(session, stock_id: int, df: pd.DataFrame) -> int:
    """Bulk-UPDATE prices.adj_close for one stock. Returns row count updated."""
    if df.empty:
        return 0
    # Build a VALUES table and UPDATE-FROM in one round trip. Postgres will
    # ignore trade_dates that don't exist in prices (LEFT of an inner join).
    rows = [(d, float(a)) for d, a in zip(df["trade_date"], df["adj_close"])]
    # Use a temporary VALUES clause; ARRAY unnest is the tidiest cross-driver.
    dates = [r[0] for r in rows]
    adjs = [r[1] for r in rows]
    result = session.execute(
        text("""
            UPDATE prices p
            SET adj_close = v.adj_close
            FROM (
                SELECT unnest(CAST(:dates AS date[])) AS trade_date,
                       unnest(CAST(:adjs  AS numeric[])) AS adj_close
            ) AS v
            WHERE p.stock_id = :stock_id
              AND p.trade_date = v.trade_date
        """),
        {"stock_id": stock_id, "dates": dates, "adjs": adjs},
    )
    return result.rowcount or 0


def _process_stock(stock_id: int, symbol: str) -> tuple[int, int]:
    """Return (rows_updated, 0=ok / 1=skipped)."""
    df = _fetch_adj(symbol)
    if df is None:
        return 0, 1
    session = SessionLocal()
    try:
        n = _bulk_update(session, stock_id, df)
        session.commit()
        return n, 0
    except Exception as e:
        session.rollback()
        log.warning("bulk update for %s failed: %s", symbol, e)
        return 0, 1
    finally:
        session.close()


def backfill(symbols: list[str] | None = None, workers: int = 8) -> int:
    with track_run("backfill_adj_close") as run:
        with SessionLocal() as s:
            q = select(Stock.id, Stock.symbol).order_by(Stock.symbol.asc())
            if symbols:
                q = q.where(Stock.symbol.in_([s.upper() for s in symbols]))
            targets = list(s.execute(q).all())

        total = 0
        skipped = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {
                ex.submit(_process_stock, sid, sym): sym
                for sid, sym in targets
            }
            with tqdm(total=len(futs), desc="adj_close") as bar:
                for f in as_completed(futs):
                    n, sk = f.result()
                    total += n
                    skipped += sk
                    bar.update(1)
                    bar.set_postfix_str(f"rows={total} skip={skipped}")

        run.rows_written = total
        if skipped:
            run.status = "partial" if total else "failed"
            run.error = f"{skipped} stock(s) had no yfinance data"
        return total


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", help="comma-separated NSE symbols (default: all)")
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()
    symbols = args.symbols.split(",") if args.symbols else None
    n = backfill(symbols=symbols, workers=args.workers)
    print(f"updated {n} rows")
