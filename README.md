# earnings-edge

Indian equity earnings analytics platform. Ingests NSE/BSE market microstructure data — bulk & block deals, FII/DII flows, delivery %, shareholding patterns, insider disclosures, and option-chain snapshots — to compute historical earnings-event base rates and surface unusual institutional positioning across the Nifty 500.

Not a prediction tool. A quantified playbook for stocks heading into (or coming out of) quarterly results.

## Status

Early build. Week 1 of a 12-week scope.

## Scope

- **Universe:** Nifty 500
- **History:** 10 years of daily OHLCV, delivery %, corporate events
- **Refresh:** nightly batch (~21:00 IST) after NSE end-of-day publish
- **Options:** nightly option-chain snapshots recorded from day 1 to build historical IV rank over time

## Data Sources

| Signal | Source |
|---|---|
| OHLCV, delivery %, bhavcopy | NSE (`jugaad-data` / `nsepython`) |
| Bulk & block deals | NSE / BSE daily CSV |
| FII/DII cash + F&O flows | NSE participant data |
| Quarterly earnings | Screener.in |
| Shareholding pattern | BSE corporate filings |
| Insider (SAST/PIT) | NSE / BSE disclosures |
| Option chain (snapshot) | NSE option chain endpoint |

## Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Alembic, Postgres 15
- **Ingest:** httpx, pandas, `jugaad-data`
- **Frontend:** Next.js 14, TypeScript, Tailwind, shadcn/ui, Recharts
- **Infra:** Docker Compose (local), GitHub Actions (nightly cron), Neon + Railway + Vercel (deploy)

## Layout

```
backend/    FastAPI app + Alembic migrations + nightly ingest jobs
frontend/   Next.js app
notebooks/  Exploration & case studies
```

## Disclaimer

Educational / research project. Not investment advice. No SEBI RA registration.
