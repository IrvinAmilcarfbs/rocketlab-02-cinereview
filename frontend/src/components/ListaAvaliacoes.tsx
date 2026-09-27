import { useState } from 'react'

import { useRemoverAvaliacao } from '../api/filmes'
import type { AvaliacaoResumo } from '../api/tipos'
import { formatarQuando } from '../utils/formato'
import { Estrelas } from './Estrelas'
import estilos from './ListaAvaliacoes.module.css'

interface Props {
  avaliacoes: AvaliacaoResumo[]
  filmeId: string
}

/** Extrai as iniciais do nome para o avatar. */
function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/)
  const primeira = partes[0]?.[0] ?? '?'
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : ''
  return (primeira + ultima).toUpperCase()
}

export function ListaAvaliacoes({ avaliacoes, filmeId }: Props) {
  const remover = useRemoverAvaliacao(filmeId)
  // Guarda o id em confirmação, e não um booleano: a lista tem vários itens e a
  // confirmação pertence a um deles.
  const [confirmando, setConfirmando] = useState<string | null>(null)

  return (
    <ul className={estilos.lista}>
      {avaliacoes.map((avaliacao) => {
        const emConfirmacao = confirmando === avaliacao.id
        const removendo = remover.isPending && remover.variables === avaliacao.id

        return (
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

              <div className={estilos.rodape}>
                {/* `dateTime` guarda o instante exato em formato legível por
                    máquina, enquanto o texto visível é aproximado. */}
                <time className={estilos.quando} dateTime={avaliacao.criado_em}>
                  {formatarQuando(avaliacao.criado_em)}
                </time>

                {emConfirmacao ? (
                  <span className={estilos.confirmacao}>
                    <span className={estilos.pergunta}>Remover esta avaliação?</span>
                    <button
                      type="button"
                      className={estilos.confirmar}
                      disabled={removendo}
                      onClick={() =>
                        remover.mutate(avaliacao.id, {
                          onSettled: () => setConfirmando(null),
                        })
                      }
                    >
                      {removendo ? 'Removendo…' : 'Remover'}
                    </button>
                    <button
                      type="button"
                      className={estilos.manter}
                      disabled={removendo}
                      onClick={() => setConfirmando(null)}
                    >
                      Cancelar
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className={estilos.acaoRemover}
                    onClick={() => setConfirmando(avaliacao.id)}
                  >
                    Remover
                  </button>
                )}
              </div>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
