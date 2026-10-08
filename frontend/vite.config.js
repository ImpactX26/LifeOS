import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    fs: { allow: ['..'] }, // contracts/ lives one level up, outside frontend/
    // /api/* -> FastAPI (backend/main.py). 127.0.0.1, not localhost: avoids the ~1 s IPv6 detour on Windows.
    proxy: { '/api': { target: 'http://127.0.0.1:8000', rewrite: (p) => p.replace(/^\/api/, '') } },
  },
})
