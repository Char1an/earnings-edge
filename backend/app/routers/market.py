from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import FiiDiiFlow
from app.schemas.market import FiiDiiPoint

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/flows", response_model=list[FiiDiiPoint])
def market_flows(
    days: int = Query(90, ge=1, le=730),
    session: Session = Depends(get_session),
) -> list[FiiDiiFlow]:
    since = date.today() - timedelta(days=days)
    stmt = (
        select(FiiDiiFlow)
        .where(FiiDiiFlow.trade_date >= since)
        .order_by(FiiDiiFlow.trade_date.asc())
    )
    return list(session.execute(stmt).scalars())
