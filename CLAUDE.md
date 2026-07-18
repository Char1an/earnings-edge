# earnings-edge — project spec for Claude Code

## What this is

An Indian equity **earnings analytics** platform for Nifty 500 stocks. Given a ticker, surface:
1. Historical earnings-event behavior (gap %, day1/3/5 returns, volume spikes, YoY/QoQ context)
2. Pre-earnings positioning signals (bulk/block deals, FII/DII flows, shareholding delta, insider trades, delivery %, option IV rank)
3. Pattern match to prior similar setups
4. Base-rate distributions (not predictions)

Framing: quantified base rates + positioning, **not** predictions. Never ship UI copy that claims to predict prices.

## Scope

- Universe: Nifty 500
- History: 10 years
- Refresh: nightly batch at ~21:00 IST (15:30 UTC) via GitHub Actions
- Options: snapshot nightly from day 1 — history builds over time
- No auth in v1; watchlist in localStorage

## Stack

- Python 3.11, FastAPI, SQLAlchemy, Alembic, Postgres 15
- httpx, pandas, `jugaad-data`, `nsepython`, `yfinance` (fallback)
- Next.js 14, TS, Tailwind, shadcn/ui, Recharts
- Docker Compose local; Neon + Railway + Vercel later

## Architecture (short)

```
NSE / BSE / Screener  ─▶  nightly ingest jobs  ─▶  Postgres
                                                       │
                              FastAPI (services layer) ┘
                                       │
                                    Next.js
```

Tables (core): `stocks`, `prices`, `earnings_events`, `earnings_reactions`, `deals`, `fii_dii_flows`, `shareholding`, `insider_trades`, `options_snapshots`, `iv_rank`, `upcoming_earnings`, `ingest_runs`.

## Non-negotiables

- All ingest jobs **idempotent** (safe to re-run same day)
- All ingest jobs **logged** to `ingest_runs`
- Cache raw HTTP responses to disk before parsing (so parse bugs don't force re-hitting NSE)
- Fail-soft nightly orchestrator (one broken source doesn't kill the rest)
- No mocked DB in tests — use a real Postgres test DB
- No emoji in code or commits unless the user asks

## Conventions

- Money in ₹ crore (`_cr` suffix) as `numeric`
- Percentages 0–100 (not 0–1)
- All timestamps UTC in DB; convert to IST only at UI layer
- Dates: `date` type for trading dates
- Snake_case for Python + SQL; camelCase for TS

## Analytics

Two functions carry the product:

- `compute_base_rates(stock_id, filters)` → n, mean, median, quartiles, histogram of `earnings_reactions`
- `find_similar_setups(stock_id, current_features, k=5)` → z-score standardize a feature vector then cosine similarity over the stock's own history

No ML for v1. Cosine similarity + windowed stats only.

## Compliance

- Personal / research use only
- No published buy/sell recommendations (would need SEBI RA)
- Disclaimer visible on every UI page
- Respect NSE rate limits: cache aggressively, backoff on 401/403

## Known caveats (deferred, not bugs)

- **Prices are NOT adjusted for splits / bonuses.** jugaad-data and yfinance
  (with `auto_adjust=False`) both return raw NSE prices. Any earnings event
  whose window straddles a split shows a false ±50%/±90% "reaction".
  Owed: `corporate_actions` table + adjustment pass over `prices` (planned
  post-week-8). Until then, treat reactions for stocks with recent splits
  (INFY, RELIANCE, WIPRO, TITAN, etc.) with skepticism.

## Build order

Week 1: repo + Docker + `stocks`/`prices` + 10y OHLCV backfill for Nifty 500.
Week 2: deals + FII/DII + delivery + nightly GH Actions.
Week 3: earnings scrape + `earnings_reactions` compute + first notebook.
Week 4: FastAPI endpoints for history + base rates.
Week 5: Next.js stock page — first demo.
Week 6: shareholding + insider ingest + positioning panel.
Week 7: options snapshot capture starts.
Week 8: pattern-matching service + panel.
Week 9: screener.
Week 10: home page + polish.
Week 11: notebook case study + deploy.
Week 12: buffer.
