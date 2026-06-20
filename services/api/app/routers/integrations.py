"""Provider credentials / Settings (M20): add keys (encrypted), test, usage meter."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.ai import llm
from app.core.audit import record_audit
from app.core.crypto import decrypt, encrypt, mask
from app.core.db import get_session
from app.core.deps import require_permission
from app.models import LlmUsage, ProviderCredential
from app.schemas import CurrentUser, ProviderCreate, ProviderRead, UsageRead
from app.core.config import settings

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

ALLOWED = {"anthropic", "openai", "github", "aws", "azure", "gcp"}


def _to_read(c: ProviderCredential) -> ProviderRead:
    return ProviderRead(
        id=c.id, provider=c.provider, label=c.label,
        masked_secret=mask(decrypt(c.secret_encrypted)),
        config=json.loads(c.config_json or "{}"), is_active=c.is_active,
        created_at=c.created_at,
    )


@router.get("/providers", response_model=list[ProviderRead])
def list_providers(session: Session = Depends(get_session),
                   current: CurrentUser = Depends(require_permission("integration.manage"))):
    rows = session.exec(
        select(ProviderCredential).where(
            ProviderCredential.tenant_id == current.tenant_id,
            ProviderCredential.is_deleted == False)  # noqa: E712
    ).all()
    return [_to_read(c) for c in rows]


@router.post("/providers", response_model=ProviderRead, status_code=201)
def add_provider(body: ProviderCreate, session: Session = Depends(get_session),
                 current: CurrentUser = Depends(require_permission("integration.manage"))):
    if body.provider not in ALLOWED:
        raise HTTPException(400, f"Unknown provider. Allowed: {sorted(ALLOWED)}")
    # One active credential per provider: deactivate prior ones.
    for prior in session.exec(select(ProviderCredential).where(
        ProviderCredential.tenant_id == current.tenant_id,
        ProviderCredential.provider == body.provider,
        ProviderCredential.is_active == True)).all():  # noqa: E712
        prior.is_active = False
        session.add(prior)
    cred = ProviderCredential(
        tenant_id=current.tenant_id, provider=body.provider, label=body.label,
        secret_encrypted=encrypt(body.secret), config_json=json.dumps(body.config),
        is_active=body.is_active, created_by=current.id, updated_by=current.id,
    )
    session.add(cred)
    session.flush()
    record_audit(session, action="integration.add", entity="provider_credential",
                 entity_id=cred.id, tenant_id=current.tenant_id, actor_id=current.id,
                 after={"provider": body.provider, "label": body.label})
    session.commit()
    session.refresh(cred)
    return _to_read(cred)


@router.delete("/providers/{cred_id}", status_code=204)
def delete_provider(cred_id: str, session: Session = Depends(get_session),
                    current: CurrentUser = Depends(require_permission("integration.manage"))):
    cred = session.get(ProviderCredential, cred_id)
    if not cred or cred.tenant_id != current.tenant_id:
        raise HTTPException(404, "Not found")
    cred.is_deleted = True
    cred.is_active = False
    session.add(cred)
    session.commit()


@router.post("/providers/{cred_id}/test")
def test_provider(cred_id: str, session: Session = Depends(get_session),
                  current: CurrentUser = Depends(require_permission("integration.manage"))):
    cred = session.get(ProviderCredential, cred_id)
    if not cred or cred.tenant_id != current.tenant_id:
        raise HTTPException(404, "Not found")
    secret = decrypt(cred.secret_encrypted)
    if not secret:
        return {"ok": False, "detail": "No secret stored."}
    try:
        if cred.provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=secret)
            cfg = json.loads(cred.config_json or "{}")
            model = cfg.get("model") or settings.llm_default_model
            # Tiny call — minimal token spend — just to validate the key.
            client.messages.create(model=model, max_tokens=4,
                                   messages=[{"role": "user", "content": "ping"}])
            return {"ok": True, "detail": f"Anthropic key valid ({model})."}
        if cred.provider == "github":
            import httpx
            r = httpx.get("https://api.github.com/user",
                          headers={"Authorization": f"Bearer {secret}"}, timeout=20)
            return {"ok": r.status_code == 200,
                    "detail": f"GitHub: {r.json().get('login', r.status_code)}"}
        return {"ok": True, "detail": "Stored (no live test for this provider yet)."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "detail": f"{type(e).__name__}: {e}"[:300]}


@router.get("/usage", response_model=UsageRead)
def usage(session: Session = Depends(get_session),
          current: CurrentUser = Depends(require_permission("integration.manage"))):
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    row = session.exec(select(LlmUsage).where(
        LlmUsage.tenant_id == current.tenant_id, LlmUsage.period == period)).first()
    return UsageRead(
        period=period,
        input_tokens=row.input_tokens if row else 0,
        output_tokens=row.output_tokens if row else 0,
        calls=row.calls if row else 0,
        monthly_budget=settings.monthly_token_budget,
    )
