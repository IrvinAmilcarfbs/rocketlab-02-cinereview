import estilos from './Estrelas.module.css'

const CAMINHO_ESTRELA =
  'M12 2l2.9 6.26 6.6.72-4.9 4.6 1.35 6.42L12 16.9l-5.95 3.1L7.4 13.58 2.5 8.98l6.6-.72L12 2z'

const POSICOES = [0, 1, 2, 3, 4]

interface Props {
  /** Nota na escala 0–10 usada pelo backend. */
  nota: number
}

function Icone() {
  return (
    <svg className={estilos.icone} viewBox="0 0 24 24" aria-hidden="true">
      <path d={CAMINHO_ESTRELA} />
    </svg>
  )
}

/** Exibe a nota como cinco estrelas, com precisão de meia estrela.
 *
 * O banco guarda a escala original dos dados (0–10) e a conversão acontece aqui,
 * na interface: cada estrela vale dois pontos. Como o preenchimento é feito por
 * largura percentual, qualquer fração é representável — não só as metades.
 */
export function Estrelas({ nota }: Props) {
  const proporcao = Math.min(Math.max(nota / 10, 0), 1)

  return (
    <span className={estilos.base}>
      <span className={estilos.trilha} aria-hidden="true">
        {POSICOES.map((posicao) => (
          <Icone key={posicao} />
        ))}
      </span>
      <span
        className={estilos.preenchida}
        style={{ width: `${proporcao * 100}%` }}
        aria-hidden="true"
      >
        {POSICOES.map((posicao) => (
          <Icone key={posicao} />
        ))}
      </span>
      <span className={estilos.apenasLeitor}>
        {(nota / 2).toFixed(1)} de 5 estrelas
      </span>
    </span>
  )
}
