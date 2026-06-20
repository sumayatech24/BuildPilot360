const { app, BrowserWindow, shell, Menu } = require("electron");
const path = require("path");

const isDev = process.env.BP360_DEV === "1";
// In dev we load the Vite server; in production we load the bundled web build.
const DEV_URL = process.env.BP360_WEB_URL || "http://localhost:5173";

function createWindow() {
  const win = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1024,
    minHeight: 680,
    backgroundColor: "#0b1220",
    title: "BuildPilot360",
    icon: path.join(__dirname, "build", process.platform === "win32" ? "icon.ico" : "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Open external links in the user's browser, not inside the app shell.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http")) shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev) {
    win.loadURL(DEV_URL);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "renderer", "index.html"));
  }
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
