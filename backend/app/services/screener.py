"""Cross-universe screener.

Filters and ranks Nifty 500 stocks by a mix of live price signals (latest
close, 20-session drift) and their most recent earnings event (YoY / QoQ
growth, days since announcement, last reaction).

One SQL query per screen — uses Postgres DISTINCT ON / window functions
via a CTE. Result set is at most ~500 rows so we're comfortable pulling
into Python for the final sort + limit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

SORT_KEYS = (
    "symbol",
    "days_since_announcement",
    "drift_20d",
    "last_yoy_pat_growth",
    "last_yoy_revenue_growth",
    "last_day5_close_pct",
    "n_reactions",
)


@dataclass(frozen=True)
class ScreenRow:
    symbol: str
    name: str | None
    sector: str | None
    is_fno: bool

    latest_close: float | None
    latest_trade_date: date | None
    drift_20d: float | None

    last_event_id: int | None
    last_fiscal_period: str | None
    last_announcement_date: date | None
    days_since_announcement: int | None

    last_yoy_revenue_growth: float | None
    last_yoy_pat_growth: float | None

    last_gap_open_pct: float | None
    last_day1_close_pct: float | None
    last_day5_close_pct: float | None

    n_reactions: int


_SQL = text(
    """
    WITH latest_price AS (
        SELECT DISTINCT ON (stock_id)
            stock_id, trade_date AS latest_trade_date,
            close AS latest_close,
            COALESCE(adj_close, close) AS latest_adj
        FROM prices
        ORDER BY stock_id, trade_date DESC
    ),
    ranked_prices AS (
        SELECT stock_id, COALESCE(adj_close, close) AS adj,
               ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY trade_date DESC) AS rn
        FROM prices
    ),
    prior_price AS (
        SELECT stock_id, adj AS adj_21d_ago
        FROM ranked_prices
        WHERE rn = 21
    ),
    latest_event AS (
        SELECT DISTINCT ON (stock_id)
            stock_id, id, fiscal_period, announcement_date,
            yoy_revenue_growth, yoy_pat_growth
        FROM earnings_events
        ORDER BY stock_id, quarter_end DESC
    ),
    reaction_counts AS (
        SELECT e.stock_id, COUNT(*) AS n
        FROM earnings_events e
        JOIN earnings_reactions r ON r.earnings_event_id = e.id
        GROUP BY e.stock_id
    )
    SELECT
        s.symbol, s.name, s.sector, s.is_fno,
        lp.latest_close, lp.latest_trade_date,
        lp.latest_adj,
        pp.adj_21d_ago,
        le.id           AS last_event_id,
        le.fiscal_period AS last_fiscal_period,
        le.announcement_date AS last_announcement_date,
        le.yoy_revenue_growth AS last_yoy_revenue_growth,
        le.yoy_pat_growth AS last_yoy_pat_growth,
        rx.gap_open_pct   AS last_gap_open_pct,
        rx.day1_close_pct AS last_day1_close_pct,
        rx.day5_close_pct AS last_day5_close_pct,
        COALESCE(rc.n, 0) AS n_reactions
    FROM stocks s
    LEFT JOIN latest_price lp ON lp.stock_id = s.id
    LEFT JOIN prior_price pp ON pp.stock_id = s.id
    LEFT JOIN latest_event le ON le.stock_id = s.id
    LEFT JOIN earnings_reactions rx ON rx.earnings_event_id = le.id
    LEFT JOIN reaction_counts rc ON rc.stock_id = s.id
    WHERE s.in_nifty500 = TRUE
    """
)


def _to_float(v) -> float | None:
    return None if v is None else float(v)


def screen(
    session: Session,
    *,
    sector: str | None = None,
    fno_only: bool = False,
    min_yoy_pat_growth: float | None = None,
    min_yoy_revenue_growth: float | None = None,
    max_days_since_announcement: int | None = None,
    min_drift_20d: float | None = None,
    min_n_reactions: int | None = None,
    sort_by: str = "days_since_announcement",
    sort_desc: bool = False,
    limit: int = 50,
) -> list[ScreenRow]:
    if sort_by not in SORT_KEYS:
        raise ValueError(f"sort_by must be one of {SORT_KEYS}")

    today = date.today()
    raw = session.execute(_SQL).all()

    rows: list[ScreenRow] = []
    for r in raw:
        latest_close = _to_float(r.latest_close)
        # Drift is split-adjusted (adj_close) so a split inside the 21-session
        # window doesn't fake a huge move; latest_close stays raw for display.
        latest_adj = _to_float(r.latest_adj)
        prior_adj = _to_float(r.adj_21d_ago)
        drift = None
        if latest_adj is not None and prior_adj and prior_adj != 0:
            drift = round((latest_adj / prior_adj - 1.0) * 100.0, 3)

        days_since = None
        if r.last_announcement_date is not None:
            days_since = (today - r.last_announcement_date).days

        row = ScreenRow(
            symbol=r.symbol,
            name=r.name,
            sector=r.sector,
            is_fno=bool(r.is_fno),
            latest_close=latest_close,
            latest_trade_date=r.latest_trade_date,
            drift_20d=drift,
            last_event_id=r.last_event_id,
            last_fiscal_period=r.last_fiscal_period,
            last_announcement_date=r.last_announcement_date,
            days_since_announcement=days_since,
            last_yoy_revenue_growth=_to_float(r.last_yoy_revenue_growth),
            last_yoy_pat_growth=_to_float(r.last_yoy_pat_growth),
            last_gap_open_pct=_to_float(r.last_gap_open_pct),
            last_day1_close_pct=_to_float(r.last_day1_close_pct),
            last_day5_close_pct=_to_float(r.last_day5_close_pct),
            n_reactions=int(r.n_reactions or 0),
        )
        rows.append(row)

    # Apply filters (Python-side; result set is small)
    def keep(r: ScreenRow) -> bool:
        if sector and r.sector != sector:
            return False
        if fno_only and not r.is_fno:
            return False
        if min_yoy_pat_growth is not None and (
            r.last_yoy_pat_growth is None or r.last_yoy_pat_growth < min_yoy_pat_growth
        ):
            return False
        if min_yoy_revenue_growth is not None and (
            r.last_yoy_revenue_growth is None
            or r.last_yoy_revenue_growth < min_yoy_revenue_growth
        ):
            return False
        if max_days_since_announcement is not None and (
            r.days_since_announcement is None
            or r.days_since_announcement > max_days_since_announcement
        ):
            return False
        if min_drift_20d is not None and (r.drift_20d is None or r.drift_20d < min_drift_20d):
            return False
        return not (min_n_reactions is not None and r.n_reactions < min_n_reactions)

    rows = [r for r in rows if keep(r)]

    # Sort — always keep Nones at the end, regardless of direction. We can't
    # just add `v is None` to the tuple because `reverse=True` would flip that
    # too and float Nones to the top. Partition, then sort each side.
    with_val = [r for r in rows if getattr(r, sort_by) is not None]
    without_val = [r for r in rows if getattr(r, sort_by) is None]
    with_val.sort(key=lambda r: getattr(r, sort_by), reverse=sort_desc)
    rows = with_val + without_val
    return rows[:limit]
