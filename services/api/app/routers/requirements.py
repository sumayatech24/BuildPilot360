"""Requirement intake + AI analysis + backlog generation (M02/M03/M05)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.ai.provider import get_provider
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.deps import require_permission
from app.models import Requirement, RequirementAnalysis, Story
from app.schemas import (
    AnalysisRead,
    CurrentUser,
    GenerateBacklogResponse,
    RequirementCreate,
    RequirementRead,
)

router = APIRouter(prefix="/api/v1/requirements", tags=["requirements"])


def _owned(session: Session, req_id: str, tenant_id: str) -> Requirement:
    req = session.get(Requirement, req_id)
    if not req or req.is_deleted or req.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.get("", response_model=list[RequirementRead])
def list_requirements(
    project_id: str | None = None,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("requirement.read")),
) -> list[Requirement]:
    stmt = select(Requirement).where(
        Requirement.tenant_id == current.tenant_id, Requirement.is_deleted == False  # noqa: E712
    )
    if project_id:
        stmt = stmt.where(Requirement.project_id == project_id)
    return session.exec(stmt).all()


@router.post("", response_model=RequirementRead, status_code=201)
def create_requirement(
    body: RequirementCreate,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("requirement.create")),
) -> Requirement:
    req = Requirement(
        tenant_id=current.tenant_id,
        project_id=body.project_id,
        title=body.title,
        raw_text=body.raw_text,
        source=body.source,
        priority=body.priority,
        created_by=current.id,
        updated_by=current.id,
    )
    session.add(req)
    session.flush()
    record_audit(session, action="requirement.create", entity="requirement", entity_id=req.id,
                 tenant_id=current.tenant_id, actor_id=current.id, after=body.model_dump())
    session.commit()
    session.refresh(req)
    return req


@router.post("/{req_id}/analyze", response_model=AnalysisRead)
def analyze_requirement(
    req_id: str,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("requirement.analyze")),
) -> AnalysisRead:
    req = _owned(session, req_id, current.tenant_id)
    provider = get_provider()
    result = provider.analyze(req.title, req.raw_text)

    analysis = RequirementAnalysis(
        tenant_id=current.tenant_id,
        requirement_id=req.id,
        summary=result.summary,
        classification=result.classification,
        confidence=result.confidence,
        gaps_json=json.dumps(result.gaps),
        questions_json=json.dumps(result.questions),
        nfr_json=json.dumps(result.nfrs),
        acceptance_criteria_json=json.dumps(result.acceptance_criteria),
        suggested_stories_json=json.dumps(result.suggested_stories),
        provider=result.provider,
        model=result.model,
        tokens_used=result.tokens_used,
        created_by=current.id,
        updated_by=current.id,
    )
    req.status = "analyzed"
    session.add(analysis)
    session.add(req)
    session.flush()
    record_audit(session, action="requirement.analyzed", entity="requirement", entity_id=req.id,
                 tenant_id=current.tenant_id, actor_id=current.id,
                 after={"provider": result.provider, "confidence": result.confidence})
    session.commit()
    session.refresh(analysis)
    return _analysis_to_read(analysis)


@router.get("/{req_id}/analysis", response_model=AnalysisRead)
def get_analysis(
    req_id: str,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("requirement.read")),
) -> AnalysisRead:
    _owned(session, req_id, current.tenant_id)
    analysis = session.exec(
        select(RequirementAnalysis)
        .where(RequirementAnalysis.requirement_id == req_id)
        .order_by(RequirementAnalysis.created_at.desc())
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis yet; run /analyze first")
    return _analysis_to_read(analysis)


@router.post("/{req_id}/generate-backlog", response_model=GenerateBacklogResponse, status_code=201)
def generate_backlog(
    req_id: str,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("story.create")),
) -> GenerateBacklogResponse:
    req = _owned(session, req_id, current.tenant_id)
    analysis = session.exec(
        select(RequirementAnalysis)
        .where(RequirementAnalysis.requirement_id == req_id)
        .order_by(RequirementAnalysis.created_at.desc())
    ).first()
    if not analysis:
        raise HTTPException(status_code=400, detail="Analyze the requirement before generating backlog")

    suggested = json.loads(analysis.suggested_stories_json)
    acceptance = analysis.acceptance_criteria_json
    created_ids: list[str] = []
    for s in suggested:
        story = Story(
            tenant_id=current.tenant_id,
            project_id=req.project_id,
            requirement_id=req.id,
            title=s.get("title", req.title),
            persona=s.get("persona"),
            story_text=(
                f"As a {s.get('persona', 'user')}, I want to {s.get('capability', 'manage')} "
                f"in {req.title}, so that delivery is governed and traceable."
            ),
            acceptance_criteria_json=acceptance,
            priority=req.priority,
            status_code="STORY_DRAFT",
            created_by=current.id,
            updated_by=current.id,
        )
        session.add(story)
        session.flush()
        created_ids.append(story.id)

    req.status = "approved"
    session.add(req)
    record_audit(session, action="backlog.generated", entity="requirement", entity_id=req.id,
                 tenant_id=current.tenant_id, actor_id=current.id,
                 after={"stories": len(created_ids)})
    session.commit()
    return GenerateBacklogResponse(requirement_id=req.id, created_story_ids=created_ids)


def _analysis_to_read(a: RequirementAnalysis) -> AnalysisRead:
    return AnalysisRead(
        id=a.id,
        requirement_id=a.requirement_id,
        summary=a.summary,
        classification=a.classification,
        confidence=a.confidence,
        gaps=json.loads(a.gaps_json),
        questions=json.loads(a.questions_json),
        nfrs=json.loads(a.nfr_json),
        acceptance_criteria=json.loads(a.acceptance_criteria_json),
        suggested_stories=json.loads(a.suggested_stories_json),
        provider=a.provider,
        model=a.model,
        tokens_used=a.tokens_used,
    )
