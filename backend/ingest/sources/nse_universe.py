"""Populate the `stocks` table with Nifty 500 constituents.

Also flags Nifty 50 members and F&O-eligible stocks so downstream jobs know
which universe to iterate.

Sources:
  - Nifty 500 constituents: NSE indices CSV
  - Nifty 50 constituents:  NSE indices CSV
  - F&O universe:           NSE F&O security list CSV

Idempotent: upserts on `symbol`.
"""
from __future__ import annotations

import io

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import Stock
from ingest.utils.http import fetch
from ingest.utils.run_log import track_run

NIFTY500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
NIFTY50_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
FNO_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"


def _read_index_csv(url: str, subdir: str) -> pd.DataFrame:
    raw = fetch(url, subdir=subdir, use_cache=False)
    return pd.read_csv(io.BytesIO(raw))


def _fno_symbols() -> set[str]:
    try:
        raw = fetch(FNO_URL, subdir="fno", use_cache=False)
        df = pd.read_csv(io.BytesIO(raw), skiprows=1)
        col = next((c for c in df.columns if "SYMBOL" in c.upper()), None)
        if col is None:
            return set()
        return {str(s).strip() for s in df[col].dropna() if str(s).strip()}
    except Exception:
        return set()


def load_universe() -> int:
    with track_run("nse_universe") as run:
        n500 = _read_index_csv(NIFTY500_URL, "nifty500")
        n50 = _read_index_csv(NIFTY50_URL, "nifty50")

        n500.columns = [c.strip() for c in n500.columns]
        n50.columns = [c.strip() for c in n50.columns]

        def col(df: pd.DataFrame, *candidates: str) -> str | None:
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        sym_col = col(n500, "Symbol", "SYMBOL")
        isin_col = col(n500, "ISIN Code", "ISIN")
        name_col = col(n500, "Company Name", "COMPANY NAME", "Name")
        ind_col = col(n500, "Industry", "INDUSTRY")
        if sym_col is None:
            raise RuntimeError(f"Nifty 500 CSV missing Symbol column; got {list(n500.columns)}")

        n50_sym_col = col(n50, "Symbol", "SYMBOL") or "Symbol"
        nifty50_symbols = set(n50[n50_sym_col].astype(str).str.strip())
        fno_symbols = _fno_symbols()

        rows = []
        for _, r in n500.iterrows():
            symbol = str(r[sym_col]).strip()
            if not symbol:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "isin": (str(r[isin_col]).strip() or None) if isin_col else None,
                    "name": (str(r[name_col]).strip() or None) if name_col else None,
                    "industry": (str(r[ind_col]).strip() or None) if ind_col else None,
                    "in_nifty50": symbol in nifty50_symbols,
                    "in_nifty500": True,
                    "is_fno": symbol in fno_symbols,
                }
            )

        if not rows:
            raise RuntimeError("Nifty 500 CSV parsed but yielded zero rows")

        session = SessionLocal()
        try:
            stmt = pg_insert(Stock).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol"],
                set_={
                    "isin": stmt.excluded.isin,
                    "name": stmt.excluded.name,
                    "industry": stmt.excluded.industry,
                    "in_nifty50": stmt.excluded.in_nifty50,
                    "in_nifty500": stmt.excluded.in_nifty500,
                    "is_fno": stmt.excluded.is_fno,
                },
            )
            session.execute(stmt)
            session.commit()
        finally:
            session.close()

        run.rows_written = len(rows)
        return len(rows)


if __name__ == "__main__":
    n = load_universe()
    print(f"upserted {n} stocks")
