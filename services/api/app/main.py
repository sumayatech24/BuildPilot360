"""BuildPilot360 API entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import settings
from app.core.db import init_db
from app.routers import auth, catalog, modules, projects, requirements, stories


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_on_start:
        # Idempotent: safe on every boot. Populates roles, lifecycle, blueprint catalog + owner.
        try:
            from app.seed import seed
            seed()
        except Exception as exc:  # noqa: BLE001 - never block startup on seed
            print(f"[startup] seed skipped: {exc}")
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="AI SDLC Delivery Platform — requirement intake, AI analysis, backlog, lifecycle.",
    lifespan=lifespan,
)

# Auth uses Bearer tokens (not cookies), so wildcard CORS is safe — and it keeps a hosted
# deploy working no matter what URL the web app is served from. Credentials are only enabled
# when an explicit origin allowlist is configured.
_origins = settings.cors_origin_list
_wildcard = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _wildcard else _origins,
    allow_origin_regex=None if _wildcard else r"^app://.*$",
    allow_credentials=not _wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(requirements.router)
app.include_router(stories.router)
app.include_router(catalog.router)
app.include_router(modules.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": settings.app_name, "version": __version__, "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "healthy"}
