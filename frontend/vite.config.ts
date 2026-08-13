import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Base public path. Locally this is "/". For GitHub Pages *project* sites the
  // app is served from https://<user>.github.io/<repo>/, so the CI build sets
  // VITE_BASE to "/<repo>/". Falls back to "/" everywhere else.
  base: process.env.VITE_BASE || '/',
})
