"""Generic module engine: tenant-scoped CRUD/search/bulk/lifecycle for all 27 modules.

One endpoint family serves every module (M01..M27). The module_id is validated against the
blueprint catalog, so the surface is fully data-driven (Platform Principle). All writes are
RBAC-gated and audited.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.audit import record_audit
from app.core.db import get_session
from app.core.deps import require_permission
from app.models import CatalogItem, ModuleRecord
from app.schemas import CurrentUser

router = APIRouter(prefix="/api/v1/modules", tags=["module-engine"])


class RecordIn(BaseModel):
    title: str
    priority: str = "P2"
    status: str = "active"
    project_id: str | None = None
    data: dict = {}


class BulkIn(BaseModel):
    items: list[RecordIn]


def _validate_module(session: Session, module_id: str) -> CatalogItem:
    mod = session.exec(
        select(CatalogItem).where(
            CatalogItem.category == "module", CatalogItem.item_id == module_id
        )
    ).first()
    if not mod:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module_id}")
    return mod


def _out(r: ModuleRecord) -> dict:
    return {
        "id": r.id, "module_id": r.module_id, "project_id": r.project_id, "title": r.title,
        "status": r.status, "priority": r.priority, "data": json.loads(r.data_json or "{}"),
        "version": r.version, "created_at": r.created_at, "updated_at": r.updated_at,
    }


@router.get("")
def list_modules(session: Session = Depends(get_session),
                 _: CurrentUser = Depends(require_permission("module.read"))) -> list[dict]:
    """List all modules from the catalog, each with this tenant's record count."""
    mods = session.exec(
        select(CatalogItem).where(CatalogItem.category == "module")
    ).all()
    out = []
    for m in mods:
        out.append({
            "module_id": m.item_id, "name": m.title, "domain": m.domain,
            "mvp_priority": m.priority, "data": json.loads(m.data_json or "{}"),
        })
    return out


@router.get("/{module_id}/records")
def list_records(
    module_id: str,
    q: str | None = Query(default=None),
    status: str | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("module.read")),
) -> dict:
    _validate_module(session, module_id)
    stmt = select(ModuleRecord).where(
        ModuleRecord.tenant_id == current.tenant_id,
        ModuleRecord.module_id == module_id,
        ModuleRecord.is_deleted == False,  # noqa: E712
    )
    if status:
        stmt = stmt.where(ModuleRecord.status == status)
    if q:
        stmt = stmt.where(ModuleRecord.title.contains(q))  # type: ignore[attr-defined]
    rows = session.exec(stmt).all()
    page = rows[offset: offset + limit]
    return {"module_id": module_id, "total": len(rows), "items": [_out(r) for r in page]}


@router.post("/{module_id}/records", status_code=201)
def create_record(
    module_id: str,
    body: RecordIn,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("module.create")),
) -> dict:
    _validate_module(session, module_id)
    rec = ModuleRecord(
        tenant_id=current.tenant_id, module_id=module_id, project_id=body.project_id,
        title=body.title, status=body.status, priority=body.priority,
        data_json=json.dumps(body.data), created_by=current.id, updated_by=current.id,
    )
    session.add(rec)
    session.flush()
    record_audit(session, action=f"{module_id}.record.create", entity="module_record",
                 entity_id=rec.id, tenant_id=current.tenant_id, actor_id=current.id,
                 after={"title": body.title})
    session.commit()
    session.refresh(rec)
    return _out(rec)


@router.post("/{module_id}/records/bulk", status_code=201)
def bulk_create(
    module_id: str,
    body: BulkIn,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("module.bulk")),
) -> dict:
    _validate_module(session, module_id)
    ids = []
    for item in body.items:
        rec = ModuleRecord(
            tenant_id=current.tenant_id, module_id=module_id, project_id=item.project_id,
            title=item.title, status=item.status, priority=item.priority,
            data_json=json.dumps(item.data), created_by=current.id, updated_by=current.id,
        )
        session.add(rec)
        session.flush()
        ids.append(rec.id)
    record_audit(session, action=f"{module_id}.record.bulk", entity="module_record",
                 tenant_id=current.tenant_id, actor_id=current.id, after={"count": len(ids)})
    session.commit()
    return {"module_id": module_id, "created_ids": ids}


def _get_owned(session: Session, record_id: str, tenant_id: str) -> ModuleRecord:
    rec = session.get(ModuleRecord, record_id)
    if not rec or rec.is_deleted or rec.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Record not found")
    return rec


@router.put("/{module_id}/records/{record_id}")
def update_record(
    module_id: str,
    record_id: str,
    body: RecordIn,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("module.update")),
) -> dict:
    rec = _get_owned(session, record_id, current.tenant_id)
    before = {"title": rec.title, "status": rec.status}
    rec.title, rec.status, rec.priority = body.title, body.status, body.priority
    rec.project_id = body.project_id
    rec.data_json = json.dumps(body.data)
    rec.updated_by = current.id
    rec.version += 1
    session.add(rec)
    record_audit(session, action=f"{module_id}.record.update", entity="module_record",
                 entity_id=rec.id, tenant_id=current.tenant_id, actor_id=current.id,
                 before=before, after={"title": rec.title, "status": rec.status})
    session.commit()
    session.refresh(rec)
    return _out(rec)


@router.delete("/{module_id}/records/{record_id}", status_code=204, response_class=Response)
def delete_record(
    module_id: str,
    record_id: str,
    session: Session = Depends(get_session),
    current: CurrentUser = Depends(require_permission("module.delete")),
) -> Response:
    rec = _get_owned(session, record_id, current.tenant_id)
    rec.is_deleted = True
    rec.updated_by = current.id
    session.add(rec)
    record_audit(session, action=f"{module_id}.record.delete", entity="module_record",
                 entity_id=rec.id, tenant_id=current.tenant_id, actor_id=current.id,
                 before={"title": rec.title})
    session.commit()
    return Response(status_code=204)
