import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" makes the build portable: same dist works on Vercel and inside Electron (file://).
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { port: 5173 },
  build: { outDir: "dist", sourcemap: false },
});
