from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://earnings:earnings@localhost:5432/earnings_edge"

    ingest_cache_dir: Path = Path("backend/ingest/cache")
    ingest_user_agent: str = "Mozilla/5.0 (Macintosh; earnings-edge research)"


settings = Settings()
