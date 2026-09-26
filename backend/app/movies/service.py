"""Regras do catálogo e tradução do esquema estrela para o contrato da API.

Esta camada é a fronteira entre os dois modelos. O banco guarda um filme
espalhado por dimensões e bridges; a API entrega um recurso plano. Concentrar a
tradução aqui evita que o formato do banco vaze para o contrato — e que uma
mudança no contrato exija mexer nas consultas.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagina, ParametrosPaginacao
from app.movies import repository
from app.movies.models import DimMovie
from app.movies.schemas import FilmeResumo, GeneroResumo


def para_resumo(filme: DimMovie) -> FilmeResumo:
    """Achata um filme do esquema estrela no item exibido no catálogo."""

    agregado = filme.reviews_summary
    return FilmeResumo(
        id=filme.sk_movie_id,
        titulo=filme.titulo,
        ano=filme.ano_lancamento,
        poster_url=filme.url_poster,
        generos=[
            GeneroResumo(id=genero.sk_genre_id, nome=genero.nome_genero) for genero in filme.genres
        ],
        # Filmes sem avaliação não têm linha no agregado: a média vira nula, que
        # é diferente de zero — "sem informação" não é "todos detestaram".
        nota_media=agregado.nota_media_usuarios if agregado else None,
        qtd_avaliacoes=agregado.qtd_avaliacoes_usuarios if agregado else 0,
    )


async def listar_catalogo(
    sessao: AsyncSession, parametros: ParametrosPaginacao
) -> Pagina[FilmeResumo]:
    """Monta uma página do catálogo."""

    total = await repository.contar_filmes(sessao)
    filmes = await repository.listar_filmes(sessao, parametros.offset, parametros.tamanho)
    return Pagina.montar([para_resumo(filme) for filme in filmes], total, parametros)
