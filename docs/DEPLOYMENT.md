# Deployment guide

BuildPilot360 ships in three forms from one repo: **web**, **desktop installers
(Windows .exe + macOS .dmg)**, and the **API** (any container host).

## 0. Live demo — GitHub Pages (zero credentials)

The web app is **static-first**: when no backend is configured it runs entirely in the browser,
serving the full blueprint from a bundled JSON and persisting data in `localStorage`. `.github/
workflows/deploy-pages.yml` builds it and publishes to GitHub Pages using the repo's built-in
`GITHUB_TOKEN` on every push to `main`.

- **URL:** https://sumayatech24.github.io/BuildPilot360/
- If the first run reports Pages isn't enabled, open **Settings → Pages → Build and deployment →
  Source: GitHub Actions** once, then re-run the workflow.

This is the quickest "working version." For server-side multi-tenancy, point the web app at the
hosted API (below) by setting `VITE_API_BASE_URL`.

## 1. Web → Vercel

The web app is a static Vite SPA, so Vercel hosting is a clean fit.

**Option A — Vercel dashboard (quickest)**
1. Import the Git repo into Vercel.
2. Set **Root Directory** to `apps/web`.
3. Framework preset: **Vite** (auto-detected via `apps/web/vercel.json`).
4. Add environment variable `VITE_API_BASE_URL` = your hosted API URL.
5. Deploy. The SPA rewrite in `vercel.json` handles client-side routing.

**Option B — Vercel CLI**
```bash
cd apps/web
npm i -g vercel
vercel link           # choose/create the project
vercel --prod         # build + deploy
```

**Option C — GitHub Actions** — `.github/workflows/deploy-web.yml` auto-deploys on push to `main`.
Add repo secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.

## 2. Desktop installers

Use CI (`.github/workflows/build-desktop.yml`) — it builds Windows on `windows-latest` and macOS on
`macos-latest` and uploads the installers as artifacts. Trigger it by pushing a tag (`git tag v0.1.0
&& git push --tags`) or via **Run workflow**.

Locally (Windows host):
```bash
npm install
npm run build:desktop:win     # -> apps/desktop/release/BuildPilot360 Setup 0.1.0.exe (+ portable)
```
macOS `.dmg` must be built on a Mac. Set `BP360_API_BASE` to point a build at your hosted API.

## 3. API

```bash
cd services/api
docker build -t buildpilot360-api .
docker run -p 8000:8000 -e DATABASE_URL=postgresql+psycopg://… -e JWT_SECRET=… buildpilot360-api
```
Runs anywhere a container runs (Fly.io, Render, AWS ECS, GCP Cloud Run, Azure Container Apps).
After first boot, run `python -m app.seed` against the same `DATABASE_URL` to load master config.
Set `CORS_ORIGINS` to include your Vercel domain and `app://.` for the desktop app.
