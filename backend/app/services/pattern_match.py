"""Find the K most-similar prior earnings events for a stock.

For each earnings_event we build a small feature vector from data we already
have — YoY / QoQ growth rates plus the stock's 20-session pre-announcement
price drift. Features are z-score standardized against that stock's own
history, then cosine similarity ranks past events against the anchor event.

Anchor selection:
    - If event_id is passed, use that event
    - Otherwise use the stock's most recent event that has an announcement_date

Only anchors and candidates with a computed reaction show up in results (an
event with no reaction has no "what happened next" to report).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import EarningsEvent, EarningsReaction, Price

FEATURE_KEYS = (
    "yoy_revenue_growth",
    "yoy_pat_growth",
    "qoq_revenue_growth",
    "qoq_pat_growth",
    "drift_20d",
    # Cyclical encoding of fiscal quarter so same-quarter events (Q1↔Q1) contribute
    # +1 to the dot product and opposite-quarter events (Q1↔Q3) contribute -1 —
    # the growth-only vector was missing this: TCS Q1FY27 vs Q1FY25 had near-
    # identical day-5 reactions but sim ≈ 0 because YoY numbers diverged.
    "fiscal_q_sin",
    "fiscal_q_cos",
)

_FISCAL_Q_RE = re.compile(r"^Q([1-4])FY\d+$", re.IGNORECASE)


def _parse_quarter(fiscal_period: str | None) -> int | None:
    if not fiscal_period:
        return None
    m = _FISCAL_Q_RE.match(fiscal_period.strip())
    return int(m.group(1)) if m else None


@dataclass(frozen=True)
class MatchedEvent:
    event_id: int
    fiscal_period: str
    announcement_date: str | None
    similarity: float
    features: dict[str, float | None]
    reaction: dict[str, float | None] | None


@dataclass(frozen=True)
class PatternResult:
    stock_id: int
    anchor_event_id: int | None
    anchor_features: dict[str, float | None]
    feature_means: dict[str, float]
    feature_stds: dict[str, float]
    matches: list[MatchedEvent]


def _drift_20d(session: Session, stock_id: int, ref_date) -> float | None:
    """Return (close_t / close_t-20 - 1) * 100 using the 21 sessions up to and
    including ref_date. Split-adjusted (adj_close where available). None if
    there isn't enough history."""
    rows = session.execute(
        select(Price.trade_date, Price.close, Price.adj_close)
        .where(Price.stock_id == stock_id)
        .where(Price.trade_date <= ref_date)
        .order_by(desc(Price.trade_date))
        .limit(21)
    ).all()
    if len(rows) < 21:
        return None
    closes = [float(r.adj_close if r.adj_close is not None else r.close) for r in rows]
    latest, older = closes[0], closes[-1]
    if older == 0:
        return None
    return round((latest / older - 1.0) * 100.0, 3)


def _feature_vector(session: Session, event: EarningsEvent) -> dict[str, float | None]:
    ref_date = None
    if event.announcement_date is not None:
        ref_date = event.announcement_date - timedelta(days=1)
    elif event.quarter_end is not None:
        ref_date = event.quarter_end
    drift = _drift_20d(session, event.stock_id, ref_date) if ref_date else None
    q = _parse_quarter(event.fiscal_period)
    if q is None:
        q_sin, q_cos = None, None
    else:
        angle = 2 * math.pi * (q - 1) / 4
        q_sin = round(math.sin(angle), 6)
        q_cos = round(math.cos(angle), 6)
    return {
        "yoy_revenue_growth": _f(event.yoy_revenue_growth),
        "yoy_pat_growth": _f(event.yoy_pat_growth),
        "qoq_revenue_growth": _f(event.qoq_revenue_growth),
        "qoq_pat_growth": _f(event.qoq_pat_growth),
        "drift_20d": drift,
        "fiscal_q_sin": q_sin,
        "fiscal_q_cos": q_cos,
    }


def _f(v) -> float | None:
    return None if v is None else float(v)


def _reaction_dict(rx: EarningsReaction | None) -> dict[str, float | None] | None:
    if rx is None:
        return None
    return {
        "gap_open_pct": _f(rx.gap_open_pct),
        "day1_close_pct": _f(rx.day1_close_pct),
        "day3_close_pct": _f(rx.day3_close_pct),
        "day5_close_pct": _f(rx.day5_close_pct),
        "detection_confidence": _f(rx.detection_confidence),
    }


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / max(len(values) - 1, 1)
    std = math.sqrt(var)
    return m, std or 1.0  # never divide by zero downstream


def _standardize(
    vec: dict[str, float | None],
    means: dict[str, float],
    stds: dict[str, float],
) -> list[float | None]:
    return [
        None if vec[k] is None else (vec[k] - means[k]) / stds[k]
        for k in FEATURE_KEYS
    ]


def _cosine(a: list[float | None], b: list[float | None]) -> float | None:
    """Cosine similarity treating None as missing (dropped from both sides)."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    dot = sum(x * y for x, y in pairs)
    na = math.sqrt(sum(x * x for x, _ in pairs))
    nb = math.sqrt(sum(y * y for _, y in pairs))
    if na == 0 or nb == 0:
        return None
    return round(dot / (na * nb), 4)


def find_similar_setups(
    session: Session,
    stock_id: int,
    *,
    anchor_event_id: int | None = None,
    k: int = 5,
) -> PatternResult:
    events_and_reactions = session.execute(
        select(EarningsEvent, EarningsReaction)
        .outerjoin(EarningsReaction, EarningsReaction.earnings_event_id == EarningsEvent.id)
        .where(EarningsEvent.stock_id == stock_id)
        .order_by(desc(EarningsEvent.quarter_end))
    ).all()

    if not events_and_reactions:
        return PatternResult(
            stock_id=stock_id,
            anchor_event_id=None,
            anchor_features={k: None for k in FEATURE_KEYS},
            feature_means={},
            feature_stds={},
            matches=[],
        )

    # Choose anchor
    anchor = None
    if anchor_event_id is not None:
        for ev, rx in events_and_reactions:
            if ev.id == anchor_event_id:
                anchor = (ev, rx)
                break
    if anchor is None:
        # First event (by quarter_end desc) that has an announcement_date
        for ev, rx in events_and_reactions:
            if ev.announcement_date is not None:
                anchor = (ev, rx)
                break

    if anchor is None:
        return PatternResult(
            stock_id=stock_id,
            anchor_event_id=None,
            anchor_features={k: None for k in FEATURE_KEYS},
            feature_means={},
            feature_stds={},
            matches=[],
        )

    anchor_ev, _anchor_rx = anchor

    # Feature vectors for every event
    vectors: list[tuple[EarningsEvent, EarningsReaction | None, dict[str, float | None]]] = []
    for ev, rx in events_and_reactions:
        vectors.append((ev, rx, _feature_vector(session, ev)))

    # Compute means / stds only from candidate events (exclude anchor itself).
    # NB: loop-variable names avoid shadowing the outer `k` (top-K count) —
    # Python leaks for-loop vars into the enclosing scope.
    per_feature: dict[str, list[float]] = {key: [] for key in FEATURE_KEYS}
    for ev, _rx, vec in vectors:
        if ev.id == anchor_ev.id:
            continue
        for feat_name, feat_val in vec.items():
            if feat_val is not None:
                per_feature[feat_name].append(feat_val)
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for feat_name, vals in per_feature.items():
        m, s = _mean_std(vals)
        means[feat_name] = round(m, 4)
        stds[feat_name] = round(s, 4)

    # Standardize + rank
    anchor_vec = next(v for ev, _rx, v in vectors if ev.id == anchor_ev.id)
    anchor_std = _standardize(anchor_vec, means, stds)

    scored: list[tuple[float, EarningsEvent, EarningsReaction | None, dict[str, float | None]]] = []
    for ev, rx, vec in vectors:
        if ev.id == anchor_ev.id:
            continue
        sim = _cosine(anchor_std, _standardize(vec, means, stds))
        if sim is None or rx is None:
            continue
        scored.append((sim, ev, rx, vec))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:k]

    matches = [
        MatchedEvent(
            event_id=ev.id,
            fiscal_period=ev.fiscal_period,
            announcement_date=ev.announcement_date.isoformat()
            if ev.announcement_date
            else None,
            similarity=sim,
            features=vec,
            reaction=_reaction_dict(rx),
        )
        for sim, ev, rx, vec in top
    ]

    return PatternResult(
        stock_id=stock_id,
        anchor_event_id=anchor_ev.id,
        anchor_features=anchor_vec,
        feature_means=means,
        feature_stds=stds,
        matches=matches,
    )
