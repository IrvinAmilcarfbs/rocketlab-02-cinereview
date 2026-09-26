import { useState } from 'react'

import type { PessoaResumo } from '../api/tipos'
import estilos from './ListaCreditos.module.css'

interface Props {
  titulo: string
  pessoas: PessoaResumo[]
  /** Acima deste total a lista é recolhida atrás de um botão. */
  limite?: number
}

/** Lista de nomes creditados, recolhível quando muito longa.
 *
 * Um filme do catálogo chega a ter 150 pessoas; sem limite, a ficha vira uma
 * lista de nomes. Direção e roteiro, que são poucos, dispensam o corte.
 */
export function ListaCreditos({ titulo, pessoas, limite }: Props) {
  const [expandido, setExpandido] = useState(false)

  if (pessoas.length === 0) {
    return null
  }

  const precisaRecolher = limite !== undefined && pessoas.length > limite
  const visiveis = precisaRecolher && !expandido ? pessoas.slice(0, limite) : pessoas
  const ocultos = pessoas.length - visiveis.length

  return (
    <section className={estilos.bloco}>
      <h3 className={estilos.titulo}>{titulo}</h3>
      <ul className={estilos.lista}>
        {visiveis.map((pessoa) => (
          <li key={pessoa.id} className={estilos.nome}>
            {pessoa.nome}
          </li>
        ))}
      </ul>
      {precisaRecolher && (
        <button
          type="button"
          className={estilos.alternar}
          onClick={() => setExpandido((atual) => !atual)}
        >
          {expandido ? 'Mostrar menos' : `Mostrar mais ${ocultos}`}
        </button>
      )}
    </section>
  )
}
