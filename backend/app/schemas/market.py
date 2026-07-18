from datetime import date

from pydantic import BaseModel, ConfigDict


class FiiDiiPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_date: date
    fii_cash_net_cr: float | None
    dii_cash_net_cr: float | None
