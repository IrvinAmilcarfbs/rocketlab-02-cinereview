"""Consultas ao esquema estrela do catálogo.

Esta camada conhece o modelo dimensional e devolve entidades ORM. Traduzir isso
para o contrato da API é responsabilidade do serviço.
"""

from collections.abc import Sequence

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.movies.models import DimMovie, FactMoviePerformance, MovieReview


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


async def obter_filme(sessao: AsyncSession, filme_id: str) -> DimMovie | None:
    """Carrega um filme com tudo que a ficha completa precisa.

    Todas as coleções usam ``selectinload``, e aqui o motivo é o oposto do que
    vale na listagem. Sem LIMIT, o risco não é o corte cair no lugar errado, e
    sim o produto cartesiano: carregar gêneros, pessoas e produtoras por JOIN na
    mesma consulta faria o banco devolver todas as combinações entre elas. Um
    filme com 3 gêneros, 150 pessoas e 2 produtoras renderia 900 linhas para
    exibir um único registro.

    ``performance`` e ``reviews_summary`` são escalares, então ``joinedload``
    é adequado e evita consultas extras.
    """

    consulta = (
        select(DimMovie)
        .where(DimMovie.sk_movie_id == filme_id)
        .options(
            selectinload(DimMovie.genres),
            selectinload(DimMovie.people),
            selectinload(DimMovie.companies),
            joinedload(DimMovie.performance),
            joinedload(DimMovie.reviews_summary),
        )
    )
    return await sessao.scalar(consulta)


async def filme_existe(sessao: AsyncSession, filme_id: str) -> bool:
    """Confirma a existência do filme sem carregar suas relações."""

    consulta = select(DimMovie.sk_movie_id).where(DimMovie.sk_movie_id == filme_id)
    return await sessao.scalar(consulta) is not None


async def contar_avaliacoes(sessao: AsyncSession, filme_id: str) -> int:
    consulta = (
        select(func.count()).select_from(MovieReview).where(MovieReview.sk_movie_id == filme_id)
    )
    return await sessao.scalar(consulta) or 0


async def listar_avaliacoes(
    sessao: AsyncSession, filme_id: str, offset: int, limite: int
) -> Sequence[MovieReview]:
    """Lista uma página de avaliações, da mais recente para a mais antiga.

    O desempate pela chave é ainda mais necessário aqui do que no catálogo: como
    a carga inicial grava todas as linhas na mesma transação, as 43.666
    avaliações importadas compartilham apenas dois valores de ``created_at``.
    Ordenar só pela data deixaria a ordem praticamente indefinida.
    """

    consulta = (
        select(MovieReview)
        .where(MovieReview.sk_movie_id == filme_id)
        .order_by(
            MovieReview.created_at.desc(),
            MovieReview.sk_movie_review_id.desc(),
        )
        .offset(offset)
        .limit(limite)
    )
    return (await sessao.scalars(consulta)).all()


ESCAPE_LIKE = "!"


def _escapar_like(termo: str) -> str:
    """Neutraliza os curingas do LIKE dentro do texto digitado.

    Sem isto, buscar por "100%" faria o ``%`` valer como curinga e casar com
    praticamente tudo; ``_`` casaria com qualquer caractere.

    O caractere de escape é ``!`` em vez da barra invertida habitual: a barra
    precisaria ser escapada na string Python e de novo no literal SQL, o que
    torna fácil escrever algo que o banco recebe errado.
    """

    return (
        termo.replace(ESCAPE_LIKE, ESCAPE_LIKE * 2)
        .replace("%", f"{ESCAPE_LIKE}%")
        .replace("_", f"{ESCAPE_LIKE}_")
    )


# A busca é escrita em SQL explícito por causa de uma única palavra: MATERIALIZED.
#
# O catálogo tem 12.165 linhas com título repetido — "Die Hart 2: Die Harter"
# aparece 30 vezes, com identificadores distintos vindos do TMDB. Para não
# devolver dezenas de cards idênticos, ROW_NUMBER numera as linhas dentro de
# cada grupo de título, ano e duração, e a busca fica com a primeira de cada.
#
# Sem MATERIALIZED, o SQLite embute a subconsulta no plano externo e decide
# percorrer o índice de popularidade do fato inteiro — 95 mil linhas — antes de
# aplicar o filtro. Medido: 531 ms contra 41 ms. A palavra-chave o obriga a
# calcular os candidatos primeiro, que é o conjunto pequeno.
#
# `HasCTE.cte()` não expõe essa dica, e as alternativas medidas foram piores:
# NOT EXISTS correlacionado custou 187–388 ms e agrupar em Python, ~520 ms.
_CANDIDATOS = """
    WITH candidatos AS MATERIALIZED (
        SELECT
            m.sk_movie_id AS sk_movie_id,
            m.titulo AS titulo,
            m.ano_lancamento AS ano_lancamento,
            m.duracao_minutos AS duracao_minutos,
            f.popularidade AS popularidade
        FROM dim_movies AS m
        JOIN fact_movies_performance AS f ON f.sk_movie_id = m.sk_movie_id
        WHERE m.titulo_busca LIKE :padrao ESCAPE '!'
    ),
    representantes AS (
        SELECT
            sk_movie_id,
            popularidade,
            ROW_NUMBER() OVER (
                PARTITION BY titulo, ano_lancamento, duracao_minutos
                ORDER BY popularidade DESC, sk_movie_id DESC
            ) AS posicao
        FROM candidatos
    )
"""

CONTAR_BUSCA = text(_CANDIDATOS + "SELECT COUNT(*) FROM representantes WHERE posicao = 1")

BUSCAR_IDS = text(
    _CANDIDATOS
    + """
    SELECT sk_movie_id FROM representantes
    WHERE posicao = 1
    ORDER BY popularidade DESC, sk_movie_id DESC
    LIMIT :limite OFFSET :offset
    """
)


async def contar_busca(sessao: AsyncSession, termo: str) -> int:
    """Conta os grupos encontrados, e não as linhas — o mesmo que a busca exibe."""

    padrao = f"%{_escapar_like(termo)}%"
    return await sessao.scalar(CONTAR_BUSCA, {"padrao": padrao}) or 0


async def buscar_filmes(
    sessao: AsyncSession, termo: str, offset: int, limite: int
) -> Sequence[DimMovie]:
    """Busca por título, sem títulos repetidos, ordenada por popularidade.

    A consulta em SQL devolve apenas as chaves; as entidades são carregadas em
    seguida pelo ORM, o que mantém o mesmo carregamento de relações usado no
    catálogo. A ordem vinda do SQL é restaurada ao final, porque um `IN` não
    garante ordem alguma.
    """

    ids = (
        await sessao.scalars(
            BUSCAR_IDS,
            {"padrao": f"%{_escapar_like(termo)}%", "limite": limite, "offset": offset},
        )
    ).all()
    if not ids:
        return []

    consulta = (
        select(DimMovie)
        .where(DimMovie.sk_movie_id.in_(ids))
        .options(
            selectinload(DimMovie.genres),
            joinedload(DimMovie.reviews_summary),
        )
    )
    encontrados = {filme.sk_movie_id: filme for filme in (await sessao.scalars(consulta)).all()}
    return [encontrados[chave] for chave in ids if chave in encontrados]
