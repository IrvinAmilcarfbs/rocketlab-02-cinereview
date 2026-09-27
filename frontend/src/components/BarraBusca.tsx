import estilos from './BarraBusca.module.css'

interface Props {
  valor: string
  onMudar: (valor: string) => void
  /** Indica que há uma requisição de busca em andamento. */
  carregando?: boolean
}

export function BarraBusca({ valor, onMudar, carregando = false }: Props) {
  return (
    <div className={estilos.caixa}>
      <svg className={estilos.lupa} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M10 4a6 6 0 104.47 10.03l4.25 4.25 1.41-1.41-4.25-4.25A6 6 0 0010 4zm0 2a4 4 0 110 8 4 4 0 010-8z"
          fill="currentColor"
        />
      </svg>

      <input
        type="search"
        className={estilos.campo}
        value={valor}
        onChange={(evento) => onMudar(evento.target.value)}
        placeholder="Buscar por título…"
        aria-label="Buscar filmes por título"
        autoComplete="off"
      />

      {valor && (
        <button
          type="button"
          className={estilos.limpar}
          onClick={() => onMudar('')}
          aria-label="Limpar busca"
        >
          ×
        </button>
      )}

      {carregando && <span className={estilos.girando} aria-hidden="true" />}
    </div>
  )
}
