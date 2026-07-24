from datetime import date

from pydantic import BaseModel


class ScreenerRow(BaseModel):
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


class ScreenerResponse(BaseModel):
    filters: dict
    n: int
    rows: list[ScreenerRow]
