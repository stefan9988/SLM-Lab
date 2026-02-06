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
    server: {
      host: true,
      port: parseInt(env.VITE_PORT || '3000'),
      proxy: {
        '/chat': env.VITE_API_URL || 'http://localhost:8000',
        '/history': env.VITE_API_URL || 'http://localhost:8000',
        '/auth': env.VITE_API_URL || 'http://localhost:8000',
      },
    },
  }
})