import { useState } from 'react'

import estilos from './SeletorEstrelas.module.css'

const CAMINHO_ESTRELA =
  'M12 2l2.9 6.26 6.6.72-4.9 4.6 1.35 6.42L12 16.9l-5.95 3.1L7.4 13.58 2.5 8.98l6.6-.72L12 2z'

/** Cada estrela vale dois pontos na escala 0–10 do banco. */
const NOTAS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

interface Props {
  /** Nota na escala 0–10; zero significa "ainda não escolhida". */
  valor: number
  onMudar: (nota: number) => void
}

/** Seletor de nota em cinco estrelas, com precisão de meia estrela.
 *
 * Cada estrela é composta de **duas** áreas clicáveis de meia largura, e cada
 * área é um `input type="radio"` invisível sobre o desenho. Escolher rádios em
 * vez de botões não é detalhe: um grupo de rádios já é navegável pelas setas do
 * teclado, anuncia "3 de 10 selecionado" ao leitor de tela e participa do
 * formulário — comportamento que, com botões, precisaria ser reimplementado à mão.
 *
 * O preenchimento é por largura percentual, como no componente de exibição, o
 * que permite recortar a estrela no meio em vez de usar um segundo ícone.
 */
export function SeletorEstrelas({ valor, onMudar }: Props) {
  // A pré-visualização segue o mouse sem alterar a escolha: o valor só muda no
  // clique. Nulo significa "não estou apontando nada".
  const [apontada, setApontada] = useState<number | null>(null)
  const exibida = apontada ?? valor
  const proporcao = Math.min(Math.max(exibida / 10, 0), 1)

  return (
    <div className={estilos.campo}>
      <div
        className={estilos.estrelas}
        onMouseLeave={() => setApontada(null)}
        role="radiogroup"
        aria-label="Nota"
      >
        <span className={estilos.trilha} aria-hidden="true">
          {[0, 1, 2, 3, 4].map((posicao) => (
            <svg key={posicao} className={estilos.icone} viewBox="0 0 24 24">
              <path d={CAMINHO_ESTRELA} />
            </svg>
          ))}
        </span>

        <span
          className={estilos.preenchida}
          style={{ width: `${proporcao * 100}%` }}
          aria-hidden="true"
        >
          {[0, 1, 2, 3, 4].map((posicao) => (
            <svg key={posicao} className={estilos.icone} viewBox="0 0 24 24">
              <path d={CAMINHO_ESTRELA} />
            </svg>
          ))}
        </span>

        <span className={estilos.alvos}>
          {NOTAS.map((nota) => (
            <label key={nota} className={estilos.alvo} onMouseEnter={() => setApontada(nota)}>
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
      </div>

      {/* O número ao lado dispensa contar estrelas e confirma a meia unidade,
          que é justamente o que o desenho representa de forma ambígua. */}
      <span className={valor ? estilos.leitura : estilos.leituraVazia}>
        {valor ? `${(valor / 2).toFixed(1)} de 5` : 'Escolha uma nota'}
      </span>
    </div>
  )
}
