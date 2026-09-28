import { IconeEstrela } from './IconeEstrela'
import estilos from './FilaEstrelas.module.css'

const POSICOES = [0, 1, 2, 3, 4]

interface Props {
  /** Nota na escala 0–10 usada pelo backend. Cada estrela vale dois pontos. */
  nota: number
}

/** Desenha cinco estrelas preenchidas até a fração indicada pela nota.
 *
 * Duas decisões de geometria sustentam isto, e cada uma corrige um defeito real.
 *
 * **A fração é calculada por estrela, não sobre a fila.** A fila mede cinco
 * caixas mais os vãos, enquanto as estrelas avançam de caixa + vão em caixa +
 * vão. Uma porcentagem sobre o total erra em toda posição fracionária, e o erro
 * troca de sinal ao longo da fila: as primeiras metades saem grandes demais e as
 * últimas, pequenas demais. Com cada estrela resolvendo a si mesma, 50% de uma
 * caixa é o centro daquela caixa — que é onde a tinta da estrela também está
 * centrada.
 *
 * **O corte é `clip-path`, e não um pai estreito com `overflow: hidden`.** A
 * folha global aplica `max-width: 100%` a todo `svg`, o que é correto para
 * imagens responsivas e destrutivo aqui: dentro de um pai estreito, o ícone não
 * é cortado — ele é **limitado**, e um SVG com `viewBox` responde a isso
 * escalando o desenho para caber. O resultado era uma estrela inteira menor no
 * lugar de metade de uma estrela. Com `clip-path`, a camada mantém o tamanho
 * cheio e o recorte acontece depois do desenho, sem nunca tocar na largura.
 */
export function FilaEstrelas({ nota }: Props) {
  const limitada = Math.min(Math.max(nota, 0), 10)

  return (
    <span className={estilos.fila} aria-hidden="true">
      {POSICOES.map((indice) => {
        const fracao = Math.min(Math.max(limitada / 2 - indice, 0), 1)

        return (
          <span key={indice} className={estilos.estrela}>
            <IconeEstrela className={estilos.vazia} />
            {fracao > 0 && (
              <span
                className={estilos.parte}
                // `inset(0 R 0 0)` recorta R da direita: para meia estrela, R é
                // 50% da caixa, que são exatamente os seus pixels centrais.
                style={{ clipPath: `inset(0 ${(1 - fracao) * 100}% 0 0)` }}
              >
                <IconeEstrela className={estilos.cheia} />
              </span>
            )}
          </span>
        )
      })}
    </span>
  )
}
