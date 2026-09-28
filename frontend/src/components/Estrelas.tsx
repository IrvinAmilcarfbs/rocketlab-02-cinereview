import { FilaEstrelas } from './FilaEstrelas'
import estilos from './Estrelas.module.css'

interface Props {
  /** Nota na escala 0–10 usada pelo backend. */
  nota: number
}

/** Exibe a nota como cinco estrelas, com qualquer fração representável.
 *
 * O banco guarda a escala original dos dados (0–10) e a conversão acontece aqui,
 * na interface: cada estrela vale dois pontos. Frações arbitrárias importam,
 * porque 39.432 das avaliações carregadas têm valores como 1,27 e 7,33.
 */
export function Estrelas({ nota }: Props) {
  return (
    <span className={estilos.base}>
      <FilaEstrelas nota={nota} />
      <span className={estilos.apenasLeitor}>{(nota / 2).toFixed(1)} de 5 estrelas</span>
    </span>
  )
}
