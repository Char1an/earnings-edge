"""Home-page data bundle.

Combines three data sources into one endpoint response:
  - upcoming earnings (next N days, inferred as last_announcement + ~91 days)
  - notable deals (last N days, top K by value)
  - FII/DII flows time series (last N days)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from app.models import Deal, FiiDiiFlow, Stock

# Median gap between last quarter's announcement and the next quarter's announcement
# for large-cap Indian companies. Rough — this is a heuristic, not a scraped calendar.
NEXT_ANNOUNCEMENT_GAP_DAYS = 91


@dataclass(frozen=True)
class UpcomingItem:
    symbol: str
    name: str | None
    sector: str | None
    last_fiscal_period: str | None
    last_announcement_date: date | None
    expected_next_date: date
    days_until: int


@dataclass(frozen=True)
class NotableDeal:
    symbol: str
    name: str | None
    trade_date: date
    deal_type: str
    buy_sell: str
    client_name: str | None
    quantity: int
    price: float
    value_cr: float | None


@dataclass(frozen=True)
class FlowPoint:
    trade_date: date
    fii_cash_net_cr: float | None
    dii_cash_net_cr: float | None


@dataclass(frozen=True)
class HomePayload:
    upcoming: list[UpcomingItem]
    notable_deals: list[NotableDeal]
    fii_dii_series: list[FlowPoint]


_UPCOMING_SQL = text(
    """
    WITH latest_event AS (
        SELECT DISTINCT ON (stock_id)
            stock_id, fiscal_period, announcement_date
        FROM earnings_events
        WHERE announcement_date IS NOT NULL
        ORDER BY stock_id, announcement_date DESC
    )
    SELECT s.symbol, s.name, s.sector,
           le.fiscal_period AS last_fiscal_period,
           le.announcement_date AS last_announcement_date
    FROM stocks s
    JOIN latest_event le ON le.stock_id = s.id
    WHERE s.in_nifty500 = TRUE
    """
)


def _upcoming(session: Session, days_ahead: int) -> list[UpcomingItem]:
    today = date.today()
    rows = session.execute(_UPCOMING_SQL).all()
    out: list[UpcomingItem] = []
    for r in rows:
        last = r.last_announcement_date
        if last is None:
            continue
        expected = last + timedelta(days=NEXT_ANNOUNCEMENT_GAP_DAYS)
        days_until = (expected - today).days
        # Only quarters ahead of us within the requested window
        if days_until < 0 or days_until > days_ahead:
            continue
        out.append(
            UpcomingItem(
                symbol=r.symbol,
                name=r.name,
                sector=r.sector,
                last_fiscal_period=r.last_fiscal_period,
                last_announcement_date=last,
                expected_next_date=expected,
                days_until=days_until,
            )
        )
    out.sort(key=lambda x: x.expected_next_date)
    return out


def _notable_deals(session: Session, days_back: int, limit: int) -> list[NotableDeal]:
    since = date.today() - timedelta(days=days_back)
    rows = session.execute(
        select(Deal, Stock.symbol, Stock.name)
        .join(Stock, Stock.id == Deal.stock_id)
        .where(Deal.trade_date >= since)
        .order_by(desc(Deal.value_cr).nulls_last(), desc(Deal.trade_date))
        .limit(limit)
    ).all()
    return [
        NotableDeal(
            symbol=sym,
            name=name,
            trade_date=d.trade_date,
            deal_type=d.deal_type,
            buy_sell=d.buy_sell,
            client_name=d.client_name or None,
            quantity=int(d.quantity),
            price=float(d.price),
            value_cr=float(d.value_cr) if d.value_cr is not None else None,
        )
        for d, sym, name in rows
    ]


def _fii_dii_series(session: Session, days_back: int) -> list[FlowPoint]:
    since = date.today() - timedelta(days=days_back)
    rows = session.execute(
        select(FiiDiiFlow)
        .where(FiiDiiFlow.trade_date >= since)
        .order_by(FiiDiiFlow.trade_date.asc())
    ).scalars()
    return [
        FlowPoint(
            trade_date=f.trade_date,
            fii_cash_net_cr=float(f.fii_cash_net_cr) if f.fii_cash_net_cr is not None else None,
            dii_cash_net_cr=float(f.dii_cash_net_cr) if f.dii_cash_net_cr is not None else None,
        )
        for f in rows
    ]


def home_bundle(
    session: Session,
    *,
    upcoming_days: int = 14,
    deals_days: int = 7,
    deals_limit: int = 15,
    flows_days: int = 30,
) -> HomePayload:
    return HomePayload(
        upcoming=_upcoming(session, upcoming_days),
        notable_deals=_notable_deals(session, deals_days, deals_limit),
        fii_dii_series=_fii_dii_series(session, flows_days),
    )
