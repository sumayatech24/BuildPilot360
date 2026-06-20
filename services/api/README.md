# BuildPilot360 API

FastAPI + SQLModel backend. Implements the Phase 0 foundation and the first Phase 1 slice:
tenancy, JWT auth, DB-driven RBAC, audit logging, requirement intake, provider-neutral AI
analysis, backlog generation, and the 16-stage story lifecycle.

## Run

```bash
python -m venv .venv && .venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env
python -m app.seed            # seeds permissions, roles, lifecycle, owner (no demo business data)
uvicorn app.main:app --reload # http://localhost:8000  — interactive docs at /docs
pytest                        # end-to-end smoke test
```

## Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/auth/login` | Email/password → JWT |
| GET  | `/api/v1/auth/me` | Current user, roles, permissions |
| GET/POST | `/api/v1/projects` | List / create projects |
| GET/POST | `/api/v1/requirements` | Intake (M02) |
| POST | `/api/v1/requirements/{id}/analyze` | AI analysis (M03) |
| POST | `/api/v1/requirements/{id}/generate-backlog` | Generate stories (M05) |
| GET  | `/api/v1/stories` | Backlog board data |
| GET  | `/api/v1/stories/lifecycle` | 16-stage lifecycle config |
| PATCH| `/api/v1/stories/{id}/status` | Lifecycle transition (audited) |
| GET  | `/api/v1/catalog/summary` | Counts across the whole blueprint |
| GET  | `/api/v1/catalog/{category}` | Browse/filter any sheet (feature, user_story, nfr, api_integration, screen, roadmap, …) |
| GET  | `/api/v1/modules` | All 27 modules from the catalog |
| GET/POST | `/api/v1/modules/{id}/records` | Generic tenant CRUD for any module |
| POST | `/api/v1/modules/{id}/records/bulk` | Bulk create |
| PUT/DELETE | `/api/v1/modules/{id}/records/{rid}` | Update / soft-delete (audited) |

## Loading the blueprint

`app/data/blueprint.json` (committed) is generated from the workbook by
`scripts/ingest_blueprint.py` and loaded into `catalog_items` by `python -m app.seed`. Re-run the
ingest script only if the source workbook changes.

## Design notes

- **Database/API-driven** — roles, permissions, and lifecycle stages live in tables (see `app/seed.py`), not in code branches.
- **Tenant isolation + RBAC** (NFR-001/002) enforced via `app/core/deps.py`.
- **Audit trail** (NFR-005) via `app/core/audit.py`, append-only `audit_logs`.
- **Provider-neutral AI** (M20, NFR-042/050) via `app/ai/provider.py` — deterministic stub by default; `ClaudeProvider` shows the adapter pattern. Set `AI_PROVIDER=claude` + `AI_API_KEY` to route to Claude.
- **SQLite by default**, PostgreSQL-ready via `DATABASE_URL`.
