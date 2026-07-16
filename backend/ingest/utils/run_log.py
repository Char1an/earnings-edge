"""Context manager to log ingest jobs to the `ingest_runs` table."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import IngestRun


@contextmanager
def track_run(job_name: str):
    """
    with track_run("nse_prices_backfill") as run:
        ...
        run.rows_written += n
    """
    session: Session = SessionLocal()
    run = IngestRun(job_name=job_name, status="running")
    session.add(run)
    session.commit()
    session.refresh(run)
    try:
        yield run
    except Exception as e:
        run.status = "failed"
        run.error = f"{type(e).__name__}: {e}"[:2000]
        run.finished_at = datetime.now(timezone.utc)
        session.commit()
        raise
    else:
        if run.status == "running":
            run.status = "ok"
        run.finished_at = datetime.now(timezone.utc)
        session.commit()
    finally:
        session.close()
