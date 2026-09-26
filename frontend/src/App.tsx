import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ErroApi } from './api/cliente'
import { Catalogo } from './pages/Catalogo'
import { FilmeDetalhe } from './pages/FilmeDetalhe'

const clienteQuery = new QueryClient({
  defaultOptions: {
    queries: {
      // Os dados do catálogo mudam pouco: por cinco minutos uma página já
      // visitada é servida do cache, sem nova requisição.
      staleTime: 5 * 60 * 1000,
      retry: (tentativas, erro) => {
        // Repetir um 4xx é inútil: o pedido está errado e continuará errado.
        if (erro instanceof ErroApi && erro.status < 500) {
          return false
        }
        return tentativas < 2
      },
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={clienteQuery}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Catalogo />} />
          <Route path="/filmes/:id" element={<FilmeDetalhe />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
