import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id: string) => {
          if (id.includes('/react-dom/') || id.includes('/react/') || id.includes('/react-router')) return 'vendor-react'
          if (id.includes('/recharts/')) return 'vendor-charts'
          if (id.includes('/leaflet/') || id.includes('/react-leaflet/')) return 'vendor-map'
          if (id.includes('/@radix-ui/') || id.includes('/lucide-react/') || id.includes('/class-variance-authority/')) return 'vendor-ui'
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
})
