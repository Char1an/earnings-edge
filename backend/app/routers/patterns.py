from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Stock
from app.schemas.patterns import MatchedEventOut, PatternsResponse
from app.services.pattern_match import find_similar_setups

router = APIRouter(prefix="/stocks/{symbol}", tags=["patterns"])


@router.get("/patterns", response_model=PatternsResponse)
def patterns(
    symbol: str,
    k: int = Query(5, ge=1, le=20),
    anchor_event_id: int | None = Query(None, description="use a specific event as anchor"),
    session: Session = Depends(get_session),
) -> PatternsResponse:
    stock = session.execute(
        select(Stock).where(Stock.symbol == symbol.upper())
    ).scalar_one_or_none()
    if stock is None:
        raise HTTPException(404, f"stock {symbol!r} not found")

    r = find_similar_setups(
        session, stock.id, anchor_event_id=anchor_event_id, k=k
    )
    return PatternsResponse(
        stock_id=r.stock_id,
        anchor_event_id=r.anchor_event_id,
        anchor_features=r.anchor_features,
        feature_means=r.feature_means,
        feature_stds=r.feature_stds,
        matches=[MatchedEventOut(**vars(m)) for m in r.matches],
    )
