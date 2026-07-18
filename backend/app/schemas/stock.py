from datetime import date

from pydantic import BaseModel, ConfigDict


class StockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str | None
    sector: str | None
    industry: str | None
    in_nifty50: bool
    in_nifty500: bool
    is_fno: bool


class StockDetail(StockSummary):
    isin: str | None
    market_cap_cr: float | None
    latest_close: float | None = None
    latest_trade_date: date | None = None
    latest_delivery_pct: float | None = None
