import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { buscar } from './cliente'
import type { FilmeResumo, Pagina } from './tipos'

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
export function useCatalogo(pagina: number) {
  return useQuery({
    queryKey: ['catalogo', pagina],
    queryFn: () =>
      buscar<Pagina<FilmeResumo>>('/movies', { pagina, tamanho: TAMANHO_PAGINA }),
    placeholderData: keepPreviousData,
  })
}
