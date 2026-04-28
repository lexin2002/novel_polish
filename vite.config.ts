import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    renderer()
  ],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:57621',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:57621',
        ws: true
      }
    }
  }
})