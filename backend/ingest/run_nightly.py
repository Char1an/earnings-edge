"""Nightly orchestrator. Runs all daily ingest jobs fail-soft.

Order matters:
  1. universe   (idempotent, cheap; keeps stocks + F&O flags fresh)
  2. prices     (OHLCV daily update, last 7d)
  3. deals      (bulk + block rolling CSVs)
  4. fii_dii    (cash net for last 1-2 days)
  5. delivery   (updates prices rows with delivery %)

Each job wraps its own IngestRun. This wrapper only sequences them and
prints a summary; one failed job never blocks the next.
"""
from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import Callable

log = logging.getLogger(__name__)


def _run(name: str, fn: Callable[[], int]) -> tuple[str, str, int | str]:
    try:
        n = fn()
        return (name, "ok", n)
    except Exception as e:
        log.error("%s failed: %s", name, e)
        traceback.print_exc()
        return (name, "failed", f"{type(e).__name__}: {e}")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Late imports so a broken import in one source doesn't abort the whole file load.
    from ingest.sources.nse_deals import ingest_deals
    from ingest.sources.nse_delivery import ingest_delivery
    from ingest.sources.nse_fii_dii import ingest_fii_dii
    from ingest.sources.nse_prices import daily_update as ingest_prices_daily
    from ingest.sources.nse_universe import load_universe

    results = [
        _run("universe", load_universe),
        _run("prices_daily", ingest_prices_daily),
        _run("deals", ingest_deals),
        _run("fii_dii", ingest_fii_dii),
        _run("delivery", ingest_delivery),
    ]

    print("\n=== nightly summary ===")
    for name, status, detail in results:
        print(f"{name:>14}  {status:>7}  {detail}")

    failed = sum(1 for _, s, _ in results if s == "failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
