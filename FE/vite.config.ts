import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Load env from root directory (one level up)
  const env = loadEnv(mode, '../', 'VITE_')
  
  return {
    plugins: [react()],
    envDir: '../', // Tell Vite to look for .env in parent directory
    server: {
      host: true,
      port: parseInt(env.VITE_PORT || '3000'),
      proxy: {
        '/chat': env.VITE_API_URL || 'http://localhost:8000',
        '/history': env.VITE_API_URL || 'http://localhost:8000',
      },
    },
  }
})