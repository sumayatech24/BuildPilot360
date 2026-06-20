"""AI code + test generation runs (M10). Background execution + polling."""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.core.audit import record_audit
from app.core.db import get_session
from app.core.deps import require_permission
from app.models import GenerationRun, Story
from app.schemas import CurrentUser, GenerateRequest, RunRead
from app.services import pipeline

router = APIRouter(prefix="/api/v1", tags=["generation"])


def _to_read(r: GenerationRun) -> RunRead:
    return RunRead(
        id=r.id, project_id=r.project_id, story_id=r.story_id, kind=r.kind,
        provider=r.provider, model=r.model, status=r.status,
        input_tokens=r.input_tokens, output_tokens=r.output_tokens,
        branch=r.branch, pr_url=r.pr_url, files=json.loads(r.files_json or "[]"),
        rationale=r.rationale, log=r.log, created_at=r.created_at,
    )


@router.post("/projects/{project_id}/generate", response_model=list[RunRead], status_code=201)
def generate(project_id: str, body: GenerateRequest, background: BackgroundTasks,
             session: Session = Depends(get_session),
             current: CurrentUser = Depends(require_permission("code.generate"))):
    if not body.story_ids:
        raise HTTPException(400, "Provide at least one story_id")
    runs: list[GenerationRun] = []
    for sid in body.story_ids:
        story = session.get(Story, sid)
        if not story or story.tenant_id != current.tenant_id or story.project_id != project_id:
            continue
        run = GenerationRun(
            tenant_id=current.tenant_id, project_id=project_id, story_id=sid,
            kind="code", status="queued", created_by=current.id, updated_by=current.id,
        )
        session.add(run)
        session.flush()
        runs.append(run)
    record_audit(session, action="code.generation.queued", entity="project",
                 entity_id=project_id, tenant_id=current.tenant_id, actor_id=current.id,
                 after={"runs": len(runs)})
    session.commit()
    for run in runs:
        session.refresh(run)
        background.add_task(pipeline.execute_generation_run, run.id)
    return [_to_read(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(run_id: str, session: Session = Depends(get_session),
            current: CurrentUser = Depends(require_permission("story.read"))):
    run = session.get(GenerationRun, run_id)
    if not run or run.tenant_id != current.tenant_id:
        raise HTTPException(404, "Run not found")
    return _to_read(run)


@router.get("/runs", response_model=list[RunRead])
def list_runs(project_id: str | None = None, session: Session = Depends(get_session),
              current: CurrentUser = Depends(require_permission("story.read"))):
    stmt = select(GenerationRun).where(GenerationRun.tenant_id == current.tenant_id)
    if project_id:
        stmt = stmt.where(GenerationRun.project_id == project_id)
    runs = sorted(session.exec(stmt).all(), key=lambda r: r.created_at, reverse=True)
    return [_to_read(r) for r in runs]
