"""BuildPilot360 API entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import settings
from app.core.db import init_db
from app.routers import auth, projects, requirements, stories


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="AI SDLC Delivery Platform — requirement intake, AI analysis, backlog, lifecycle.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"^app://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(requirements.router)
app.include_router(stories.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": settings.app_name, "version": __version__, "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "healthy"}
