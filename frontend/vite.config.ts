import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O proxy encaminha /api para o backend em desenvolvimento. Com isso o
// navegador enxerga uma única origem: o front não precisa conhecer a URL do
// backend, não há preflight de CORS e o comportamento fica igual ao de produção
// servida atrás de um mesmo domínio.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
