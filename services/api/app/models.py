"""SQLModel ORM models for BuildPilot360.

Every business table is tenant-scoped and carries audit fields. Master/config values
(roles, permissions, lifecycle stages, statuses) live in tables — not hardcoded in logic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuditMixin(SQLModel):
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    created_by: str | None = Field(default=None, index=True)
    updated_by: str | None = Field(default=None)
    version: int = Field(default=1)
    is_deleted: bool = Field(default=False, index=True)


# ---------------------------------------------------------------------------
# Core platform (M01)
# ---------------------------------------------------------------------------
class Tenant(AuditMixin, table=True):
    __tablename__ = "tenants"
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    plan: str = Field(default="trial")
    status: str = Field(default="active")


class User(AuditMixin, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    email: str = Field(index=True)
    full_name: str
    hashed_password: str
    status: str = Field(default="active")


class Role(AuditMixin, table=True):
    __tablename__ = "roles"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str
    scope: str = Field(default="tenant")
    description: str | None = None


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"
    id: str = Field(default_factory=_uuid, primary_key=True)
    code: str = Field(index=True, unique=True)
    module: str
    action: str
    description: str | None = None


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"
    role_id: str = Field(foreign_key="roles.id", primary_key=True)
    permission_code: str = Field(foreign_key="permissions.code", primary_key=True)


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    role_id: str = Field(foreign_key="roles.id", primary_key=True)


class Project(AuditMixin, table=True):
    __tablename__ = "projects"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str
    code: str = Field(index=True)
    description: str | None = None
    status: str = Field(default="active")


# ---------------------------------------------------------------------------
# Requirement intake & AI analysis (M02 / M03)
# ---------------------------------------------------------------------------
class Requirement(AuditMixin, table=True):
    __tablename__ = "requirements"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    project_id: str = Field(index=True, foreign_key="projects.id")
    title: str
    raw_text: str
    source: str = Field(default="text")  # text | file | voice | url | import
    status: str = Field(default="captured")  # captured | analyzed | approved | rejected
    priority: str = Field(default="P2")


class RequirementAnalysis(AuditMixin, table=True):
    __tablename__ = "requirement_analyses"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    requirement_id: str = Field(index=True, foreign_key="requirements.id")
    summary: str
    classification: str
    confidence: float = Field(default=0.0)
    gaps_json: str = Field(default="[]")
    questions_json: str = Field(default="[]")
    nfr_json: str = Field(default="[]")
    acceptance_criteria_json: str = Field(default="[]")
    suggested_stories_json: str = Field(default="[]")
    provider: str = Field(default="stub")
    model: str | None = None
    tokens_used: int = Field(default=0)


# ---------------------------------------------------------------------------
# Backlog (M05)
# ---------------------------------------------------------------------------
class Epic(AuditMixin, table=True):
    __tablename__ = "epics"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    project_id: str = Field(index=True, foreign_key="projects.id")
    title: str
    description: str | None = None
    status: str = Field(default="open")


class Story(AuditMixin, table=True):
    __tablename__ = "stories"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    project_id: str = Field(index=True, foreign_key="projects.id")
    requirement_id: str | None = Field(default=None, index=True, foreign_key="requirements.id")
    epic_id: str | None = Field(default=None, foreign_key="epics.id")
    title: str
    persona: str | None = None
    story_text: str | None = None
    acceptance_criteria_json: str = Field(default="[]")
    priority: str = Field(default="P2")
    estimate: int | None = None
    # lifecycle status code from the Story Lifecycle Workflow (config table below)
    status_code: str = Field(default="STORY_DRAFT", index=True)


# ---------------------------------------------------------------------------
# Config / master data (M06 / M23) — drives lifecycle without hardcoding
# ---------------------------------------------------------------------------
class LifecycleStage(SQLModel, table=True):
    __tablename__ = "lifecycle_stages"
    id: str = Field(default_factory=_uuid, primary_key=True)
    stage_no: int = Field(index=True)
    stage_name: str
    status_code: str = Field(index=True, unique=True)
    primary_owner: str
    verifier: str
    ai_automation: str
    manual_verification: str
    exit_criteria: str
    audit_event: str


# ---------------------------------------------------------------------------
# Audit (M21) — append-only trail
# ---------------------------------------------------------------------------
class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    id: str = Field(default_factory=_uuid, primary_key=True)
    tenant_id: str | None = Field(default=None, index=True)
    actor_id: str | None = Field(default=None, index=True)
    action: str = Field(index=True)
    entity: str = Field(index=True)
    entity_id: str | None = None
    before_json: str | None = None
    after_json: str | None = None
    created_at: datetime = Field(default_factory=_now)
