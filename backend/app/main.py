from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import earnings, market, stocks

app = FastAPI(
    title="earnings-edge",
    version="0.1.0",
    description="Indian equity earnings analytics — base rates, positioning, patterns.",
)

# Permissive CORS for local Next.js dev. Tighten in prod when we have a real domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(stocks.router, prefix=API_PREFIX)
app.include_router(earnings.router, prefix=API_PREFIX)
app.include_router(market.router, prefix=API_PREFIX)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
