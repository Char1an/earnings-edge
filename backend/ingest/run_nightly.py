"""Nightly orchestrator. Runs all daily ingest jobs fail-soft.

Daily order:
  1. universe          idempotent, cheap; keeps stocks + F&O flags fresh
  2. prices_daily      OHLCV last 7d
  3. deals             bulk + block rolling CSVs
  4. fii_dii           cash net for last 1-2 days
  5. delivery          updates prices rows with delivery %
  6. options           nightly option-chain snapshot for F&O stocks (builds
                       IV rank history over time)
  7. compute_iv_rank   rolling 252-session IV rank + percentile
  8. compute_reactions inferred announcement date + reaction metrics for any
                       earnings_event still missing a reaction row

Weekly (Fridays, UTC — same run as the last weekday cron):
  9. screener_earnings scrape quarterly financials for Nifty 500

Each job wraps its own IngestRun. This wrapper only sequences them and
prints a summary; one failed job never blocks the next.
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def _run(name: str, fn: Callable[[], int]) -> tuple[str, str, int | str]:
    try:
        n = fn()
        return (name, "ok", n)
    except Exception as e:
        log.error("%s failed: %s", name, e)
        traceback.print_exc()
        return (name, "failed", f"{type(e).__name__}: {e}")


def _should_run_weekly() -> bool:
    if os.environ.get("FORCE_WEEKLY") == "1":
        return True
    # Friday. The nightly cron runs Mon-Fri; Screener is scraped once per week
    # on Friday's run, catching every earnings announcement from the trading week.
    return datetime.now(timezone.utc).weekday() == 4


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Late imports so a broken import in one source doesn't abort the whole file load.
    from ingest.sources.compute_iv_rank import compute_iv_rank
    from ingest.sources.compute_reactions import compute_reactions
    from ingest.sources.nse_deals import ingest_deals
    from ingest.sources.nse_delivery import ingest_delivery
    from ingest.sources.nse_fii_dii import ingest_fii_dii
    from ingest.sources.nse_options import snapshot_options
    from ingest.sources.nse_prices import daily_update as ingest_prices_daily
    from ingest.sources.nse_universe import load_universe
    from ingest.sources.screener_earnings import ingest_earnings

    results = [
        _run("universe", load_universe),
        _run("prices_daily", ingest_prices_daily),
        _run("deals", ingest_deals),
        _run("fii_dii", ingest_fii_dii),
        _run("delivery", ingest_delivery),
        _run("options", snapshot_options),
        _run("compute_iv_rank", compute_iv_rank),
    ]

    if _should_run_weekly():
        results.append(_run("screener_earnings", ingest_earnings))

    # Always try to compute reactions for any new earnings events.
    results.append(_run("compute_reactions", compute_reactions))

    print("\n=== nightly summary ===")
    for name, status, detail in results:
        print(f"{name:>18}  {status:>7}  {detail}")

    failed = sum(1 for _, s, _ in results if s == "failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
