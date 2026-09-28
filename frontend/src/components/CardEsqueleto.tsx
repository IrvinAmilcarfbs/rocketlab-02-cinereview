import estilos from './CardEsqueleto.module.css'

/** Contorno de um cartão durante o carregamento.
 *
 * Ocupa exatamente o mesmo espaço do cartão real — um retângulo na proporção de
 * pôster — de modo que a grade não salte quando os dados chegam. Como a
 * informação do cartão vive sobre o pôster, o esqueleto não precisa de linhas de
 * texto: o cartão pronto também não mostra nenhuma em repouso.
 */
export function CardEsqueleto() {
  return <div className={estilos.cartao} aria-hidden="true" />
}
