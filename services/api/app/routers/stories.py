"""Backlog stories + lifecycle transitions (M05/M06, Story Lifecycle Workflow)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.audit import record_audit
from app.core.db import get_session
from app.core.deps import require_permission
from app.models import LifecycleStage, Story
from app.schemas import CurrentUser, LifecycleStageRead, StoryRead, StoryStatusUpdate

router = APIRouter(prefix="/api/v1/stories", tags=["stories"])


def _to_read(s: Story) -> StoryRead:
    return StoryRead(
        id=s.id,
        project_id=s.project_id,
        requirement_id=s.requirement_id,
        title=s.title,
        persona=s.persona,
        story_text=s.story_text,
        acceptance_criteria=json.loads(s.acceptance_criteria_json or "[]"),
        priority=s.priority,
        status_code=s.status_code,
        rank=s.rank,
        mvp=s.mvp,
        priority_score=s.priority_score,
        priority_rationale=s.priority_rationale,
        created_at=s.created_at,
    )


@router.get("", response_model=list[StoryRead])
def list_stories(
    project_id: str | None = None,
    status_code: str | None = None,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("story.read")),
) -> list[StoryRead]:
    stmt = select(Story).where(
        Story.tenant_id == current.tenant_id, Story.is_deleted == False  # noqa: E712
    )
    if project_id:
        stmt = stmt.where(Story.project_id == project_id)
    if status_code:
        stmt = stmt.where(Story.status_code == status_code)
    return [_to_read(s) for s in session.exec(stmt).all()]


@router.get("/lifecycle", response_model=list[LifecycleStageRead])
def lifecycle(session: Session = Depends(get_session),
              current: CurrentUser = Depends(require_permission("story.read"))) -> list[LifecycleStage]:
    return session.exec(select(LifecycleStage).order_by(LifecycleStage.stage_no)).all()


@router.patch("/{story_id}/status", response_model=StoryRead)
def update_status(
    story_id: str,
    body: StoryStatusUpdate,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("story.update")),
) -> StoryRead:
    story = session.get(Story, story_id)
    if not story or story.is_deleted or story.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Story not found")

    stage = session.exec(
        select(LifecycleStage).where(LifecycleStage.status_code == body.status_code)
    ).first()
    if not stage:
        raise HTTPException(status_code=400, detail=f"Unknown status code: {body.status_code}")

    before = story.status_code
    story.status_code = body.status_code
    story.updated_by = current.id
    story.version += 1
    session.add(story)
    record_audit(session, action=stage.audit_event, entity="story", entity_id=story.id,
                 tenant_id=current.tenant_id, actor_id=current.id,
                 before={"status_code": before}, after={"status_code": body.status_code})
    session.commit()
    session.refresh(story)
    return _to_read(story)
