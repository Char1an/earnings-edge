"""Daily FII/DII cash net flow.

NSE publishes it as JSON at /api/fiidiiTradeReact. Requires cookie warmup
against nseindia.com first. Returns the latest 2 trading days.

Schema is a list of {category, date, buyValue, sellValue, netValue}.
Keys occasionally rename — parse defensively.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import FiiDiiFlow
from ingest.utils.http import fetch
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

WARMUP = "https://www.nseindia.com/reports/fii-dii"
API = "https://www.nseindia.com/api/fiidiiTradeReact"


def _parse_date(s: str) -> datetime.date | None:
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _pick(d: dict, *keys: str):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _as_float(x) -> float | None:
    if x is None:
        return None
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def ingest_fii_dii() -> int:
    with track_run("nse_fii_dii") as run:
        raw = fetch(API, subdir="fii_dii", use_cache=False, warmup_url=WARMUP)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"FII/DII endpoint returned non-JSON: {raw[:200]!r}") from e

        if not isinstance(data, list) or not data:
            raise RuntimeError("FII/DII endpoint returned empty payload")

        # Group by date, then category → net cash
        by_date: dict = {}
        for row in data:
            if not isinstance(row, dict):
                continue
            d = _parse_date(str(_pick(row, "date", "reportDate", "tradeDate") or ""))
            if d is None:
                continue
            cat = str(_pick(row, "category", "clientType") or "").upper()
            net = _as_float(_pick(row, "netValue", "net"))
            if net is None:
                continue
            entry = by_date.setdefault(d, {"fii": None, "dii": None})
            if "FII" in cat or "FPI" in cat:
                entry["fii"] = net
            elif "DII" in cat:
                entry["dii"] = net

        rows = [
            {
                "trade_date": d,
                "fii_cash_net_cr": v["fii"],
                "dii_cash_net_cr": v["dii"],
                "source": "nse_fii_dii_api",
            }
            for d, v in by_date.items()
            if v["fii"] is not None or v["dii"] is not None
        ]
        if not rows:
            raise RuntimeError("FII/DII payload parsed but no usable rows")

        session = SessionLocal()
        try:
            stmt = pg_insert(FiiDiiFlow).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trade_date"],
                set_={
                    "fii_cash_net_cr": stmt.excluded.fii_cash_net_cr,
                    "dii_cash_net_cr": stmt.excluded.dii_cash_net_cr,
                    "source": stmt.excluded.source,
                },
            )
            session.execute(stmt)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        run.rows_written = len(rows)
        return len(rows)


if __name__ == "__main__":
    n = ingest_fii_dii()
    print(f"wrote {n} FII/DII rows")
