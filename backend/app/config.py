from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The backend root — anchor for on-disk paths so `cd backend && …` and running
# from the repo root both resolve to the SAME cache directory.
BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://earnings:earnings@localhost:5432/earnings_edge"

    ingest_cache_dir: Path = BACKEND_ROOT / "ingest" / "cache"
    ingest_user_agent: str = "Mozilla/5.0 (Macintosh; earnings-edge research)"

    # Comma-separated list of allowed CORS origins. Overridable per-env so we can
    # whitelist a new frontend URL without a code change.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Regex fallback so Vercel preview deployments (per-branch subdomains) work
    # without an env change on every PR.
    cors_origin_regex: str = r"https://.*\.vercel\.app"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Accept raw Neon/Postgres URLs and coerce to the SQLAlchemy psycopg3 driver spec.
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://") :]
        if v.startswith("postgresql://") and "+" not in v.split("://", 1)[0]:
            return "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @field_validator("ingest_cache_dir")
    @classmethod
    def _resolve_cache_dir(cls, v: Path) -> Path:
        # Always resolve relative to backend/ so the path is stable regardless of cwd.
        return v if v.is_absolute() else (BACKEND_ROOT / v).resolve()


settings = Settings()
