// Builds the web app and copies its dist into the desktop app's renderer/ folder,
// so electron-builder packages a fully offline UI.
import { execSync } from "node:child_process";
import { cpSync, rmSync, existsSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..", "..", "..");
const webDir = resolve(repoRoot, "apps", "web");
const webDist = resolve(webDir, "dist");
const rendererDir = resolve(__dirname, "..", "renderer");

console.log("[bundle-web] Building web app…");
execSync("npm run build", { cwd: webDir, stdio: "inherit" });

if (!existsSync(webDist)) {
  console.error("[bundle-web] Web build output not found at", webDist);
  process.exit(1);
}

console.log("[bundle-web] Copying web dist -> desktop/renderer");
rmSync(rendererDir, { recursive: true, force: true });
mkdirSync(rendererDir, { recursive: true });
cpSync(webDist, rendererDir, { recursive: true });
console.log("[bundle-web] Done.");
