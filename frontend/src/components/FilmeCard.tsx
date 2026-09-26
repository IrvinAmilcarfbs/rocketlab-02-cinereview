import { Link } from 'react-router-dom'

import type { FilmeResumo } from '../api/tipos'
import { Estrelas } from './Estrelas'
import estilos from './FilmeCard.module.css'

interface Props {
  filme: FilmeResumo
}

const MAX_GENEROS = 2

export function FilmeCard({ filme }: Props) {
  const generos = filme.generos.slice(0, MAX_GENEROS)

  return (
    <Link to={`/filmes/${filme.id}`} className={estilos.card}>
      <div className={estilos.capa}>
        {filme.poster_url ? (
          <img
            src={filme.poster_url}
            alt={`Pôster de ${filme.titulo}`}
            loading="lazy"
            className={estilos.imagem}
          />
        ) : (
          // Parte relevante do catálogo não tem pôster; um espaço vazio quebraria
          // o alinhamento da grade.
          <div className={estilos.semCapa}>
            <span>{filme.titulo}</span>
          </div>
        )}
      </div>

      <div className={estilos.info}>
        <h3 className={estilos.titulo} title={filme.titulo}>
          {filme.titulo}
        </h3>
        <p className={estilos.ano}>{filme.ano ?? 'Ano desconhecido'}</p>

        {generos.length > 0 && (
          <ul className={estilos.generos}>
            {generos.map((genero) => (
              <li key={genero.id}>{genero.nome}</li>
            ))}
          </ul>
        )}

        <div className={estilos.avaliacao}>
          {filme.nota_media === null ? (
            // Ausência de avaliação é diferente de nota zero: mostrar estrelas
            // vazias sugeriria que o filme foi mal avaliado.
            <span className={estilos.semNota}>Sem avaliações</span>
          ) : (
            <>
              <Estrelas nota={filme.nota_media} />
              <span className={estilos.quantidade}>
                {filme.nota_media.toFixed(1)}
                <span className={estilos.separador}>·</span>
                {filme.qtd_avaliacoes}
              </span>
            </>
          )}
        </div>
      </div>
    </Link>
  )
}
