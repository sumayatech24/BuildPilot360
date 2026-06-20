"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    id: str
    tenant_id: str
    email: str
    full_name: str
    roles: list[str] = []
    permissions: list[str] = []


# --- Projects ---
class ProjectCreate(BaseModel):
    name: str
    code: str
    description: str | None = None


class ProjectRead(BaseModel):
    id: str
    name: str
    code: str
    description: str | None = None
    status: str
    repo_url: str | None = None
    tech_stack: str | None = None
    default_branch: str = "main"
    created_at: datetime


# --- Requirements ---
class RequirementCreate(BaseModel):
    project_id: str
    title: str
    raw_text: str
    source: str = "text"
    priority: str = "P2"


class RequirementRead(BaseModel):
    id: str
    project_id: str
    title: str
    raw_text: str
    source: str
    status: str
    priority: str
    created_at: datetime


class AnalysisRead(BaseModel):
    id: str
    requirement_id: str
    summary: str
    classification: str
    confidence: float
    gaps: list[str]
    questions: list[str]
    nfrs: list[str]
    acceptance_criteria: list[str]
    suggested_stories: list[dict]
    provider: str
    model: str | None
    tokens_used: int


# --- Stories ---
class StoryRead(BaseModel):
    id: str
    project_id: str
    requirement_id: str | None
    title: str
    persona: str | None
    story_text: str | None
    acceptance_criteria: list[str]
    priority: str
    status_code: str
    rank: int = 0
    mvp: bool = False
    priority_score: float = 0.0
    priority_rationale: str | None = None
    created_at: datetime


# --- Integrations / providers ---
class ProviderCreate(BaseModel):
    provider: str = Field(..., description="anthropic | openai | github | aws | azure | gcp")
    label: str
    secret: str = Field(..., description="API key / token (stored encrypted)")
    config: dict = {}
    is_active: bool = True


class ProviderRead(BaseModel):
    id: str
    provider: str
    label: str
    masked_secret: str
    config: dict
    is_active: bool
    created_at: datetime


# --- Projects (extended) ---
class ProjectCreateFull(BaseModel):
    name: str
    code: str
    description: str | None = None
    repo_url: str | None = None
    tech_stack: str | None = None
    default_branch: str = "main"


# --- Generation runs ---
class GenerateRequest(BaseModel):
    story_ids: list[str]


class RunRead(BaseModel):
    id: str
    project_id: str
    story_id: str | None
    kind: str
    provider: str
    model: str | None
    status: str
    input_tokens: int
    output_tokens: int
    branch: str | None
    pr_url: str | None
    files: list[dict]
    rationale: str | None
    log: str | None
    created_at: datetime


class UsageRead(BaseModel):
    period: str
    input_tokens: int
    output_tokens: int
    calls: int
    monthly_budget: int


class StoryStatusUpdate(BaseModel):
    status_code: str = Field(..., description="Target lifecycle status code")


class GenerateBacklogResponse(BaseModel):
    requirement_id: str
    created_story_ids: list[str]


class LifecycleStageRead(BaseModel):
    stage_no: int
    stage_name: str
    status_code: str
    primary_owner: str
    verifier: str
    exit_criteria: str
