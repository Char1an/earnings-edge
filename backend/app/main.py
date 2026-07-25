from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import earnings, home, market, patterns, positioning, screener, stocks

app = FastAPI(
    title="earnings-edge",
    version="0.1.0",
    description="Indian equity earnings analytics — base rates, positioning, patterns.",
)

# CORS origins are env-driven so prod (Vercel URL) can be whitelisted without a code change.
# `cors_origin_regex` covers Vercel preview subdomains automatically.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(stocks.router, prefix=API_PREFIX)
app.include_router(earnings.router, prefix=API_PREFIX)
app.include_router(positioning.router, prefix=API_PREFIX)
app.include_router(patterns.router, prefix=API_PREFIX)
app.include_router(screener.router, prefix=API_PREFIX)
app.include_router(home.router, prefix=API_PREFIX)
app.include_router(market.router, prefix=API_PREFIX)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
