"""Scrape quarterly earnings from screener.in.

Page: https://www.screener.in/company/{SYMBOL}/consolidated/ (fallback to /company/{SYMBOL}/)

Parses the #quarters section: quarter labels ("Jun 2024") in the header and
row-labeled numeric cells (Sales, Net Profit, EPS in Rs, OPM %). Converts to
Indian fiscal-year labels and quarter-end dates, computes YoY + QoQ growth,
and upserts one row per (stock_id, fiscal_period).
"""
from __future__ import annotations

import logging
import re
import time
from calendar import monthrange
from datetime import date

from bs4 import BeautifulSoup, Tag
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import EarningsEvent, Stock
from ingest.utils.http import fetch
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

BASE = "https://www.screener.in/company/{symbol}/{scope}/"
MONTHS = {"Mar": 3, "Jun": 6, "Sep": 9, "Dec": 12}
PER_STOCK_DELAY_S = 0.4  # be nice to Screener

# Map of normalized screener row label → key in our record. Comparison is
# done on `label.replace(" ", "")` so we tolerate "OPM %" vs "OPM%" etc.
ROW_KEYS = {
    "sales": "revenue_cr",
    "revenue": "revenue_cr",
    "netprofit": "pat_cr",
    "epsinrs": "eps",
    "opm": "opm_pct",
}


def _fetch_html(symbol: str) -> str | None:
    for scope in ("consolidated", ""):
        url = BASE.format(symbol=symbol, scope=scope).rstrip("/") + "/"
        try:
            # use_cache=False: this scraper is called weekly and MUST see fresh
            # HTML to pick up newly released quarters.
            return fetch(url, subdir=f"screener/{scope or 'standalone'}", use_cache=False).decode(
                "utf-8", errors="replace"
            )
        except Exception as e:
            log.debug("screener %s [%s] failed: %s", symbol, scope or "standalone", e)
    return None


def _parse_num(text: str) -> float | None:
    if text is None:
        return None
    s = text.strip().replace(",", "").replace("–", "-").replace("−", "-")
    s = s.replace("%", "").strip()
    if s in ("", "-"):
        return None
    # Accounting negative: (123.45) → -123.45
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1].strip()
    m = re.match(r"^-?\d+(\.\d+)?$", s)
    if not m:
        return None
    return float(s)


def _quarter_end(label: str) -> tuple[date, str] | None:
    """('Jun 2024', ) -> (date(2024,6,30), 'Q1FY25')."""
    m = re.match(r"([A-Za-z]{3})\s+(\d{4})", label.strip())
    if not m:
        return None
    mon_name, year_s = m.group(1).title(), m.group(2)
    month = MONTHS.get(mon_name)
    if month is None:
        return None
    year = int(year_s)
    last_day = monthrange(year, month)[1]
    qend = date(year, month, last_day)

    # Indian FY: Apr→Mar. Mar = Q4 of FY that ends this March.
    if month == 3:
        fy_year = year  # FY24 ends Mar 2024
        q = 4
    elif month == 6:
        fy_year = year + 1
        q = 1
    elif month == 9:
        fy_year = year + 1
        q = 2
    else:  # Dec
        fy_year = year + 1
        q = 3
    fiscal_period = f"Q{q}FY{fy_year % 100:02d}"
    return qend, fiscal_period


def _extract_quarters(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    section = soup.find("section", id="quarters")
    if section is None:
        return []
    table = section.find("table")
    if not isinstance(table, Tag):
        return []

    thead = table.find("thead")
    header_cells = thead.find_all("th") if thead else []
    quarter_labels = [th.get_text(strip=True) for th in header_cells[1:]]  # first cell is blank
    if not quarter_labels:
        return []

    # Some Screener tables omit an explicit <tbody>; fall back to direct <tr>.
    body = table.find("tbody") or table
    per_row: dict[str, list[str]] = {}
    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        raw_label = cells[0].get_text(" ", strip=True).lower().rstrip(":+")
        raw_label = re.sub(r"\s+", " ", raw_label).strip()
        norm = raw_label.replace(" ", "").rstrip("+:%")
        for row_key, out_key in ROW_KEYS.items():
            if norm.startswith(row_key):
                per_row[out_key] = [c.get_text(strip=True) for c in cells[1:]]
                break

    out: list[dict] = []
    for i, qlabel in enumerate(quarter_labels):
        parsed = _quarter_end(qlabel)
        if parsed is None:
            continue
        qend, fiscal_period = parsed
        rec = {"fiscal_period": fiscal_period, "quarter_end": qend}
        for key, values in per_row.items():
            rec[key] = _parse_num(values[i]) if i < len(values) else None
        out.append(rec)
    return out


def _with_growth(recs: list[dict]) -> list[dict]:
    """Add YoY (index-4) and QoQ (index-1) growth deltas for revenue + PAT.

    Screener columns are chronological left→right; index 0 is oldest.
    """

    def pct(cur, prev):
        if cur is None or prev is None or prev == 0:
            return None
        return round((cur - prev) / abs(prev) * 100.0, 3)

    for i, r in enumerate(recs):
        prev = recs[i - 1] if i - 1 >= 0 else None
        yoy = recs[i - 4] if i - 4 >= 0 else None
        r["qoq_revenue_growth"] = pct(r.get("revenue_cr"), prev.get("revenue_cr") if prev else None)
        r["qoq_pat_growth"] = pct(r.get("pat_cr"), prev.get("pat_cr") if prev else None)
        r["yoy_revenue_growth"] = pct(r.get("revenue_cr"), yoy.get("revenue_cr") if yoy else None)
        r["yoy_pat_growth"] = pct(r.get("pat_cr"), yoy.get("pat_cr") if yoy else None)
    return recs


def _upsert(stock_id: int, recs: list[dict]) -> int:
    if not recs:
        return 0
    rows = []
    for r in recs:
        rows.append(
            {
                "stock_id": stock_id,
                "fiscal_period": r["fiscal_period"],
                "quarter_end": r["quarter_end"],
                "revenue_cr": r.get("revenue_cr"),
                "pat_cr": r.get("pat_cr"),
                "eps": r.get("eps"),
                "opm_pct": r.get("opm_pct"),
                "yoy_revenue_growth": r.get("yoy_revenue_growth"),
                "yoy_pat_growth": r.get("yoy_pat_growth"),
                "qoq_revenue_growth": r.get("qoq_revenue_growth"),
                "qoq_pat_growth": r.get("qoq_pat_growth"),
                "source": "screener",
            }
        )

    session = SessionLocal()
    try:
        stmt = pg_insert(EarningsEvent).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_earnings_stock_period",
            set_={
                "quarter_end": stmt.excluded.quarter_end,
                "revenue_cr": stmt.excluded.revenue_cr,
                "pat_cr": stmt.excluded.pat_cr,
                "eps": stmt.excluded.eps,
                "opm_pct": stmt.excluded.opm_pct,
                "yoy_revenue_growth": stmt.excluded.yoy_revenue_growth,
                "yoy_pat_growth": stmt.excluded.yoy_pat_growth,
                "qoq_revenue_growth": stmt.excluded.qoq_revenue_growth,
                "qoq_pat_growth": stmt.excluded.qoq_pat_growth,
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
    return len(rows)


def _scrape_one(stock_id: int, symbol: str) -> int:
    html = _fetch_html(symbol)
    if html is None:
        return 0
    recs = _with_growth(_extract_quarters(html))
    return _upsert(stock_id, recs)


def ingest_earnings(only_symbols: list[str] | None = None, limit: int | None = None) -> int:
    """Scrape earnings for all Nifty 500 stocks (or a subset)."""
    with track_run("screener_earnings") as run:
        session = SessionLocal()
        try:
            q = select(Stock.id, Stock.symbol).where(Stock.in_nifty500.is_(True))
            if only_symbols:
                q = q.where(Stock.symbol.in_(only_symbols))
            stocks = session.execute(q).all()
        finally:
            session.close()

        if limit:
            stocks = stocks[:limit]

        total = 0
        failed = 0
        for stock_id, symbol in stocks:
            try:
                total += _scrape_one(stock_id, symbol)
            except Exception as e:
                failed += 1
                log.warning("screener %s failed: %s", symbol, e)
            time.sleep(PER_STOCK_DELAY_S)

        run.rows_written = total
        if failed:
            run.status = "partial"
            run.error = f"{failed} symbol(s) failed"
        return total


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="*", help="restrict to these symbols (debug)")
    p.add_argument("--limit", type=int, help="cap total stocks scraped (debug)")
    args = p.parse_args()

    n = ingest_earnings(only_symbols=args.symbols, limit=args.limit)
    print(f"wrote {n} earnings-event rows")
