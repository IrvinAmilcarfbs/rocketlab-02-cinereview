import { useState } from 'react'

import { FilaEstrelas } from './FilaEstrelas'
import estilos from './SeletorEstrelas.module.css'

const POSICOES = [0, 1, 2, 3, 4]

interface Props {
  /** Nota na escala 0–10; zero significa "ainda não escolhida". */
  valor: number
  onMudar: (nota: number) => void
}

/** Seletor de nota em cinco estrelas, com precisão de meia estrela.
 *
 * Cada estrela tem **duas** áreas clicáveis, e cada área é um
 * `input type="radio"` invisível sobre o desenho. Escolher rádios em vez de
 * botões não é detalhe: um grupo de rádios já é navegável pelas setas do teclado,
 * anuncia "3 de 10 selecionado" ao leitor de tela e participa do formulário —
 * comportamento que, com botões, precisaria ser reimplementado à mão.
 *
 * Os alvos são agrupados **por estrela**, e não distribuídos igualmente pela
 * fila. É o mesmo motivo que vale para o preenchimento (ver `FilaEstrelas`): dez
 * alvos iguais sobre a largura total não coincidiriam com as metades desenhadas,
 * porque a fila inclui os vãos entre as estrelas.
 */
export function SeletorEstrelas({ valor, onMudar }: Props) {
  // A nota apontada pelo mouse é separada da escolhida: o valor só muda no
  // clique. Nulo significa "não estou apontando nada".
  const [apontada, setApontada] = useState<number | null>(null)
  const exibida = apontada ?? valor

  return (
    <div className={estilos.campo}>
      <div
        className={estilos.estrelas}
        onMouseLeave={() => setApontada(null)}
        role="radiogroup"
        aria-label="Nota"
      >
        <FilaEstrelas nota={exibida} />

        <span className={estilos.alvos}>
          {POSICOES.map((indice) => (
            <span key={indice} className={estilos.par}>
              {[indice * 2 + 1, indice * 2 + 2].map((nota) => (
                <label
                  key={nota}
                  className={estilos.alvo}
                  onMouseEnter={() => setApontada(nota)}
                >
                  <input
                    type="radio"
                    name="nota"
                    className={estilos.radio}
                    checked={valor === nota}
                    onChange={() => onMudar(nota)}
                  />
                  <span className={estilos.apenasLeitor}>{nota / 2} de 5 estrelas</span>
                </label>
              ))}
            </span>
          ))}
        </span>
      </div>

      {/* O número ao lado dispensa contar estrelas e confirma a meia unidade,
          que é justamente o que o desenho representa de forma ambígua. */}
      <span className={valor ? estilos.leitura : estilos.leituraVazia}>
        {valor ? `${(valor / 2).toFixed(1)} de 5` : 'Escolha uma nota'}
      </span>
    </div>
  )
}
