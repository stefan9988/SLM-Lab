/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '../', '')

  return {
    plugins: [react()],
    envDir: '../',
    define: {
      'import.meta.env.VITE_GOOGLE_CLIENT_ID': JSON.stringify(env.GOOGLE_CLIENT_ID || ''),
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/test/setup.ts',
    },
    server: {
      host: true,
      port: parseInt(env.VITE_PORT || '3000'),
      proxy: {
        '/chat': { target: env.VITE_API_URL || 'http://localhost:8000' },
        '/history': { target: env.VITE_API_URL || 'http://localhost:8000' },
        '/auth': { target: env.VITE_API_URL || 'http://localhost:8000' },
        '/sessions': { target: env.VITE_API_URL || 'http://localhost:8000' },
        '/archive': { target: env.VITE_API_URL || 'http://localhost:8000' },
        '/schemas': { target: env.VITE_API_URL || 'http://localhost:8000' },
        '/analyze': { target: env.VITE_API_URL || 'http://localhost:8000' },
        '/general-agent': { target: env.VITE_API_URL || 'http://localhost:8000' },
      },
    },
  }
})