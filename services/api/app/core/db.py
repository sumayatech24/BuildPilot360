"""Database engine and session management."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


def _normalize(url: str) -> str:
    """Managed Postgres providers hand out 'postgresql://…'. Pin the psycopg v3 driver
    so SQLAlchemy uses the installed binary instead of the absent psycopg2."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize(settings.database_url)
IS_POSTGRES = DATABASE_URL.startswith("postgresql")
# Isolate all tables in a dedicated schema when set (e.g. on a shared managed database),
# so BuildPilot360 never touches another app's tables.
DB_SCHEMA = settings.db_schema.strip()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, connect_args=connect_args)

if IS_POSTGRES and DB_SCHEMA:
    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_conn, _record):  # noqa: ANN001
        # Restrict to the dedicated schema ONLY — never include public — so table-existence
        # checks and FK resolution can't pick up another app's tables on a shared database.
        with dbapi_conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{DB_SCHEMA}"')


def init_db() -> None:
    """Create the schema (if isolated) and all tables. Importing models registers them."""
    from app import models  # noqa: F401

    if IS_POSTGRES and DB_SCHEMA:
        with engine.begin() as conn:
            if settings.reset_schema:
                # Guarded: only ever drops our own dedicated schema, never public.
                conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{DB_SCHEMA}" CASCADE')
            conn.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
