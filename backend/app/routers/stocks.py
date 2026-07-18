from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Price, Stock
from app.schemas.stock import StockDetail, StockSummary

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=list[StockSummary])
def list_stocks(
    q: str | None = Query(None, description="prefix match on symbol"),
    sector: str | None = None,
    in_fno: bool | None = None,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[Stock]:
    stmt = select(Stock).where(Stock.in_nifty500.is_(True))
    if q:
        stmt = stmt.where(Stock.symbol.ilike(f"{q}%"))
    if sector:
        stmt = stmt.where(Stock.sector == sector)
    if in_fno is not None:
        stmt = stmt.where(Stock.is_fno.is_(in_fno))
    stmt = stmt.order_by(Stock.symbol).limit(limit)
    return list(session.execute(stmt).scalars())


@router.get("/{symbol}", response_model=StockDetail)
def get_stock(symbol: str, session: Session = Depends(get_session)) -> StockDetail:
    stock = session.execute(
        select(Stock).where(Stock.symbol == symbol.upper())
    ).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock {symbol!r} not found")

    latest = session.execute(
        select(Price.trade_date, Price.close, Price.delivery_pct)
        .where(Price.stock_id == stock.id)
        .order_by(desc(Price.trade_date))
        .limit(1)
    ).first()

    out = StockDetail.model_validate(stock)
    if latest:
        out = out.model_copy(
            update={
                "latest_trade_date": latest[0],
                "latest_close": float(latest[1]) if latest[1] is not None else None,
                "latest_delivery_pct": float(latest[2]) if latest[2] is not None else None,
            }
        )
    return out
