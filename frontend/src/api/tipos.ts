/** Contrato da API, escrito à mão a partir do OpenAPI publicado pelo backend.
 *
 * Estes tipos precisam acompanhar `app/movies/schemas.py`. Enquanto forem
 * poucos, mantê-los aqui é mais simples do que gerar; se os endpoints
 * crescerem, vale derivá-los do OpenAPI com `openapi-typescript`.
 */

export interface GeneroResumo {
  id: string
  nome: string
}

export interface FilmeResumo {
  id: string
  titulo: string
  ano: number | null
  poster_url: string | null
  generos: GeneroResumo[]
  /** Escala 0–10; nulo quando o filme ainda não recebeu avaliações. */
  nota_media: number | null
  qtd_avaliacoes: number
}

/** Envelope devolvido por todos os endpoints paginados. */
export interface Pagina<T> {
  items: T[]
  total: number
  pagina: number
  tamanho: number
  paginas: number
}
