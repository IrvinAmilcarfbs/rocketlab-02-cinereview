import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import { buscar, enviar } from './cliente'
import type {
  AvaliacaoResumo,
  FilmeDetalhe,
  FilmeEntrada,
  FilmeResumo,
  GeneroResumo,
  Ordenacao,
  Pagina,
} from './tipos'

export const TAMANHO_PAGINA = 20

/** Carrega uma página do catálogo.
 *
 * `keepPreviousData` mantém a página anterior na tela enquanto a nova chega.
 * Sem isso, cada avanço de página apagaria a grade e mostraria o estado de
 * carregamento, fazendo o layout saltar a cada clique.
 *
 * A `queryKey` inclui a página: é ela que identifica a entrada no cache, e é
 * por isso que voltar para uma página já visitada é instantâneo.
 */
export function useCatalogo(pagina: number, busca = '', ordenar: Ordenacao = 'popularidade') {
  const termo = busca.trim()
  return useQuery({
    // O termo e a ordem fazem parte da chave: cada combinacao vira uma entrada
    // de cache propria, entao respostas que chegam fora de ordem nao se
    // sobrescrevem e repetir uma consulta ja feita e instantaneo.
    queryKey: ['catalogo', pagina, termo, ordenar],
    queryFn: () =>
      buscar<Pagina<FilmeResumo>>('/movies', {
        pagina,
        tamanho: TAMANHO_PAGINA,
        busca: termo || undefined,
        ordenar,
      }),
    placeholderData: keepPreviousData,
  })
}

export const AVALIACOES_POR_PAGINA = 10

/** Carrega a ficha completa de um filme. */
export function useFilme(id: string) {
  return useQuery({
    queryKey: ['filme', id],
    queryFn: () => buscar<FilmeDetalhe>(`/movies/${id}`),
  })
}

/** Carrega uma página de avaliações do filme.
 *
 * Fica numa query separada da ficha justamente para que criar uma avaliação
 * (Etapa 7) invalide apenas esta lista, sem recarregar o filme inteiro.
 */
export function useAvaliacoes(id: string, pagina: number) {
  return useQuery({
    queryKey: ['avaliacoes', id, pagina],
    queryFn: () =>
      buscar<Pagina<AvaliacaoResumo>>(`/movies/${id}/reviews`, {
        pagina,
        tamanho: AVALIACOES_POR_PAGINA,
      }),
    placeholderData: keepPreviousData,
  })
}

/** Vocabulário fechado de gêneros, para o formulário de cadastro.
 *
 * `staleTime: Infinity` porque a lista vem de uma dimensão de 19 valores que a
 * aplicação não altera — não há por que revalidá-la durante a sessão.
 */
export function useGeneros() {
  return useQuery({
    queryKey: ['generos'],
    queryFn: () => buscar<GeneroResumo[]>('/movies/generos'),
    staleTime: Infinity,
  })
}

/** Cadastra um filme.
 *
 * `setQueryData` guarda a ficha que o POST já devolveu: o redirecionamento para
 * a página do filme renderiza na hora, sem um segundo GET. `invalidateQueries`
 * marca o catálogo como obsoleto — sem isso, voltar à listagem mostraria o
 * cache antigo, sem o filme recém-criado.
 */
export function useCriarFilme() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (entrada: FilmeEntrada) => enviar<FilmeDetalhe>('POST', '/movies', entrada),
    onSuccess: (filme) => {
      cliente.setQueryData(['filme', filme.id], filme)
      void cliente.invalidateQueries({ queryKey: ['catalogo'] })
    },
  })
}

/** Atualiza um filme existente. */
export function useAtualizarFilme(id: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (entrada: FilmeEntrada) => enviar<FilmeDetalhe>('PUT', `/movies/${id}`, entrada),
    onSuccess: (filme) => {
      cliente.setQueryData(['filme', id], filme)
      void cliente.invalidateQueries({ queryKey: ['catalogo'] })
    },
  })
}

/** Remove um filme junto com suas avaliações.
 *
 * Aqui as consultas do filme são **removidas**, não invalidadas: invalidar
 * mandaria o TanStack Query buscar de novo um recurso que acabou de deixar de
 * existir, e a tela piscaria um erro 404 no caminho da saída.
 */
export function useRemoverFilme() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => enviar<void>('DELETE', `/movies/${id}`),
    onSuccess: (_resultado, id) => {
      cliente.removeQueries({ queryKey: ['filme', id] })
      cliente.removeQueries({ queryKey: ['avaliacoes', id] })
      void cliente.invalidateQueries({ queryKey: ['catalogo'] })
    },
  })
}
