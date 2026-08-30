"""Context manager to log ingest jobs to the `ingest_runs` table.

Uses short-lived sessions: one to INSERT the initial row, another to UPDATE the
final status. Never holds a session open across the yield — otherwise a
long-running ingest (>3h) trips Neon's IdleInTransactionSessionTimeout and the
closing UPDATE crashes even though every per-item commit already succeeded.
That was the "cosmetic" nightly failure surfaced during the 6-day catch-up run
in Aug 2026 — universe, prices_daily etc. all wrote data but two jobs reported
`failed` because only the bookkeeping UPDATE at the end timed out.

Callers only ever mutate `rows_written`, `status`, and `error` on the yielded
handle, so we don't need a live ORM object here — a plain dataclass is enough.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import update

from app.db import SessionLocal
from app.models import IngestRun


@dataclass
class RunHandle:
    """Mutable state a caller can set inside `with track_run(...) as run:`.
    Whatever is on the handle at exit is written back to ingest_runs by _finalize.
    """

    id: int
    rows_written: int = 0
    status: str = "running"
    error: str | None = None


def _finalize(h: RunHandle) -> None:
    """Single UPDATE via a short-lived fresh session — cannot be idle-timed-out."""
    with SessionLocal() as s:
        s.execute(
            update(IngestRun)
            .where(IngestRun.id == h.id)
            .values(
                status=h.status,
                error=h.error,
                rows_written=h.rows_written,
                finished_at=datetime.now(UTC),
            )
        )
        s.commit()


@contextmanager
def track_run(job_name: str):
    """
    with track_run("nse_prices_backfill") as run:
        ...
        run.rows_written += n
    """
    with SessionLocal() as s:
        row = IngestRun(job_name=job_name, status="running")
        s.add(row)
        s.commit()
        run_id = row.id

    handle = RunHandle(id=run_id)
    try:
        yield handle
    except Exception as e:
        handle.status = "failed"
        handle.error = f"{type(e).__name__}: {e}"[:2000]
        _finalize(handle)
        raise
    else:
        if handle.status == "running":
            handle.status = "ok"
        _finalize(handle)
