import estilos from './CardEsqueleto.module.css'

/** Contorno de um card durante o carregamento.
 *
 * Ocupa exatamente o mesmo espaço do card real, de modo que a grade não salte
 * quando os dados chegam.
 */
export function CardEsqueleto() {
  return (
    <div className={estilos.card} aria-hidden="true">
      <div className={estilos.capa} />
      <div className={estilos.info}>
        <div className={estilos.linha} />
        <div className={estilos.linhaCurta} />
      </div>
    </div>
  )
}
