from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.screener import ScreenerResponse, ScreenerRow
from app.services.screener import SORT_KEYS, screen

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("", response_model=ScreenerResponse)
def screener(
    sector: str | None = None,
    fno_only: bool = False,
    min_yoy_pat_growth: float | None = Query(None, description="% e.g. 10 for +10%"),
    min_yoy_revenue_growth: float | None = None,
    max_days_since_announcement: int | None = None,
    min_drift_20d: float | None = None,
    min_n_reactions: int | None = None,
    sort_by: str = Query("days_since_announcement", description=f"one of {SORT_KEYS}"),
    sort_desc: bool = False,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
) -> ScreenerResponse:
    if sort_by not in SORT_KEYS:
        raise HTTPException(400, f"sort_by must be one of {SORT_KEYS}")

    rows = screen(
        session,
        sector=sector,
        fno_only=fno_only,
        min_yoy_pat_growth=min_yoy_pat_growth,
        min_yoy_revenue_growth=min_yoy_revenue_growth,
        max_days_since_announcement=max_days_since_announcement,
        min_drift_20d=min_drift_20d,
        min_n_reactions=min_n_reactions,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
    )

    filters = {
        k: v
        for k, v in {
            "sector": sector,
            "fno_only": fno_only or None,
            "min_yoy_pat_growth": min_yoy_pat_growth,
            "min_yoy_revenue_growth": min_yoy_revenue_growth,
            "max_days_since_announcement": max_days_since_announcement,
            "min_drift_20d": min_drift_20d,
            "min_n_reactions": min_n_reactions,
            "sort_by": sort_by,
            "sort_desc": sort_desc or None,
            "limit": limit,
        }.items()
        if v not in (None, False)
    }

    return ScreenerResponse(
        filters=filters,
        n=len(rows),
        rows=[ScreenerRow(**vars(r)) for r in rows],
    )
