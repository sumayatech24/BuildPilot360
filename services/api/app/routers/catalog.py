"""Read-only access to the full blueprint catalog (every workbook sheet as data)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, func, select

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import CatalogItem
from app.schemas import CurrentUser

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


def _row(c: CatalogItem) -> dict:
    return {
        "id": c.id, "category": c.category, "item_id": c.item_id, "module_id": c.module_id,
        "title": c.title, "domain": c.domain, "phase": c.phase, "priority": c.priority,
        "status": c.status, "data": json.loads(c.data_json or "{}"),
    }


@router.get("/summary")
def summary(session: Session = Depends(get_session),
            _: CurrentUser = Depends(get_current_user)) -> dict:
    rows = session.exec(
        select(CatalogItem.category, func.count()).group_by(CatalogItem.category)
    ).all()
    counts = {cat: n for cat, n in rows}
    return {
        "counts": counts,
        "totals": {
            "modules": counts.get("module", 0),
            "features": counts.get("feature", 0),
            "user_stories": counts.get("user_story", 0),
            "nfrs": counts.get("nfr", 0),
            "api_integrations": counts.get("api_integration", 0),
            "screens": counts.get("screen", 0),
        },
    }


@router.get("/{category}")
def list_category(
    category: str,
    module_id: str | None = None,
    phase: str | None = None,
    priority: str | None = None,
    domain: str | None = None,
    q: str | None = Query(default=None, description="Title contains"),
    limit: int = Query(default=200, le=2000),
    offset: int = 0,
    session: Session = Depends(get_session),
    _: CurrentUser = Depends(get_current_user),
) -> dict:
    stmt = select(CatalogItem).where(CatalogItem.category == category)
    if module_id:
        stmt = stmt.where(CatalogItem.module_id == module_id)
    if phase:
        stmt = stmt.where(CatalogItem.phase == phase)
    if priority:
        stmt = stmt.where(CatalogItem.priority == priority)
    if domain:
        stmt = stmt.where(CatalogItem.domain == domain)
    if q:
        stmt = stmt.where(CatalogItem.title.contains(q))  # type: ignore[attr-defined]

    total = len(session.exec(stmt).all())
    page = session.exec(stmt.offset(offset).limit(limit)).all()
    return {"category": category, "total": total, "limit": limit, "offset": offset,
            "items": [_row(c) for c in page]}
