import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // contracts/ lives one level up, outside frontend/
  server: { port: 5173, fs: { allow: ['..'] } },
})
