# Blueprint → implementation status

Source: *AI Automated SDLC Platform Blueprint (v3)* — 27 modules, 1248 features, 450 user stories,
74 DB tables, 60 NFRs. This repo delivers the foundation and the first MVP slice; the table tracks
the rest as the roadmap.

## Module status

| Module | Domain | MVP | Status in this repo |
|--------|--------|-----|---------------------|
| M01 Tenant, Org & RBAC | Core | MVP | **Implemented** — tenants, users, roles, permissions, RBAC |
| M02 Requirement Intake | Discovery | MVP | **Implemented** — text intake + API |
| M03 AI Requirement Analysis | Discovery | MVP | **Implemented** — provider-neutral analyzer |
| M04 Product Discovery & MVP Planning | Discovery | MVP | Planned |
| M05 Backlog Generation | Delivery | MVP | **Implemented** — story generation from analysis |
| M06 Story Template & Governance | Delivery | MVP | **Partial** — 16-stage lifecycle + audited transitions |
| M07 PM Integrations (Jira/ADO/ClickUp) | Integrations | MVP | Planned (adapter framework) |
| M08 BDD/TDD & Test Design | Quality | MVP | Planned |
| M20 AI Prompt & Model Management | AI Platform | MVP | **Partial** — model routing in AI adapter |
| M21 Reporting, Governance & Audit | Governance | MVP | **Partial** — audit log + dashboard |
| M23 Admin Configuration | Core | MVP | **Partial** — DB-driven config tables |
| M09–M19, M22, M24 | Eng/DevOps/Cloud/Mobile | Phase 2+ | **Engine-backed** — generic CRUD/search/bulk/lifecycle live; bespoke logic planned |
| M25 GCP Dev & Deployment | Cloud | Phase 4 | **Engine-backed**; DeploymentAdapter planned |
| M26 Data Pipelines & Orchestration | Data | Phase 4 | **Engine-backed**; pipeline designer planned |
| M27 Data Platform Integrations | Data | Phase 4 | **Engine-backed**; platform adapters planned |

> **Every module is operational today** via the metadata-driven module engine
> (`/api/v1/modules/{id}/records`): tenant-scoped create/read/update/delete/bulk, RBAC-gated and
> audited, with the module's full planned-feature list visible in its workspace. "Implemented" above
> means the module also has bespoke domain logic beyond the generic engine.

## Implemented now

- Multi-tenant data model with audit fields on every business table.
- JWT auth; database-driven roles + permission catalog; RBAC enforced per-endpoint.
- Append-only audit log capturing before/after on writes and every lifecycle transition.
- Requirement intake → provider-neutral AI analysis (gaps, questions, NFRs, acceptance criteria,
  suggested stories, confidence) → one-click backlog generation.
- The full 16-stage Story Lifecycle (from the *Story Lifecycle Workflow* sheet) seeded as config and
  driving the Kanban board.
- Three delivery targets wired: web (Vercel), desktop (Electron → win/mac installers), API (Docker).

## Token-safe execution (from the v3 sheets) — design honored

The AI adapter is built to send compact, scoped context (requirement summary, not whole project),
record token usage, and route by task. `ClaudeProvider` is the seam where the real Anthropic SDK call,
JSON-schema output validation (NFR-045), secret redaction, and token budgeting plug in.

## Next milestones

1. **Phase 1 completion** — clarification loop, prioritization scoring, story editor, approvals.
2. **Phase 2** — PM sync adapters (Jira/ADO/ClickUp) on the provider-neutral integration framework.
3. **Phase 3** — BDD/TDD test generation linked to stories.
4. **Phase 4+** — architecture/code automation, CI/CD, cloud (incl. GCP) and data-platform adapters.
