# BuildPilot360

**AI SDLC Delivery Platform** — turn raw requirements into governed, traceable, AI-assisted software delivery: requirement intake → AI analysis → backlog generation → test design → PM/Git sync → CI/CD → cloud & data deployment, with token-safe LLM execution and manual verification gates.

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

## Status

Phase 0 (foundation: tenancy, auth, RBAC, audit) and the first slice of Phase 1 (requirement intake → AI analysis → backlog) are implemented and runnable. The remaining 25 modules are scaffolded as a roadmap in [docs/BLUEPRINT.md](docs/BLUEPRINT.md).

## License

Proprietary — © BuildPilot360. All rights reserved.
