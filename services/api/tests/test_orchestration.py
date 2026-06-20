"""Orchestration tests using the deterministic MOCK provider (no Anthropic key → zero token spend).

Covers the real pipeline: provider settings, requirement → AI stories → prioritize → code-gen run.
GitHub publishing is exercised via the no-repo path (files stored on the run for in-app review).
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/bp360_orch.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

seed()
client = TestClient(app)


def _h() -> dict:
    r = client.post("/api/v1/auth/login",
                    json={"email": "owner@buildpilot360.dev", "password": "ChangeMe123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_provider_settings_and_usage():
    h = _h()
    # Add an (encrypted) provider key; secret is never returned raw.
    r = client.post("/api/v1/integrations/providers", headers=h, json={
        "provider": "anthropic", "label": "My Claude", "secret": "sk-ant-SECRET-123456",
        "config": {"model": "claude-opus-4-8"}})
    assert r.status_code == 201, r.text
    body = r.json()
    assert "SECRET" not in body["masked_secret"] and body["masked_secret"].endswith("3456")

    usage = client.get("/api/v1/integrations/usage", headers=h).json()
    assert usage["monthly_budget"] > 0

    # Remove it so the rest of the suite runs on the mock (no token spend).
    client.delete(f"/api/v1/integrations/providers/{body['id']}", headers=h)


def test_requirement_to_code_run():
    h = _h()
    pid = client.post("/api/v1/projects", headers=h, json={
        "name": "Pilot", "code": "PILOT", "tech_stack": "FastAPI + React"}).json()["id"]

    req = client.post("/api/v1/requirements", headers=h, json={
        "project_id": pid, "title": "Tenant onboarding",
        "raw_text": "As an admin I want to onboard tenants so customers self-serve."})
    assert req.status_code == 201
    rid = req.json()["id"]

    # Real AI story generation (mock provider → deterministic, zero tokens)
    stories = client.post(f"/api/v1/requirements/{rid}/generate-stories", headers=h)
    assert stories.status_code == 201, stories.text
    sids = [s["id"] for s in stories.json()]
    assert len(sids) >= 3

    # AI prioritization
    prio = client.post(f"/api/v1/projects/{pid}/prioritize?mode=ai", headers=h)
    assert prio.status_code == 200, prio.text
    ranked = prio.json()["ranked"]
    assert any(r["mvp"] for r in ranked)
    assert ranked[0]["rank"] == 1

    # Manual prioritization override
    man = client.patch(f"/api/v1/projects/{pid}/prioritize/manual", headers=h,
                       json=[{"story_id": sids[0], "rank": 1, "mvp": True, "priority": "P0"}])
    assert man.status_code == 200 and man.json()["updated"] == 1

    # Code + test generation (background run; TestClient runs background tasks on response)
    gen = client.post(f"/api/v1/projects/{pid}/generate", headers=h,
                     json={"story_ids": [sids[0]]})
    assert gen.status_code == 201, gen.text
    run_id = gen.json()[0]["id"]

    run = client.get(f"/api/v1/runs/{run_id}", headers=h).json()
    assert run["status"] == "succeeded", run
    assert len(run["files"]) >= 2  # code + unit test (+ perf)
    paths = [f["path"] for f in run["files"]]
    assert any(p.startswith("tests/") for p in paths)
    assert run["pr_url"] is None  # no repo configured → in-app review


def test_budget_blocks_when_exhausted():
    """When the monthly budget is exhausted, generation is blocked (quota protection)."""
    h = _h()
    from app.core.db import engine
    from app.models import LlmUsage
    from sqlmodel import Session, select
    from app.core.config import settings
    from datetime import datetime, timezone
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    with Session(engine) as s:
        me = client.get("/api/v1/auth/me", headers=h).json()
        row = s.exec(select(LlmUsage).where(LlmUsage.tenant_id == me["tenant_id"],
                                            LlmUsage.period == period)).first()
        if not row:
            row = LlmUsage(tenant_id=me["tenant_id"], period=period)
        row.input_tokens = settings.monthly_token_budget + 1
        s.add(row)
        s.commit()

    pid = client.post("/api/v1/projects", headers=h, json={"name": "B", "code": "B"}).json()["id"]
    req = client.post("/api/v1/requirements", headers=h, json={
        "project_id": pid, "title": "X", "raw_text": "do something"}).json()["id"]
    r = client.post(f"/api/v1/requirements/{req}/generate-stories", headers=h)
    assert r.status_code == 429  # blocked by budget
