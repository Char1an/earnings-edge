"""Nightly NSE option chain snapshots for F&O stocks.

Endpoint: https://www.nseindia.com/api/option-chain-equities?symbol=X
Needs cookie warmup on nseindia.com.

For each F&O stock we snapshot the *nearest expiry only*: ATM IV, ATM OI,
total call/put OI, PCR (OI + volume), and the implied move (ATM straddle / spot).
Raw chain is stashed as JSON for future reprocessing.

Idempotent: unique (stock_id, snapshot_date, expiry_date).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import OptionsSnapshot, Stock
from ingest.utils.http import fetch
from ingest.utils.run_log import track_run

log = logging.getLogger(__name__)

WARMUP = "https://www.nseindia.com/option-chain"
API_FMT = "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
PER_STOCK_DELAY_S = 0.5


def _fetch_chain(symbol: str) -> dict | None:
    url = API_FMT.format(symbol=symbol)
    try:
        raw = fetch(url, subdir="options", use_cache=False, warmup_url=WARMUP)
    except Exception as e:
        log.debug("option-chain fetch failed for %s: %s", symbol, e)
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.debug("option-chain non-JSON for %s: %s", symbol, raw[:120])
        return None


def _parse_expiry(s: str) -> date | None:
    for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _extract(chain: dict) -> dict | None:
    """Return a parsed snapshot for the *nearest* expiry, or None if unusable."""
    records = chain.get("records") or {}
    data = records.get("data") or []
    if not data:
        return None

    spot = records.get("underlyingValue")
    if not spot:
        return None
    spot = float(spot)

    # Find soonest FUTURE expiry from the payload. If the endpoint only serves
    # already-expired chains (weekends, stale data, delisted F&O), skip cleanly
    # rather than record a snapshot with a negative days_to_expiry.
    expiries: set[date] = set()
    for row in data:
        d = _parse_expiry(str(row.get("expiryDate", "")))
        if d:
            expiries.add(d)
    future = [e for e in expiries if e >= date.today()]
    if not future:
        return None
    nearest = min(future)

    # Filter to nearest-expiry rows.
    near_rows = [
        r for r in data if _parse_expiry(str(r.get("expiryDate", ""))) == nearest
    ]
    if not near_rows:
        return None

    # ATM strike = the strike closest to spot.
    strikes = [float(r["strikePrice"]) for r in near_rows if "strikePrice" in r]
    if not strikes:
        return None
    atm_strike = min(strikes, key=lambda s: abs(s - spot))

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def bi(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    call_oi_total = put_oi_total = 0
    call_vol_total = put_vol_total = 0
    atm_call = atm_put = None

    for r in near_rows:
        strike = num(r.get("strikePrice"))
        ce = r.get("CE") or {}
        pe = r.get("PE") or {}
        call_oi_total += bi(ce.get("openInterest")) or 0
        put_oi_total += bi(pe.get("openInterest")) or 0
        call_vol_total += bi(ce.get("totalTradedVolume")) or 0
        put_vol_total += bi(pe.get("totalTradedVolume")) or 0
        if strike == atm_strike:
            atm_call = ce
            atm_put = pe

    atm_call_iv = num((atm_call or {}).get("impliedVolatility"))
    atm_put_iv = num((atm_put or {}).get("impliedVolatility"))
    atm_iv = (
        round((atm_call_iv + atm_put_iv) / 2, 3)
        if atm_call_iv is not None and atm_put_iv is not None
        else atm_call_iv or atm_put_iv
    )

    atm_call_price = num((atm_call or {}).get("lastPrice")) or 0.0
    atm_put_price = num((atm_put or {}).get("lastPrice")) or 0.0
    implied_move_pct = (
        round((atm_call_price + atm_put_price) / spot * 100.0, 3)
        if spot > 0 and (atm_call_price + atm_put_price) > 0
        else None
    )

    pcr_oi = (
        round(put_oi_total / call_oi_total, 3) if call_oi_total > 0 else None
    )
    pcr_volume = (
        round(put_vol_total / call_vol_total, 3) if call_vol_total > 0 else None
    )

    return {
        "expiry_date": nearest,
        "days_to_expiry": (nearest - date.today()).days,
        "spot": round(spot, 4),
        "atm_strike": atm_strike,
        "atm_call_iv": atm_call_iv,
        "atm_put_iv": atm_put_iv,
        "atm_iv": atm_iv,
        "atm_call_oi": bi((atm_call or {}).get("openInterest")),
        "atm_put_oi": bi((atm_put or {}).get("openInterest")),
        "total_call_oi": call_oi_total or None,
        "total_put_oi": put_oi_total or None,
        "total_call_volume": call_vol_total or None,
        "total_put_volume": put_vol_total or None,
        "pcr_oi": pcr_oi,
        "pcr_volume": pcr_volume,
        "implied_move_pct": implied_move_pct,
    }


def _upsert(stock_id: int, snapshot_date: date, parsed: dict, raw: dict) -> None:
    row = {
        "stock_id": stock_id,
        "snapshot_date": snapshot_date,
        **parsed,
        "raw_chain": raw,
    }
    session = SessionLocal()
    try:
        stmt = pg_insert(OptionsSnapshot).values(row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_options_snapshot",
            set_={
                k: stmt.excluded[k]
                for k in row
                if k not in ("stock_id", "snapshot_date", "expiry_date")
            },
        )
        session.execute(stmt)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def snapshot_options(only_symbols: list[str] | None = None) -> int:
    with track_run("nse_options") as run:
        session = SessionLocal()
        try:
            q = select(Stock.id, Stock.symbol).where(Stock.is_fno.is_(True))
            if only_symbols:
                q = q.where(Stock.symbol.in_(only_symbols))
            stocks = session.execute(q).all()
        finally:
            session.close()

        today = date.today()
        total = 0
        failed = 0
        for stock_id, symbol in stocks:
            chain = _fetch_chain(symbol)
            if chain is None:
                failed += 1
                time.sleep(PER_STOCK_DELAY_S)
                continue
            parsed = _extract(chain)
            if parsed is None:
                failed += 1
                time.sleep(PER_STOCK_DELAY_S)
                continue
            try:
                _upsert(stock_id, today, parsed, chain)
                total += 1
            except Exception as e:
                failed += 1
                log.warning("options upsert failed for %s: %s", symbol, e)
            time.sleep(PER_STOCK_DELAY_S)

        run.rows_written = total
        if failed:
            run.status = "partial"
            run.error = f"{failed} symbol(s) failed"
        return total


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(levelname)s: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="*", help="restrict to these symbols (debug)")
    args = p.parse_args()
    n = snapshot_options(only_symbols=args.symbols)
    print(f"snapshotted {n} F&O stocks")
