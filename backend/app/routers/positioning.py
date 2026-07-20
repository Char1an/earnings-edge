from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Stock
from app.schemas.positioning import DealItem, PositioningResponse
from app.services.positioning import compute_positioning

router = APIRouter(prefix="/stocks/{symbol}", tags=["positioning"])


@router.get("/positioning", response_model=PositioningResponse)
def positioning(
    symbol: str,
    window_days: int = Query(30, ge=1, le=180),
    session: Session = Depends(get_session),
) -> PositioningResponse:
    stock = session.execute(
        select(Stock).where(Stock.symbol == symbol.upper())
    ).scalar_one_or_none()
    if stock is None:
        raise HTTPException(404, f"stock {symbol!r} not found")

    r = compute_positioning(session, stock.id, window_days=window_days)
    return PositioningResponse(
        stock_id=r.stock_id,
        window_days=r.window_days,
        recent_deals=[DealItem(**vars(d)) for d in r.recent_deals],
        deals_buy_count=r.deals_buy_count,
        deals_sell_count=r.deals_sell_count,
        deals_net_value_cr=r.deals_net_value_cr,
        fii_net_window_cr=r.fii_net_window_cr,
        dii_net_window_cr=r.dii_net_window_cr,
        delivery_pct_recent=r.delivery_pct_recent,
        delivery_pct_baseline=r.delivery_pct_baseline,
        delivery_pct_delta=r.delivery_pct_delta,
    )
