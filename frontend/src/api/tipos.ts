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

export interface PessoaResumo {
  id: string
  nome: string
}

export interface ProdutoraResumo {
  id: string
  nome: string
}

/** Métricas externas e financeiras vindas da tabela fato.
 *
 * Tudo é opcional porque a cobertura varia muito: notas externas existem para
 * ~87% do catálogo, enquanto orçamento aparece em 8% e receita em 3,5%.
 */
export interface MetricasFilme {
  popularidade: number | null
  nota_tmdb: number | null
  qtd_tmdb: number | null
  nota_imdb: number | null
  qtd_imdb: number | null
  orcamento_usd: number | null
  receita_usd: number | null
  lucro_usd: number | null
}

export interface FilmeDetalhe {
  id: string
  titulo: string
  ano: number | null
  /** Data ISO (`2017-02-01`); o JSON não tem tipo de data. */
  data_lancamento: string | null
  duracao_minutos: number | null
  status: string | null
  sinopse: string | null
  poster_url: string | null
  backdrop_url: string | null
  generos: GeneroResumo[]
  diretores: PessoaResumo[]
  roteiristas: PessoaResumo[]
  elenco: PessoaResumo[]
  produtoras: ProdutoraResumo[]
  metricas: MetricasFilme | null
  nota_media: number | null
  qtd_avaliacoes: number
}

/** Valores de `status_filme` presentes na base. É um conjunto fechado. */
export type StatusFilme = 'Lançado' | 'Pós-Produção' | 'Em Produção' | 'Planejado'

/** Ordem do catálogo. `recentes` exibe primeiro o que foi cadastrado aqui. */
export type Ordenacao = 'popularidade' | 'recentes'

/** Subconjunto editável de um filme, no cadastro e na atualização.
 *
 * Espelha `FilmeEntrada` no backend. O `PUT` substitui este subconjunto
 * inteiro: o que o formulário mostra em branco fica em branco. Campos fora
 * daqui — popularidade, notas externas, financeiro, backdrop, elenco,
 * roteiristas e produtoras — não são alcançados pelo formulário.
 */
export interface FilmeEntrada {
  titulo: string
  ano: number | null
  sinopse: string | null
  duracao_minutos: number | null
  status: StatusFilme | null
  poster_url: string | null
  /** Nomes de gêneros existentes; o backend recusa os desconhecidos. */
  generos: string[]
  /** Nomes de diretores; os que ainda não existem são criados. */
  diretores: string[]
}

export interface AvaliacaoResumo {
  id: string
  nome: string
  /** Escala 0–10. */
  nota: number
  comentario: string
  criado_em: string
}

/** Avaliação enviada por um usuário.
 *
 * `nota` vai de 0 a 10, como no banco. O seletor de estrelas produz inteiros de
 * 1 a 10 (½ a 5 estrelas), mas o contrato acompanha a escala inteira.
 */
export interface AvaliacaoEntrada {
  nome: string
  nota: number
  comentario: string
}
