from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


# Neon drops idle server-side backends (idle-in-transaction / autosuspend). Without
# TCP keepalives a client read can then block forever on the dead socket — which hung
# a long compute_reactions run mid-query. pool_pre_ping only checks liveness at
# checkout, so it doesn't help a connection that dies mid-statement. Add libpq
# keepalives (break a dead socket in ~30s + 5×10s), a connect timeout, a server-side
# statement_timeout as a backstop, and recycle connections older than 5 min so we never
# reuse one Neon has already reaped.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "options": "-c statement_timeout=120000",
    },
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
