import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
// /api/* -> the LifeOS FastAPI backend (backend/main.py). 127.0.0.1, not localhost: avoids a ~1 s IPv6 detour on
// Windows. LIFEOS_API points the dev server at another backend (used for testing). The dev server listens on this
// machine only; pass --host to show it on your network.
const target = process.env.LIFEOS_API || "http://127.0.0.1:8000";
const proxy = { "/api": { target, rewrite: (p: string) => p.replace(/^\/api/, "") } };
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: "127.0.0.1", port: 4173, proxy },
  preview: { host: "127.0.0.1", port: 4173, proxy },
});
