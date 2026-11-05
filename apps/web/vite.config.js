import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  server: { proxy: { '/api': { target: process.env.BFF_URL || 'http://localhost:8081' } } },
  test: { environment: 'jsdom' }
})
