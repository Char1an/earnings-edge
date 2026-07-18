from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import EarningsEvent, EarningsReaction, Stock
from app.schemas.earnings import (
    BaseRatesResponse,
    Distribution,
    EarningsEventOut,
    EarningsHistoryItem,
    EarningsReactionOut,
)
from app.services.base_rates import compute_base_rates

router = APIRouter(prefix="/stocks/{symbol}", tags=["earnings"])


def _resolve_stock(session: Session, symbol: str) -> Stock:
    stock = session.execute(
        select(Stock).where(Stock.symbol == symbol.upper())
    ).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock {symbol!r} not found")
    return stock


@router.get("/earnings/history", response_model=list[EarningsHistoryItem])
def earnings_history(
    symbol: str,
    limit: int = Query(20, ge=1, le=80, description="most-recent N"),
    session: Session = Depends(get_session),
) -> list[EarningsHistoryItem]:
    stock = _resolve_stock(session, symbol)

    rows = session.execute(
        select(EarningsEvent, EarningsReaction)
        .outerjoin(EarningsReaction, EarningsReaction.earnings_event_id == EarningsEvent.id)
        .where(EarningsEvent.stock_id == stock.id)
        .order_by(desc(EarningsEvent.quarter_end))
        .limit(limit)
    ).all()

    return [
        EarningsHistoryItem(
            event=EarningsEventOut.model_validate(ev),
            reaction=EarningsReactionOut.model_validate(rx) if rx is not None else None,
        )
        for ev, rx in rows
    ]


@router.get("/base-rates", response_model=BaseRatesResponse)
def base_rates(
    symbol: str,
    min_confidence: float | None = Query(None, ge=0, description="reactions with confidence >="),
    only_beat_yoy_pat: bool = False,
    only_miss_yoy_pat: bool = False,
    session: Session = Depends(get_session),
) -> BaseRatesResponse:
    stock = _resolve_stock(session, symbol)

    if only_beat_yoy_pat and only_miss_yoy_pat:
        raise HTTPException(400, "only_beat_yoy_pat and only_miss_yoy_pat are mutually exclusive")

    result = compute_base_rates(
        session,
        stock.id,
        min_confidence=min_confidence,
        only_beat_yoy_pat=only_beat_yoy_pat,
        only_miss_yoy_pat=only_miss_yoy_pat,
    )
    return BaseRatesResponse(
        stock_id=result.stock_id,
        n_events=result.n_events,
        filters_applied=result.filters_applied,
        distributions={
            k: Distribution(**vars(d)) for k, d in result.distributions.items()
        },
    )
