"""Aggregate 30-day positioning signals for a stock.

    - recent_deals            list of bulk/block deals (last N days)
    - deals_net_value_cr      buy - sell aggregate over window
    - deals_buy_count / sell  count of each side
    - fii_net_30d_cr          market-wide FII cash net summed over the window
    - dii_net_30d_cr          market-wide DII cash net summed over the window
    - delivery_pct_recent     mean delivery % over last 20 trading days
    - delivery_pct_baseline   mean delivery % over the 60 sessions prior
    - delivery_pct_delta      recent - baseline (in percentage points)

Note: FII/DII here is the *market* aggregate, not this stock's flow —
we don't have per-stock institutional flow data. It's still useful as a
regime indicator.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.models import Deal, FiiDiiFlow, Price

DEFAULT_WINDOW_DAYS = 30
DELIVERY_RECENT_SESSIONS = 20
DELIVERY_BASELINE_SESSIONS = 60


@dataclass(frozen=True)
class DealOut:
    trade_date: date
    deal_type: str
    exchange: str
    client_name: str | None
    buy_sell: str
    quantity: int
    price: float
    value_cr: float | None


@dataclass(frozen=True)
class PositioningResult:
    stock_id: int
    window_days: int
    recent_deals: list[DealOut]
    deals_buy_count: int
    deals_sell_count: int
    deals_net_value_cr: float
    fii_net_window_cr: float | None
    dii_net_window_cr: float | None
    delivery_pct_recent: float | None
    delivery_pct_baseline: float | None
    delivery_pct_delta: float | None


def _fetch_recent_deals(session: Session, stock_id: int, since: date) -> list[DealOut]:
    rows = session.execute(
        select(Deal)
        .where(and_(Deal.stock_id == stock_id, Deal.trade_date >= since))
        .order_by(desc(Deal.trade_date), desc(Deal.value_cr))
    ).scalars()
    return [
        DealOut(
            trade_date=d.trade_date,
            deal_type=d.deal_type,
            exchange=d.exchange,
            client_name=d.client_name or None,
            buy_sell=d.buy_sell,
            quantity=int(d.quantity),
            price=float(d.price),
            value_cr=float(d.value_cr) if d.value_cr is not None else None,
        )
        for d in rows
    ]


def _summarize_deals(deals: list[DealOut]) -> tuple[int, int, float]:
    buy_count = sum(1 for d in deals if d.buy_sell == "BUY")
    sell_count = sum(1 for d in deals if d.buy_sell == "SELL")
    net = sum(
        (d.value_cr or 0.0) * (1 if d.buy_sell == "BUY" else -1) for d in deals
    )
    return buy_count, sell_count, round(net, 3)


def _fii_dii_sum(session: Session, since: date) -> tuple[float | None, float | None]:
    row = session.execute(
        select(
            func.sum(FiiDiiFlow.fii_cash_net_cr),
            func.sum(FiiDiiFlow.dii_cash_net_cr),
        ).where(FiiDiiFlow.trade_date >= since)
    ).first()
    fii = float(row[0]) if row and row[0] is not None else None
    dii = float(row[1]) if row and row[1] is not None else None
    return fii, dii


def _delivery_windows(
    session: Session, stock_id: int
) -> tuple[float | None, float | None]:
    # Two-tier: latest 20 sessions vs. the 60 sessions before that.
    rows = session.execute(
        select(Price.trade_date, Price.delivery_pct)
        .where(and_(Price.stock_id == stock_id, Price.delivery_pct.is_not(None)))
        .order_by(desc(Price.trade_date))
        .limit(DELIVERY_RECENT_SESSIONS + DELIVERY_BASELINE_SESSIONS)
    ).all()
    if len(rows) < DELIVERY_RECENT_SESSIONS + 5:
        return None, None
    recent_vals = [float(r[1]) for r in rows[:DELIVERY_RECENT_SESSIONS]]
    baseline_vals = [float(r[1]) for r in rows[DELIVERY_RECENT_SESSIONS:]]
    recent = round(sum(recent_vals) / len(recent_vals), 3) if recent_vals else None
    baseline = (
        round(sum(baseline_vals) / len(baseline_vals), 3) if baseline_vals else None
    )
    return recent, baseline


def compute_positioning(
    session: Session, stock_id: int, window_days: int = DEFAULT_WINDOW_DAYS
) -> PositioningResult:
    since = date.today() - timedelta(days=window_days)

    deals = _fetch_recent_deals(session, stock_id, since)
    buy_count, sell_count, net = _summarize_deals(deals)

    fii, dii = _fii_dii_sum(session, since)
    recent_deliv, baseline_deliv = _delivery_windows(session, stock_id)
    delta = (
        round(recent_deliv - baseline_deliv, 3)
        if recent_deliv is not None and baseline_deliv is not None
        else None
    )

    return PositioningResult(
        stock_id=stock_id,
        window_days=window_days,
        recent_deals=deals,
        deals_buy_count=buy_count,
        deals_sell_count=sell_count,
        deals_net_value_cr=net,
        fii_net_window_cr=fii,
        dii_net_window_cr=dii,
        delivery_pct_recent=recent_deliv,
        delivery_pct_baseline=baseline_deliv,
        delivery_pct_delta=delta,
    )
