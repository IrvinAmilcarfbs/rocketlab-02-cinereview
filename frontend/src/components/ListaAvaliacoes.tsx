import type { AvaliacaoResumo } from '../api/tipos'
import { Estrelas } from './Estrelas'
import estilos from './ListaAvaliacoes.module.css'

interface Props {
  avaliacoes: AvaliacaoResumo[]
}

/** Extrai as iniciais do nome para o avatar. */
function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/)
  const primeira = partes[0]?.[0] ?? '?'
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : ''
  return (primeira + ultima).toUpperCase()
}

export function ListaAvaliacoes({ avaliacoes }: Props) {
  return (
    <ul className={estilos.lista}>
      {avaliacoes.map((avaliacao) => (
        <li key={avaliacao.id} className={estilos.item}>
          <div className={estilos.avatar} aria-hidden="true">
            {iniciais(avaliacao.nome)}
          </div>
          <div className={estilos.corpo}>
            <div className={estilos.cabecalho}>
              <span className={estilos.autor}>{avaliacao.nome}</span>
              <span className={estilos.nota}>
                <Estrelas nota={avaliacao.nota} />
                <span className={estilos.valor}>{avaliacao.nota.toFixed(1)}</span>
              </span>
            </div>
            <p className={estilos.comentario}>{avaliacao.comentario}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}
