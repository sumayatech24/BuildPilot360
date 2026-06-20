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
# schema_translate_map makes SQLAlchemy emit fully schema-qualified names (buildpilot360.users)
# in the generated SQL. This is robust through transaction-mode connection poolers (pgbouncer,
# which Render's managed Postgres uses) where a session-level `SET search_path` issued at connect
# time does NOT reliably persist across transactions. No reliance on connection session state.
_exec_opts: dict = {}
if IS_POSTGRES and DB_SCHEMA:
    _exec_opts["schema_translate_map"] = {None: DB_SCHEMA}
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True,
                       connect_args=connect_args, execution_options=_exec_opts)

if IS_POSTGRES and DB_SCHEMA:
    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_conn, _record):  # noqa: ANN001
        # Belt-and-suspenders for raw SQL paths; primary isolation is schema_translate_map above.
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
    if IS_POSTGRES:
        _add_missing_columns()


def _add_missing_columns() -> None:
    """Lightweight additive migration: ALTER TABLE ADD COLUMN for any model columns missing
    from an existing table (Postgres). Only ever adds nullable columns — never drops or
    retypes — so deploying new fields onto a live database preserves data.
    """
    from sqlalchemy import inspect

    insp = inspect(engine)
    schema = DB_SCHEMA or None
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            try:
                existing = {c["name"] for c in insp.get_columns(table.name, schema=schema)}
            except Exception:  # noqa: BLE001 - table not present yet; create_all handles it
                continue
            qualified = f'"{schema}".{table.name}' if schema else table.name
            for col in table.columns:
                if col.name in existing:
                    continue
                coltype = col.type.compile(dialect=engine.dialect)
                conn.exec_driver_sql(
                    f'ALTER TABLE {qualified} ADD COLUMN IF NOT EXISTS "{col.name}" {coltype}'
                )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
