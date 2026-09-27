import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { buscar } from './cliente'
import type {
  AvaliacaoResumo,
  FilmeDetalhe,
  FilmeResumo,
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
export function useCatalogo(pagina: number, busca = '') {
  const termo = busca.trim()
  return useQuery({
    // O termo faz parte da chave: cada busca vira uma entrada de cache propria,
    // entao respostas que chegam fora de ordem nao se sobrescrevem e repetir
    // uma busca ja feita e instantaneo.
    queryKey: ['catalogo', pagina, termo],
    queryFn: () =>
      buscar<Pagina<FilmeResumo>>('/movies', {
        pagina,
        tamanho: TAMANHO_PAGINA,
        busca: termo || undefined,
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
