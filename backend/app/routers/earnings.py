import bisect
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import EarningsEvent, EarningsReaction, Price, Stock
from app.schemas.earnings import (
    BaseRatesResponse,
    Distribution,
    EarningsEventOut,
    EarningsHistoryItem,
    EarningsReactionOut,
    EventTimeline,
    TimelinePoint,
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
    if only_beat_yoy_pat and only_miss_yoy_pat:
        raise HTTPException(400, "only_beat_yoy_pat and only_miss_yoy_pat are mutually exclusive")

    stock = _resolve_stock(session, symbol)

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


@router.get("/earnings/timelines", response_model=list[EventTimeline])
def earnings_timelines(
    symbol: str,
    window: int = Query(10, ge=1, le=30, description="trading sessions each side"),
    limit: int = Query(20, ge=1, le=80, description="most-recent N events"),
    session: Session = Depends(get_session),
) -> list[EventTimeline]:
    """Price path around each earnings event, normalized to pre_close = 0%.

    Offset convention: 0 = first trading day on/after announcement (the reaction
    day). Offset -1 = last trading day strictly before announcement (this is the
    pre_close baseline). Offsets range [-window, +window] but real trading days
    only — no synthetic weekend padding.
    """
    stock = _resolve_stock(session, symbol)

    events = session.execute(
        select(EarningsEvent.id, EarningsEvent.fiscal_period, EarningsEvent.announcement_date)
        .where(EarningsEvent.stock_id == stock.id)
        .where(EarningsEvent.announcement_date.is_not(None))
        .order_by(desc(EarningsEvent.quarter_end))
        .limit(limit)
    ).all()
    if not events:
        return []

    ann_dates = [e.announcement_date for e in events]
    # Buffer generously — weekends + holidays mean N trading days needs ~1.5N calendar days.
    buffer = timedelta(days=window * 2 + 20)
    span_start = min(ann_dates) - buffer
    span_end = max(ann_dates) + buffer

    price_rows = session.execute(
        select(Price.trade_date, Price.close)
        .where(Price.stock_id == stock.id)
        .where(Price.trade_date.between(span_start, span_end))
        .order_by(asc(Price.trade_date))
    ).all()
    if not price_rows:
        return []

    date_list = [r.trade_date for r in price_rows]
    close_list = [float(r.close) for r in price_rows]

    out: list[EventTimeline] = []
    for ev in events:
        a = ev.announcement_date
        # First trading day >= announcement_date is the "day 0" reaction day.
        idx0 = bisect.bisect_left(date_list, a)
        if idx0 == 0 or idx0 >= len(date_list):
            continue  # not enough surrounding data
        pre_idx = idx0 - 1
        pre_close = close_list[pre_idx]
        if pre_close <= 0:
            continue

        points: list[TimelinePoint] = []
        for offset in range(-window, window + 1):
            i = idx0 + offset
            if i < 0 or i >= len(date_list):
                continue
            points.append(TimelinePoint(
                offset=offset,
                trade_date=date_list[i],
                close=round(close_list[i], 3),
                pct_from_pre=round((close_list[i] / pre_close - 1.0) * 100.0, 3),
            ))

        out.append(EventTimeline(
            event_id=ev.id,
            fiscal_period=ev.fiscal_period,
            announcement_date=a,
            pre_close=round(pre_close, 3),
            points=points,
        ))

    return out
