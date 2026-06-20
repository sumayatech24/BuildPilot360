"""Audit logging helper (NFR-005). Reusable service, not one-off logic."""
from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session

from app.models import AuditLog


def record_audit(
    session: Session,
    *,
    action: str,
    entity: str,
    entity_id: str | None = None,
    tenant_id: str | None = None,
    actor_id: str | None = None,
    before: Any | None = None,
    after: Any | None = None,
) -> AuditLog:
    log = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before_json=json.dumps(before, default=str) if before is not None else None,
        after_json=json.dumps(after, default=str) if after is not None else None,
    )
    session.add(log)
    return log
