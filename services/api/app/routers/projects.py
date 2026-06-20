"""Project endpoints (tenant-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.audit import record_audit
from app.core.db import get_session
from app.core.deps import require_permission
from app.models import Project
from app.schemas import CurrentUser, ProjectCreateFull, ProjectRead

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("project.read")),
) -> list[Project]:
    return session.exec(
        select(Project).where(
            Project.tenant_id == current.tenant_id, Project.is_deleted == False  # noqa: E712
        )
    ).all()


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    body: ProjectCreateFull,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("project.create")),
) -> Project:
    project = Project(
        tenant_id=current.tenant_id,
        name=body.name,
        code=body.code,
        description=body.description,
        repo_url=body.repo_url,
        tech_stack=body.tech_stack,
        default_branch=body.default_branch,
        created_by=current.id,
        updated_by=current.id,
    )
    session.add(project)
    session.flush()
    record_audit(session, action="project.create", entity="project", entity_id=project.id,
                 tenant_id=current.tenant_id, actor_id=current.id, after=body.model_dump())
    session.commit()
    session.refresh(project)
    return project
