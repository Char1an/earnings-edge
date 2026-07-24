from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.home import FlowPoint, HomeResponse, NotableDeal, UpcomingItem
from app.services.home import home_bundle

router = APIRouter(prefix="/home", tags=["home"])


@router.get("", response_model=HomeResponse)
def home(
    upcoming_days: int = Query(14, ge=1, le=90),
    deals_days: int = Query(7, ge=1, le=90),
    deals_limit: int = Query(15, ge=1, le=100),
    flows_days: int = Query(30, ge=1, le=365),
    session: Session = Depends(get_session),
) -> HomeResponse:
    p = home_bundle(
        session,
        upcoming_days=upcoming_days,
        deals_days=deals_days,
        deals_limit=deals_limit,
        flows_days=flows_days,
    )
    return HomeResponse(
        upcoming=[UpcomingItem(**vars(u)) for u in p.upcoming],
        notable_deals=[NotableDeal(**vars(d)) for d in p.notable_deals],
        fii_dii_series=[FlowPoint(**vars(f)) for f in p.fii_dii_series],
    )
