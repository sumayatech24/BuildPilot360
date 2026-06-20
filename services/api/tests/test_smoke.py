"""End-to-end smoke test: login -> project -> requirement -> analyze -> backlog -> lifecycle."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/bp360_test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

seed()
client = TestClient(app)


def _token() -> str:
    r = client.post("/api/v1/auth/login",
                    json={"email": "owner@buildpilot360.dev", "password": "ChangeMe123!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_full_flow():
    h = {"Authorization": f"Bearer {_token()}"}

    me = client.get("/api/v1/auth/me", headers=h).json()
    assert "*" in me["permissions"]

    proj = client.post("/api/v1/projects", headers=h,
                       json={"name": "Demo", "code": "DEMO"})
    assert proj.status_code == 201, proj.text
    pid = proj.json()["id"]

    req = client.post("/api/v1/requirements", headers=h, json={
        "project_id": pid,
        "title": "Tenant onboarding self-service",
        "raw_text": "As an admin I want to onboard a new tenant so that customers can self serve.",
    })
    assert req.status_code == 201, req.text
    rid = req.json()["id"]

    analysis = client.post(f"/api/v1/requirements/{rid}/analyze", headers=h)
    assert analysis.status_code == 200, analysis.text
    assert analysis.json()["confidence"] > 0

    backlog = client.post(f"/api/v1/requirements/{rid}/generate-backlog", headers=h)
    assert backlog.status_code == 201, backlog.text
    story_ids = backlog.json()["created_story_ids"]
    assert len(story_ids) == 4

    stories = client.get("/api/v1/stories", headers=h, params={"project_id": pid}).json()
    assert len(stories) == 4

    upd = client.patch(f"/api/v1/stories/{story_ids[0]}/status", headers=h,
                      json={"status_code": "READY_FOR_DEV"})
    assert upd.status_code == 200, upd.text
    assert upd.json()["status_code"] == "READY_FOR_DEV"


def test_rbac_blocks_unauthenticated():
    assert client.get("/api/v1/projects").status_code == 401


def test_full_catalog_loaded():
    h = {"Authorization": f"Bearer {_token()}"}
    summary = client.get("/api/v1/catalog/summary", headers=h).json()
    totals = summary["totals"]
    assert totals["modules"] == 27
    assert totals["features"] >= 1248
    assert totals["user_stories"] >= 450
    assert totals["nfrs"] == 60

    # Filter features by module
    feats = client.get("/api/v1/catalog/feature", headers=h,
                       params={"module_id": "M01", "limit": 5}).json()
    assert feats["total"] > 0
    assert all(i["module_id"] == "M01" for i in feats["items"])


def test_generic_module_engine():
    h = {"Authorization": f"Bearer {_token()}"}
    mods = client.get("/api/v1/modules", headers=h).json()
    assert len(mods) == 27

    # Create -> list -> update -> delete a record on module M08 (Test Design)
    created = client.post("/api/v1/modules/M08/records", headers=h,
                         json={"title": "Regression pack for checkout", "priority": "P1",
                               "data": {"coverage": "smoke"}})
    assert created.status_code == 201, created.text
    rid = created.json()["id"]

    listed = client.get("/api/v1/modules/M08/records", headers=h).json()
    assert listed["total"] == 1

    upd = client.put(f"/api/v1/modules/M08/records/{rid}", headers=h,
                    json={"title": "Regression pack v2", "status": "in_review", "data": {}})
    assert upd.status_code == 200 and upd.json()["title"] == "Regression pack v2"

    assert client.delete(f"/api/v1/modules/M08/records/{rid}", headers=h).status_code == 204
    assert client.get("/api/v1/modules/M08/records", headers=h).json()["total"] == 0

    # Unknown module rejected
    assert client.get("/api/v1/modules/M99/records", headers=h).status_code == 404
