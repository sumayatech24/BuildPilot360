# BuildPilot360

**AI SDLC Delivery Platform** — turn raw requirements into governed, traceable, AI-assisted software delivery: requirement intake → AI analysis → backlog generation → test design → PM/Git sync → CI/CD → cloud & data deployment, with token-safe LLM execution and manual verification gates.

> **▶ Deploy the full stack (free) — Postgres + API + web:**
>
> [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sumayatech24/BuildPilot360)
>
> One click reads [`render.yaml`](render.yaml) and provisions a free PostgreSQL database, the
> FastAPI backend (Docker, auto-seeded on first boot), and the web app — all wired together.
> Validated end-to-end against real Postgres via Docker.
>
> Static browser-only demo (no backend): https://sumayatech24.github.io/BuildPilot360/

Built from the *AI Automated SDLC Platform Blueprint (v3)* — 27 modules, 1248 planned features, 450 user stories, 74 DB tables. This repository implements the **Phase 0 foundation + start of the Phase 1 MVP** as a fully runnable product across three delivery targets.

## Delivery targets

| Target | Tech | Output |
|--------|------|--------|
| **Web app** | React + TypeScript + Vite | Static SPA → **Vercel** |
| **Desktop app** | Electron + electron-builder | **Windows `.exe`** (NSIS installer + portable) and **macOS `.dmg`** |
| **API / backend** | Python FastAPI + SQLModel | Container / server deployment |

## Repository layout

```
buildpilot360/
├── brand/                 # Logo (SVG), palette, app icon source
├── apps/
│   ├── web/               # React + TS web app (deploys to Vercel)
│   └── desktop/           # Electron shell → Windows .exe + macOS .dmg
├── services/
│   └── api/               # FastAPI backend (tenants, RBAC, audit, requirements, AI, backlog)
├── scripts/               # Icon generation, tooling
└── docs/                  # Architecture + distilled blueprint
```

## Quick start

### 1. Backend API
```bash
cd services/api
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m app.seed                                  # seed master config (no demo business data)
uvicorn app.main:app --reload                       # http://localhost:8000  (docs at /docs)
```

### 2. Web app
```bash
cd apps/web
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev                                          # http://localhost:5173
```

### 3. Desktop app
```bash
npm install                  # from repo root (workspaces)
npm run gen:icons            # rasterize brand/icon.svg -> app icons
npm run dev:desktop          # launch Electron against the dev web server
npm run build:desktop:win    # produce Windows installer + portable .exe
npm run build:desktop:mac    # produce macOS .dmg (run on macOS / CI)
```

## Deployment

- **Web → Vercel**: `apps/web` ships with `vercel.json`. Set project root to `apps/web`, framework **Vite**, env `VITE_API_BASE_URL` to the hosted API. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
- **Desktop**: `npm run build:desktop:win` / `:mac` produces signed-able installers under `apps/desktop/release/`.

## Default login (seeded)

After `python -m app.seed`: **`owner@buildpilot360.dev` / `ChangeMe123!`** (rotate immediately).

## What's implemented

**Foundation (Phase 0):** multi-tenant data model, JWT auth, database-driven RBAC, append-only audit log.

**Requirement → backlog flow (Phase 1):** requirement intake → provider-neutral AI analysis (gaps, questions, NFRs, acceptance criteria, confidence) → backlog generation → 16-stage story lifecycle board.

**Entire blueprint as live data:** the full workbook is ingested into the platform DB — **27 modules, 1268 features, 470 user stories, 60 NFRs, 40 integrations, 155 screens**, plus roadmap, lifecycle, token-safe rules and verification gates (2,396 catalog items). All browsable and filterable in the web UI (`/features`, `/stories`, `/nfrs`, `/integrations`, `/screens`, `/roadmap`).

**Metadata-driven module engine:** all 27 modules get working tenant-scoped **CRUD + search + bulk + lifecycle**, RBAC-gated and audited, through one generic endpoint family (`/api/v1/modules/{module_id}/records`) and a per-module workspace UI — the capability behind the 1248 features, without 1248 bespoke screens.

See [docs/BLUEPRINT.md](docs/BLUEPRINT.md) for per-module status and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design.

## License

Proprietary — © BuildPilot360. All rights reserved.
