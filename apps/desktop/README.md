# BuildPilot360 Desktop

Electron shell that packages the BuildPilot360 web UI into installable desktop apps:

- **Windows** — NSIS installer (`BuildPilot360 Setup x.y.z.exe`) **and** a portable `.exe`
- **macOS** — `.dmg` (x64 + arm64)
- **Linux** — AppImage

## How it works

`scripts/bundle-web.mjs` builds `apps/web` and copies its `dist/` into `renderer/`, so the
packaged app ships a fully offline UI. `main.js` loads `renderer/index.html` in production (or the
Vite dev server when `BP360_DEV=1`). `preload.js` injects the API base URL into the page via
`contextBridge` (context isolation stays on). Point a build at a hosted backend with
`BP360_API_BASE`.

## Develop

```bash
# from repo root
npm install
npm run dev:web            # terminal 1 — Vite dev server on :5173
npm run dev:desktop        # terminal 2 — Electron against the dev server
```

## Build installers

```bash
npm run gen:icons          # from repo root: rasterize brand/icon.svg -> icon.ico / icon.png
npm run build:win          # Windows NSIS + portable .exe  -> apps/desktop/release/
npm run build:mac          # macOS .dmg (run on macOS)     -> apps/desktop/release/
```

> **CI is the recommended path.** `.github/workflows/build-desktop.yml` builds Windows on
> `windows-latest` and macOS on `macos-latest` and uploads the installers as artifacts. The macOS
> `.dmg` *must* be built on macOS.

### Local Windows note

Some endpoint-security / antivirus products quarantine electron-builder's `app-builder.exe` helper
and Electron's own `electron.exe` as false positives, which breaks local packaging with a spurious
`ENOENT` (the file is removed moments after extraction). If that happens, add an exclusion for the
repo's `node_modules` or just use the CI workflow above.
