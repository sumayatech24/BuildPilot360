"""Seed master/config data (NOT demo business data).

Creates: permission catalog, baseline roles, the 16-stage story lifecycle (from the
blueprint's Story Lifecycle Workflow), and a bootstrap tenant + owner user.
Idempotent — safe to re-run.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.catalog_loader import load_catalog
from app.core.config import settings
from app.core.db import engine, init_db
from app.core.security import hash_password
from app.models import (
    LifecycleStage,
    Permission,
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)

PERMISSIONS: list[tuple[str, str, str]] = [
    ("*", "ALL", "all"),
    ("project.read", "M01", "read"),
    ("project.create", "M01", "create"),
    ("requirement.read", "M02", "read"),
    ("requirement.create", "M02", "create"),
    ("requirement.analyze", "M03", "analyze"),
    ("story.read", "M05", "read"),
    ("story.create", "M05", "create"),
    ("story.update", "M05", "update"),
    # Generic module engine (applies to all 27 modules)
    ("module.read", "ALL", "read"),
    ("module.create", "ALL", "create"),
    ("module.update", "ALL", "update"),
    ("module.delete", "ALL", "delete"),
    ("module.bulk", "ALL", "bulk"),
    # AI orchestration (M10/M20)
    ("integration.manage", "M20", "manage"),
    ("story.generate", "M03", "generate"),
    ("code.generate", "M10", "generate"),
]

# Baseline roles -> permission codes ('*' = all). Roles/permissions are DB-driven (NFR-002).
ROLES: dict[str, list[str]] = {
    "Owner": ["*"],
    "Product Owner": [
        "project.read", "project.create", "requirement.read", "requirement.create",
        "requirement.analyze", "story.read", "story.create", "story.update",
        "module.read", "module.create", "module.update", "module.bulk",
        "integration.manage", "story.generate", "code.generate",
    ],
    "Developer": [
        "project.read", "requirement.read", "story.read", "story.update",
        "module.read", "module.create", "module.update",
    ],
    "QA Engineer": [
        "project.read", "requirement.read", "story.read", "story.update",
        "module.read", "module.update",
    ],
    "Viewer": ["project.read", "requirement.read", "story.read", "module.read"],
}

# 16-stage lifecycle: (no, name, status_code, owner, verifier, ai, manual, exit, audit_event)
LIFECYCLE: list[tuple] = [
    (1, "Intake", "STORY_DRAFT", "Product Owner", "Business Analyst", "Normalize requirement", "Yes", "Requirement captured, tenant/project assigned", "story.created"),
    (2, "AI Analysis", "AI_ANALYSIS_IN_PROGRESS", "AI Requirement Agent", "Product Owner", "Analyze scope/risk/NFR/AC", "Yes", "AI output passes schema + confidence threshold", "story.ai_analysis_started"),
    (3, "Clarification", "CLARIFICATION_REQUIRED", "Product Owner", "Business Stakeholder", "Generate clarification questions", "Yes", "All blocking questions answered", "story.clarification_requested"),
    (4, "Ready for Prioritization", "READY_FOR_PRIORITY", "Product Owner", "Delivery Manager", "Score MVP/phase/priority", "Yes", "Priority and phase approved", "story.prioritized"),
    (5, "Ready for Development", "READY_FOR_DEV", "Tech Lead", "Product Owner", "Generate implementation plan", "Yes", "Definition of Ready satisfied", "story.ready_for_dev"),
    (6, "Development Queued", "DEV_QUEUED", "Delivery Manager", "Tech Lead", "Create chunk plan + token budget", "Yes", "Developer assigned, chunks generated", "story.dev_queued"),
    (7, "AI Code Generation", "AI_CODING", "AI Dev Agent", "Developer", "Generate code chunk-by-chunk", "Yes", "Code compiles, no blocked errors", "story.ai_code_generated"),
    (8, "Developer Review", "DEV_REVIEW", "Developer", "Tech Lead", "Self-review, lint, unit tests", "Yes", "Ready for peer review", "story.dev_review_submitted"),
    (9, "Peer Review", "PEER_REVIEW", "Tech Lead", "Architect", "AI PR review + security hints", "Yes", "Reviewer approves or requests change", "story.peer_review_completed"),
    (10, "Automated QA", "AUTO_QA", "QA Agent", "QA Lead", "Generate/run unit/API/UI/BDD", "Yes", "Mandatory tests pass or defects raised", "story.auto_qa_completed"),
    (11, "Manual QA", "MANUAL_QA_OPTIONAL", "QA Engineer", "QA Lead", "Manual test checklist + evidence", "Configurable", "Manual QA pass or defects linked", "story.manual_qa_completed"),
    (12, "UAT Review", "UAT_REVIEW", "Product Owner", "Business Stakeholder", "Generate UAT script vs AC", "Yes", "UAT signoff received or rejected", "story.uat_signed_off"),
    (13, "Deployment Ready", "DEPLOYMENT_READY", "DevOps Engineer", "Release Manager", "Validate env/secrets/migrations", "Yes", "Release gate approved", "story.deployment_ready"),
    (14, "Deployment", "DEPLOYING", "DevOps Agent", "DevOps Engineer", "Run CI/CD to environment", "Yes", "Deployment + health checks pass", "story.deployed"),
    (15, "Post-Deployment Validation", "POST_DEPLOY_VALIDATION", "QA Engineer", "Release Manager", "Smoke + monitoring checks", "Yes", "No critical issues, no rollback", "story.post_deploy_validated"),
    (16, "Closure", "DONE", "Delivery Manager", "Product Owner", "Release note + traceability", "Yes", "Story closed with evidence", "story.closed"),
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        _seed_permissions(session)
        _seed_lifecycle(session)
        tenant = _seed_tenant(session)
        roles = _seed_roles(session, tenant.id)
        _seed_owner(session, tenant.id, roles["Owner"].id)
        counts = load_catalog(session, replace=True)
        session.commit()
    print("Seed complete.")
    if counts:
        print("  Catalog loaded:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"  Owner login: {settings.seed_owner_email} / {settings.seed_owner_password}")
    print("  Rotate this password immediately.")


def _seed_permissions(session: Session) -> None:
    for code, module, action in PERMISSIONS:
        if not session.exec(select(Permission).where(Permission.code == code)).first():
            session.add(Permission(code=code, module=module, action=action))
    session.flush()


def _seed_lifecycle(session: Session) -> None:
    for (no, name, code, owner, verifier, ai, manual, exit_c, event) in LIFECYCLE:
        if not session.exec(select(LifecycleStage).where(LifecycleStage.status_code == code)).first():
            session.add(LifecycleStage(
                stage_no=no, stage_name=name, status_code=code, primary_owner=owner,
                verifier=verifier, ai_automation=ai, manual_verification=manual,
                exit_criteria=exit_c, audit_event=event,
            ))
    session.flush()


def _seed_tenant(session: Session) -> Tenant:
    slug = settings.seed_tenant_name.lower().replace(" ", "-")
    tenant = session.exec(select(Tenant).where(Tenant.slug == slug)).first()
    if not tenant:
        tenant = Tenant(name=settings.seed_tenant_name, slug=slug, plan="enterprise")
        session.add(tenant)
        session.flush()
    return tenant


def _seed_roles(session: Session, tenant_id: str) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name, codes in ROLES.items():
        role = session.exec(
            select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
        ).first()
        if not role:
            role = Role(tenant_id=tenant_id, name=name)
            session.add(role)
            session.flush()
        existing = set(session.exec(
            select(RolePermission.permission_code).where(RolePermission.role_id == role.id)
        ).all())
        for code in codes:
            if code not in existing:
                session.add(RolePermission(role_id=role.id, permission_code=code))
        roles[name] = role
    session.flush()
    return roles


def _seed_owner(session: Session, tenant_id: str, owner_role_id: str) -> None:
    user = session.exec(select(User).where(User.email == settings.seed_owner_email)).first()
    if not user:
        user = User(
            tenant_id=tenant_id,
            email=settings.seed_owner_email,
            full_name="Platform Owner",
            hashed_password=hash_password(settings.seed_owner_password),
        )
        session.add(user)
        session.flush()
    if not session.exec(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == owner_role_id)
    ).first():
        session.add(UserRole(user_id=user.id, role_id=owner_role_id))
    session.flush()


if __name__ == "__main__":
    seed()
