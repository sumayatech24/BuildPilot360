"""AI / manual MVP prioritization (M04)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.ai import llm
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.deps import require_permission
from app.models import Story
from app.schemas import CurrentUser
from app.services import pipeline

router = APIRouter(prefix="/api/v1/projects", tags=["prioritization"])


class ManualRank(BaseModel):
    story_id: str
    rank: int
    mvp: bool = False
    priority: str | None = None


@router.post("/{project_id}/prioritize")
def prioritize(project_id: str, mode: str = "ai",
               session: Session = Depends(get_session),
               current: CurrentUser = Depends(require_permission("story.update"))):
    if mode != "ai":
        raise HTTPException(400, "Use POST /prioritize?mode=ai or PATCH /prioritize/manual")
    try:
        ordered = pipeline.prioritize_stories(session, current.tenant_id, project_id)
    except llm.BudgetExceeded as e:
        raise HTTPException(429, str(e))
    record_audit(session, action="stories.prioritized.ai", entity="project",
                 entity_id=project_id, tenant_id=current.tenant_id, actor_id=current.id,
                 after={"count": len(ordered)})
    session.commit()
    return {"project_id": project_id, "mode": "ai",
            "ranked": [{"id": s.id, "rank": s.rank, "mvp": s.mvp,
                        "score": s.priority_score, "rationale": s.priority_rationale,
                        "title": s.title} for s in ordered]}


@router.patch("/{project_id}/prioritize/manual")
def prioritize_manual(project_id: str, items: list[ManualRank],
                      session: Session = Depends(get_session),
                      current: CurrentUser = Depends(require_permission("story.update"))):
    updated = 0
    for item in items:
        story = session.get(Story, item.story_id)
        if not story or story.tenant_id != current.tenant_id or story.project_id != project_id:
            continue
        story.rank = item.rank
        story.mvp = item.mvp
        if item.priority:
            story.priority = item.priority
        story.priority_rationale = "Set manually"
        story.updated_by = current.id
        session.add(story)
        updated += 1
    record_audit(session, action="stories.prioritized.manual", entity="project",
                 entity_id=project_id, tenant_id=current.tenant_id, actor_id=current.id,
                 after={"updated": updated})
    session.commit()
    return {"project_id": project_id, "mode": "manual", "updated": updated}
