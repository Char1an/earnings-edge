from datetime import date

from pydantic import BaseModel, ConfigDict


class EarningsEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fiscal_period: str
    quarter_end: date
    announcement_date: date | None
    revenue_cr: float | None
    pat_cr: float | None
    eps: float | None
    opm_pct: float | None
    yoy_revenue_growth: float | None
    yoy_pat_growth: float | None
    qoq_revenue_growth: float | None
    qoq_pat_growth: float | None


class EarningsReactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pre_close: float | None
    gap_open_pct: float | None
    day1_close_pct: float | None
    day3_close_pct: float | None
    day5_close_pct: float | None
    day1_high_pct: float | None
    day1_low_pct: float | None
    volume_spike: float | None
    detection_method: str | None
    detection_confidence: float | None


class EarningsHistoryItem(BaseModel):
    event: EarningsEventOut
    reaction: EarningsReactionOut | None


class Distribution(BaseModel):
    metric: str
    n: int
    mean: float | None
    median: float | None
    p25: float | None
    p75: float | None
    min: float | None
    max: float | None
    hist_bin_edges: list[float]
    hist_counts: list[int]


class BaseRatesResponse(BaseModel):
    stock_id: int
    n_events: int
    filters_applied: dict
    distributions: dict[str, Distribution]
