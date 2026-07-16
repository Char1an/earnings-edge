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
    n = ingest_delivery()
    print(f"updated {n} price rows with delivery %")
