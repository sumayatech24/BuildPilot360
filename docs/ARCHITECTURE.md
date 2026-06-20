# Architecture

BuildPilot360 is an enterprise, multi-tenant AI SDLC delivery platform. This repo implements the
Phase 0 foundation and the first Phase 1 slice across three delivery targets that share one backend.

```
                       ┌──────────────────────────────┐
   Web (Vercel) ─────► │                              │
                       │   FastAPI API (services/api) │ ──► PostgreSQL / SQLite
 Desktop (Electron) ─► │   JWT · RBAC · audit · AI    │ ──► (Redis, pgvector — Phase 1+)
                       │                              │
   Mobile (Phase 8) ─► └──────────────────────────────┘
```

## Backend (`services/api`)

Clean layering per the blueprint's Backend Prompt:

- **Routers** (`app/routers/`) — HTTP surface, validation, RBAC dependency injection.
- **Core** (`app/core/`) — config, DB engine, security (hash/JWT), audit service, auth+RBAC deps.
- **Models** (`app/models.py`) — SQLModel tables; every business row is tenant-scoped + audited.
- **AI** (`app/ai/`) — provider-neutral adapter (`StubProvider`, `ClaudeProvider`) with model routing.
- **Seed** (`app/seed.py`) — master/config data only: permissions, roles, 16-stage lifecycle, owner.

Guardrails realized: tenant isolation (NFR-001), DB-driven RBAC (NFR-002), audit logging (NFR-005),
provider-neutral AI + fallback (NFR-042/050), no hardcoded business data (Platform Principle).

## Web (`apps/web`)

React + TypeScript + Vite SPA. `base: "./"` makes one build portable across Vercel (https) and
Electron (`file://`). API base URL is config-driven (`VITE_API_BASE_URL`, or a global injected by the
desktop preload). Pages: Login, Dashboard, Requirement intake (intake → AI analysis → backlog), Board
(16-stage lifecycle Kanban).

## Desktop (`apps/desktop`)

Electron shell. `bundle-web.mjs` folds the web `dist/` into `renderer/` for a fully offline UI.
electron-builder targets Windows (NSIS + portable), macOS (dmg), Linux (AppImage). Context isolation
on; only a minimal, safe surface is exposed via `contextBridge`.

## Why one codebase, three apps

The web build is the single source of UI truth. Vercel serves it over HTTPS; Electron embeds the same
`dist` for desktop. This guarantees pixel-and-behavior parity and means new features ship to web and
desktop simultaneously.
