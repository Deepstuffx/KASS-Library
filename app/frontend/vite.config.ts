import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { execSync } from 'node:child_process'

// Ensure Tauri loads dev server on the exact port and
// production assets use relative paths inside the app bundle.
const gitSha = (() => {
  try { return execSync('git rev-parse --short HEAD').toString().trim() } catch { return 'nogit' }
})()

export default defineConfig(({ command }) => {
  const isDev = command === 'serve'
  return {
    plugins: [react()],
    base: isDev ? '/' : './',
    define: {
      __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
      __GIT_SHA__: JSON.stringify(gitSha),
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
    },
    preview: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: false,
    },
    esbuild: isDev ? {} : { drop: ['console', 'debugger'] },
    build: {
      target: 'es2021',
      sourcemap: false,
      chunkSizeWarningLimit: 1024,
      rollupOptions: {
        output: {
          manualChunks: {
            wavesurfer: ['wavesurfer.js'],
          },
        },
      },
    },
    optimizeDeps: {
      include: [],
      exclude: ['wavesurfer.js'],
    },
  }
})
