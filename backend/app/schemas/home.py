from datetime import date

from pydantic import BaseModel


class UpcomingItem(BaseModel):
    symbol: str
    name: str | None
    sector: str | None
    last_fiscal_period: str | None
    last_announcement_date: date | None
    expected_next_date: date
    days_until: int


class NotableDeal(BaseModel):
    symbol: str
    name: str | None
    trade_date: date
    deal_type: str
    buy_sell: str
    client_name: str | None
    quantity: int
    price: float
    value_cr: float | None


class FlowPoint(BaseModel):
    trade_date: date
    fii_cash_net_cr: float | None
    dii_cash_net_cr: float | None


class HomeResponse(BaseModel):
    upcoming: list[UpcomingItem]
    notable_deals: list[NotableDeal]
    fii_dii_series: list[FlowPoint]
