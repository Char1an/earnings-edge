"""Historical earnings-reaction base rates for a stock.

Given a stock and optional filters, load its earnings_reactions and return
distribution statistics (mean/median/quartiles) and a histogram, per metric.

The filters are simple, boolean-composable predicates on the event itself:
    - min_confidence:      only reactions with detection_confidence >= x
    - beat_yoy_pat:        only quarters where yoy_pat_growth > 0
    - miss_yoy_pat:        only quarters where yoy_pat_growth <= 0
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EarningsEvent, EarningsReaction

METRICS = ("gap_open_pct", "day1_close_pct", "day3_close_pct", "day5_close_pct")
Metric = Literal["gap_open_pct", "day1_close_pct", "day3_close_pct", "day5_close_pct"]


@dataclass(frozen=True)
class Distribution:
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


@dataclass(frozen=True)
class BaseRatesResult:
    stock_id: int
    n_events: int
    filters_applied: dict
    distributions: dict[str, Distribution]


def _distribution(values: list[float], metric: str, bins: int = 15) -> Distribution:
    arr = np.array([v for v in values if v is not None], dtype=float)
    n = int(arr.size)
    if n == 0:
        return Distribution(
            metric=metric,
            n=0,
            mean=None,
            median=None,
            p25=None,
            p75=None,
            min=None,
            max=None,
            hist_bin_edges=[],
            hist_counts=[],
        )
    counts, edges = np.histogram(arr, bins=bins)
    return Distribution(
        metric=metric,
        n=n,
        mean=float(round(arr.mean(), 3)),
        median=float(round(np.median(arr), 3)),
        p25=float(round(np.percentile(arr, 25), 3)),
        p75=float(round(np.percentile(arr, 75), 3)),
        min=float(round(arr.min(), 3)),
        max=float(round(arr.max(), 3)),
        hist_bin_edges=[round(float(x), 3) for x in edges.tolist()],
        hist_counts=[int(c) for c in counts.tolist()],
    )


def compute_base_rates(
    session: Session,
    stock_id: int,
    *,
    min_confidence: float | None = None,
    only_beat_yoy_pat: bool = False,
    only_miss_yoy_pat: bool = False,
) -> BaseRatesResult:
    q = (
        select(
            EarningsReaction.gap_open_pct,
            EarningsReaction.day1_close_pct,
            EarningsReaction.day3_close_pct,
            EarningsReaction.day5_close_pct,
            EarningsReaction.detection_confidence,
            EarningsEvent.yoy_pat_growth,
        )
        .join(EarningsEvent, EarningsEvent.id == EarningsReaction.earnings_event_id)
        .where(EarningsEvent.stock_id == stock_id)
    )
    if min_confidence is not None:
        q = q.where(EarningsReaction.detection_confidence >= min_confidence)
    if only_beat_yoy_pat:
        q = q.where(EarningsEvent.yoy_pat_growth > 0)
    if only_miss_yoy_pat:
        q = q.where(EarningsEvent.yoy_pat_growth <= 0)

    rows = session.execute(q).all()
    buckets: dict[str, list[float]] = {m: [] for m in METRICS}
    for r in rows:
        for i, m in enumerate(METRICS):
            v = r[i]
            if v is not None:
                buckets[m].append(float(v))

    distributions = {m: _distribution(vs, m) for m, vs in buckets.items()}

    filters_applied = {
        k: v
        for k, v in {
            "min_confidence": min_confidence,
            "only_beat_yoy_pat": only_beat_yoy_pat or None,
            "only_miss_yoy_pat": only_miss_yoy_pat or None,
        }.items()
        if v not in (None, False)
    }

    return BaseRatesResult(
        stock_id=stock_id,
        n_events=len(rows),
        filters_applied=filters_applied,
        distributions=distributions,
    )
