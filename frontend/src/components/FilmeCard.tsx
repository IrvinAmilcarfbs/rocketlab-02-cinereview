import { Link } from 'react-router-dom'

import type { FilmeResumo } from '../api/tipos'
import { Estrelas } from './Estrelas'
import estilos from './FilmeCard.module.css'

interface Props {
  filme: FilmeResumo
}

/** Deriva um matiz estável do identificador do filme.
 *
 * 8,6% do catálogo não tem pôster, e uma parede de retângulos idênticos parece
 * defeito. Dando a cada ausência uma cor própria — sempre a mesma para o mesmo
 * filme, porque vem do id — a lacuna passa a parecer intencional, e ainda ajuda
 * a distinguir um cartão do outro ao percorrer a grade.
 */
function matiz(id: string): number {
  let acumulado = 0
  for (const letra of id) {
    acumulado = (acumulado * 31 + letra.charCodeAt(0)) % 360
  }
  return acumulado
}

/** Cartão do catálogo: o pôster é o cartão.
 *
 * A informação textual fica sobre o pôster e só aparece no ponteiro ou no foco.
 * A razão não é imitar streaming: é que gêneros e notas têm comprimentos
 * diferentes, e mantê-los no fluxo fazia cada cartão terminar numa altura
 * própria — a fileira inteira ficava serrilhada. Fora do fluxo, todo cartão é
 * exatamente um pôster, e a grade fica regular por construção.
 *
 * Duas situações quebram essa regra e são tratadas à parte: um filme **sem
 * pôster** não tem o que revelar, então o título é exibido sempre; e em telas
 * sem ponteiro não existe hover, então a faixa de informação fica permanente
 * (ver a media query `hover: none`).
 */
export function FilmeCard({ filme }: Props) {
  const semPoster = !filme.poster_url

  return (
    <Link
      to={`/filmes/${filme.id}`}
      className={estilos.cartao}
      aria-label={`${filme.titulo}${filme.ano ? `, ${filme.ano}` : ''}`}
    >
      {semPoster ? (
        <div
          className={estilos.capaVazia}
          style={{ '--matiz': matiz(filme.id) } as React.CSSProperties}
        >
          <svg className={estilos.marca} viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm1 2v2h2V5H5zm12 0v2h2V5h-2zM5 9v2h2V9H5zm12 0v2h2V9h-2zM5 13v2h2v-2H5zm12 0v2h2v-2h-2zM5 17v2h2v-2H5zm12 0v2h2v-2h-2zM9 5v14h6V5H9z" />
          </svg>
          <span className={estilos.tituloSemCapa}>{filme.titulo}</span>
        </div>
      ) : (
        <img
          src={filme.poster_url ?? ''}
          alt=""
          loading="lazy"
          className={estilos.imagem}
        />
      )}

      {/* `aria-hidden` porque o link já carrega o mesmo texto em `aria-label`:
          sem isso o leitor de tela anunciaria título e ano duas vezes. */}
      <div className={estilos.info} aria-hidden="true">
        <h3 className={estilos.titulo}>{filme.titulo}</h3>

        <div className={estilos.linha}>
          <span className={estilos.ano}>{filme.ano ?? '—'}</span>

          {filme.nota_media !== null && (
            <span className={estilos.nota}>
              <Estrelas nota={filme.nota_media} />
              <span className={estilos.valor}>{filme.nota_media.toFixed(1)}</span>
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}
