from datetime import date

from pydantic import BaseModel


class DealItem(BaseModel):
    trade_date: date
    deal_type: str
    exchange: str
    client_name: str | None
    buy_sell: str
    quantity: int
    price: float
    value_cr: float | None


class PositioningResponse(BaseModel):
    stock_id: int
    window_days: int
    recent_deals: list[DealItem]
    deals_buy_count: int
    deals_sell_count: int
    deals_net_value_cr: float
    fii_net_window_cr: float | None
    dii_net_window_cr: float | None
    delivery_pct_recent: float | None
    delivery_pct_baseline: float | None
    delivery_pct_delta: float | None
