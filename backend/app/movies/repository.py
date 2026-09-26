"""Consultas ao esquema estrela do catálogo.

Esta camada conhece o modelo dimensional e devolve entidades ORM. Traduzir isso
para o contrato da API é responsabilidade do serviço.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.movies.models import DimMovie, FactMoviePerformance


async def contar_filmes(sessao: AsyncSession) -> int:
    """Total de filmes exibíveis no catálogo.

    A contagem precisa descrever o mesmo conjunto que :func:`listar_filmes`
    devolve — ou seja, os filmes que possuem fato. Caso contrário, o total e a
    quantidade de páginas falariam de um catálogo diferente do percorrido.

    Contar diretamente o fato é equivalente a repetir aquele join interno, mas
    sem pagá-lo: ``sk_movie_id`` é a chave primária do fato e estrangeira para
    ``dim_movies``, então a integridade referencial já garante que todo fato tem
    filme. Medido no catálogo completo: 3,9 ms contra 175 ms do join.
    """

    consulta = select(func.count()).select_from(FactMoviePerformance)
    return await sessao.scalar(consulta) or 0


async def listar_filmes(sessao: AsyncSession, offset: int, limite: int) -> Sequence[DimMovie]:
    """Retorna uma página do catálogo ordenada por popularidade.

    Duas decisões de carregamento importam aqui:

    * ``genres`` usa ``selectinload``. Com ``joinedload``, o LIMIT recairia
      sobre as linhas do JOIN — um filme com três gêneros ocuparia três linhas —
      e a página voltaria incompleta. O ``selectinload`` emite uma segunda
      consulta com os IDs já paginados, preservando o corte.
    * ``reviews_summary`` é escalar (``uselist=False``), então ``joinedload`` é
      seguro e evita uma consulta adicional.

    O desempate por ``sk_movie_id`` não é decorativo: 86.372 filmes compartilham
    valor de popularidade, e sem um critério único a ordem entre eles fica
    indefinida — a paginação passaria a repetir e omitir registros.

    Duas escolhas atendem ao índice ``(popularidade, sk_movie_id)``:

    * O join é **interno**. Com ``LEFT OUTER JOIN`` o SQLite não pode reordenar
      as tabelas, parte de ``dim_movies`` e ordena as 95 mil linhas a cada
      página (medido: 319 ms contra 0,4 ms). O join interno o libera a começar
      pelo fato, percorrendo o índice já na ordem certa. Isso pressupõe que todo
      filme tenha linha no fato — hoje vale para 100% do catálogo, e o cadastro
      precisará criar as duas em conjunto.
    * Ambas as colunas são ordenadas de forma decrescente, para que o índice
      ascendente possa ser percorrido ao contrário. Em ordem mista sobraria uma
      ordenação temporária.
    """

    consulta = (
        select(DimMovie)
        .join(
            FactMoviePerformance,
            FactMoviePerformance.sk_movie_id == DimMovie.sk_movie_id,
        )
        .options(
            selectinload(DimMovie.genres),
            joinedload(DimMovie.reviews_summary),
        )
        .order_by(
            FactMoviePerformance.popularidade.desc(),
            FactMoviePerformance.sk_movie_id.desc(),
        )
        .offset(offset)
        .limit(limite)
    )
    return (await sessao.scalars(consulta)).all()
