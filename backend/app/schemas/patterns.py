from pydantic import BaseModel


class MatchedEventOut(BaseModel):
    event_id: int
    fiscal_period: str
    announcement_date: str | None
    similarity: float
    features: dict[str, float | None]
    reaction: dict[str, float | None] | None


class PatternsResponse(BaseModel):
    stock_id: int
    anchor_event_id: int | None
    anchor_features: dict[str, float | None]
    feature_means: dict[str, float]
    feature_stds: dict[str, float]
    matches: list[MatchedEventOut]
