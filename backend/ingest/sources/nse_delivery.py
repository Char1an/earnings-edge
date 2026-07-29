"""Delivery % ingest from NSE sec_bhavdata_full CSV.

Updates delivery_qty + delivery_pct on existing rows in the prices table
for the given date(s). Assumes price ingest has already populated the row.

URL: https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv
Columns of interest: SYMBOL, SERIES, DATE1, DELIV_QTY, DELIV_PER
"""
from __future__ import annotations

import io
import logging
from datetime import date, timedelta

import httpx
import pandas as pd
from sqlalchemy import text

from app.db import SessionLocal
from ingest.utils.http import fetch
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

URL_FMT = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"


def _url(d: date) -> str:
    return URL_FMT.format(ddmmyyyy=d.strftime("%d%m%Y"))


def _parse(csv_bytes: bytes, target: date) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(csv_bytes))
    df.columns = [c.strip() for c in df.columns]
    df = df[df["SERIES"].astype(str).str.strip() == "EQ"].copy()
    return pd.DataFrame(
        {
            "symbol": df["SYMBOL"].astype(str).str.strip(),
            "trade_date": target,
            "delivery_qty": pd.to_numeric(df["DELIV_QTY"], errors="coerce"),
            "delivery_pct": pd.to_numeric(df["DELIV_PER"], errors="coerce"),
        }
    ).dropna(subset=["delivery_qty", "delivery_pct"])


def _apply(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    payload = [
        {
            "symbol": r.symbol,
            "trade_date": r.trade_date,
            "delivery_qty": int(r.delivery_qty),
            "delivery_pct": float(r.delivery_pct),
        }
        for r in df.itertuples(index=False)
    ]

    stmt = text(
        """
        UPDATE prices p
           SET delivery_qty = :delivery_qty,
               delivery_pct = :delivery_pct
          FROM stocks s
         WHERE p.stock_id = s.id
           AND s.symbol = :symbol
           AND p.trade_date = :trade_date
        """
    )

    updated = 0
    session = SessionLocal()
    try:
        for row in payload:
            r = session.execute(stmt, row)
            updated += r.rowcount or 0
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return updated


def _apply_bulk(df: pd.DataFrame) -> int:
    """Fast single-statement delivery update for one day via unnest join."""
    if df.empty:
        return 0
    syms = df["symbol"].tolist()
    qtys = [int(x) for x in df["delivery_qty"].tolist()]
    pcts = [float(x) for x in df["delivery_pct"].tolist()]
    d = df["trade_date"].iloc[0]
    session = SessionLocal()
    try:
        res = session.execute(
            text(
                """
                UPDATE prices p
                   SET delivery_qty = v.qty, delivery_pct = v.pct
                  FROM (
                    SELECT unnest(CAST(:syms AS text[])) AS symbol,
                           unnest(CAST(:qtys AS bigint[])) AS qty,
                           unnest(CAST(:pcts AS numeric[])) AS pct
                  ) v
                  JOIN stocks s ON s.symbol = v.symbol
                 WHERE p.stock_id = s.id AND p.trade_date = :d
                """
            ),
            {"syms": syms, "qtys": qtys, "pcts": pcts, "d": d},
        )
        session.commit()
        return res.rowcount or 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def backfill_delivery(lookback_trading_days: int = 40) -> int:
    """Backfill delivery % for the most recent N trading dates that already
    exist in the prices table (delivery only makes sense where a price row is
    present). Idempotent — safe to re-run."""
    with track_run("nse_delivery_backfill") as run:
        with SessionLocal() as s:
            dates = [
                r[0]
                for r in s.execute(
                    text(
                        "SELECT DISTINCT trade_date FROM prices "
                        "ORDER BY trade_date DESC LIMIT :n"
                    ),
                    {"n": lookback_trading_days},
                ).all()
            ]
        total = 0
        errs: list[str] = []
        for d in dates:
            try:
                raw = fetch(_url(d), subdir="delivery", use_cache=True)
                total += _apply_bulk(_parse(raw, d))
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (403, 404):
                    continue  # holiday / not published for that date
                errs.append(f"{d}: {e}")
            except Exception as e:
                errs.append(f"{d}: {type(e).__name__}: {e}")
        run.rows_written = total
        if errs:
            run.status = "partial" if total else "failed"
            run.error = " | ".join(errs)[:2000]
        return total


def ingest_delivery(target: date | None = None, lookback_days: int = 5) -> int:
    """Fetch delivery data for `target` (default: today) walking back up to
    `lookback_days` calendar days on 404 to skip weekends/holidays."""
    with track_run("nse_delivery") as run:
        total = 0
        errs: list[str] = []
        d = target or date.today()
        attempts = 0
        while attempts <= lookback_days:
            url = _url(d)
            try:
                raw = fetch(url, subdir="delivery", use_cache=False)
                df = _parse(raw, d)
                total += _apply(df)
                run.rows_written = total
                return total
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (403, 404):
                    d -= timedelta(days=1)
                    attempts += 1
                    continue
                errs.append(f"{d}: {e}")
                break
            except Exception as e:
                errs.append(f"{d}: {type(e).__name__}: {e}")
                break

        run.rows_written = total
        if errs:
            run.status = "partial" if total else "failed"
            run.error = " | ".join(errs)[:2000]
        return total


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument(
        "--backfill",
        type=int,
        metavar="N",
        help="backfill delivery for the last N trading dates present in prices",
    )
    args = p.parse_args()
    if args.backfill:
        n = backfill_delivery(lookback_trading_days=args.backfill)
        print(f"backfilled {n} price rows with delivery %")
    else:
        n = ingest_delivery()
        print(f"updated {n} price rows with delivery %")
