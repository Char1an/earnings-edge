"""Ingest NSE bulk and block deals.

NSE publishes a rolling CSV of the last ~4 weeks:
  bulk:  https://nsearchives.nseindia.com/content/equities/bulk.csv
  block: https://nsearchives.nseindia.com/content/equities/block.csv

CSV columns (both files use the same shape):
  Date, Symbol, Security Name, Client Name, Buy/Sell, Quantity Traded,
  Trade Price / Wght. Avg. Price, Remarks
"""
from __future__ import annotations

import io
import logging

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import Deal, Stock
from ingest.utils.http import fetch
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

BULK_URL = "https://nsearchives.nseindia.com/content/equities/bulk.csv"
BLOCK_URL = "https://nsearchives.nseindia.com/content/equities/block.csv"


def _load_symbol_map() -> dict[str, int]:
    session = SessionLocal()
    try:
        rows = session.execute(select(Stock.id, Stock.symbol)).all()
        return {sym: sid for sid, sym in rows}
    finally:
        session.close()


def _parse(csv_bytes: bytes, deal_type: str) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(csv_bytes))
    df.columns = [c.strip() for c in df.columns]

    def find(*cands: str) -> str | None:
        for c in cands:
            for col in df.columns:
                if c.lower() in col.lower():
                    return col
        return None

    date_col = find("Date")
    sym_col = find("Symbol")
    client_col = find("Client Name")
    side_col = find("Buy/Sell", "Buy / Sell")
    qty_col = find("Quantity Traded", "Quantity")
    price_col = find("Price")

    if not all([date_col, sym_col, side_col, qty_col, price_col]):
        raise RuntimeError(
            f"{deal_type} CSV missing expected columns; got {list(df.columns)}"
        )

    out = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(df[date_col], dayfirst=True, errors="coerce").dt.date,
            "symbol": df[sym_col].astype(str).str.strip(),
            "client_name": df[client_col].astype(str).str.strip() if client_col else None,
            "buy_sell": df[side_col].astype(str).str.strip().str.upper().str[:4],
            "quantity": pd.to_numeric(df[qty_col].astype(str).str.replace(",", ""), errors="coerce"),
            "price": pd.to_numeric(df[price_col].astype(str).str.replace(",", ""), errors="coerce"),
        }
    ).dropna(subset=["trade_date", "symbol", "buy_sell", "quantity", "price"])

    out["buy_sell"] = out["buy_sell"].str.replace("BUY", "BUY").str.replace("SELL", "SELL")
    out["value_cr"] = (out["quantity"] * out["price"]) / 1e7
    out["deal_type"] = deal_type
    out["exchange"] = "NSE"
    return out


def _upsert(df: pd.DataFrame, symbol_map: dict[str, int]) -> int:
    df = df.copy()
    df["stock_id"] = df["symbol"].map(symbol_map)
    df = df.dropna(subset=["stock_id"])
    df["stock_id"] = df["stock_id"].astype(int)
    df["quantity"] = df["quantity"].astype("int64")

    rows = df[
        [
            "stock_id",
            "trade_date",
            "deal_type",
            "exchange",
            "client_name",
            "buy_sell",
            "quantity",
            "price",
            "value_cr",
        ]
    ].to_dict("records")
    if not rows:
        return 0

    session = SessionLocal()
    try:
        stmt = pg_insert(Deal).values(rows)
        # Unique constraint uq_deals_natural handles dedupe on retry.
        stmt = stmt.on_conflict_do_nothing(constraint="uq_deals_natural")
        session.execute(stmt)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return len(rows)


def _run_one(url: str, deal_type: str, subdir: str) -> int:
    raw = fetch(url, subdir=subdir, use_cache=False)
    df = _parse(raw, deal_type)
    if df.empty:
        return 0
    symbol_map = _load_symbol_map()
    return _upsert(df, symbol_map)


def ingest_deals() -> int:
    with track_run("nse_deals") as run:
        total = 0
        errs: list[str] = []
        for url, deal_type, sub in ((BULK_URL, "bulk", "bulk"), (BLOCK_URL, "block", "block")):
            try:
                total += _run_one(url, deal_type, sub)
            except Exception as e:
                errs.append(f"{deal_type}: {type(e).__name__}: {e}")
                log.warning("deals %s failed: %s", deal_type, e)
        run.rows_written = total
        if errs:
            run.status = "partial"
            run.error = " | ".join(errs)[:2000]
        return total


if __name__ == "__main__":
    n = ingest_deals()
    print(f"processed {n} deal rows (upserted where new)")
