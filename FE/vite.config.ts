import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    proxy: {
      '/chat': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
    },
  },
})
