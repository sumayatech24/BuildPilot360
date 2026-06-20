const { contextBridge } = require("electron");

// The API base can be overridden at packaging time via BP360_API_BASE so a desktop
// build can target a hosted backend (e.g. the Vercel-fronted API).
const apiBase = process.env.BP360_API_BASE || "http://localhost:8000";

// With contextIsolation enabled, the only safe way to publish into the page's main
// world is contextBridge. api.ts reads window.__BP360_API_BASE__.
contextBridge.exposeInMainWorld("__BP360_API_BASE__", apiBase);
contextBridge.exposeInMainWorld("bp360", {
  platform: process.platform,
  apiBase,
});
