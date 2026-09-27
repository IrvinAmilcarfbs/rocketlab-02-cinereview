"""Consultas ao esquema estrela do catálogo.

Esta camada conhece o modelo dimensional e devolve entidades ORM. Traduzir isso
para o contrato da API é responsabilidade do serviço.
"""

from collections.abc import Sequence

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.movies.models import (
    DimGenre,
    DimMovie,
    DimPerson,
    FactMoviePerformance,
    MovieReview,
    PersonType,
    generate_surrogate_key,
)


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


async def listar_filmes(
    sessao: AsyncSession, offset: int, limite: int, *, somente_acervo: bool = False
) -> Sequence[DimMovie]:
    """Retorna uma página do catálogo ordenada por popularidade.

    ``somente_acervo`` exclui os filmes cadastrados pela aplicação. Serve à
    ordenação por recentes, que os exibe antes desta lista e não pode repeti-los
    aqui.

    A exclusão é escrita como ``NOT IN`` sobre a chave do **fato**, e não como
    ``WHERE dim_movies.criado_em IS NULL``, porque a diferença é grande no fim do
    catálogo. O filtro na dimensão obriga a consultar a tabela ``dim_movies``
    linha a linha e desfaz o índice coberto; o ``NOT IN`` deixa o SQLite
    materializar a lista uma única vez, pelo índice parcial, e comparar contra a
    chave que ele já tem em mãos. Medido na página 4.782: 174 ms contra 497 ms,
    frente aos 173 ms da consulta sem filtro algum.

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
    if somente_acervo:
        # `sk_movie_id` é chave primária, portanto nunca nula. Isso importa mais
        # do que parece: um único nulo na subconsulta faria `NOT IN` avaliar para
        # nulo em toda linha, e o catálogo voltaria vazio sem erro nenhum.
        cadastrados = select(DimMovie.sk_movie_id).where(DimMovie.criado_em.is_not(None))
        consulta = consulta.where(FactMoviePerformance.sk_movie_id.not_in(cadastrados))
    return (await sessao.scalars(consulta)).all()


async def contar_cadastrados(sessao: AsyncSession) -> int:
    """Quantos filmes foram cadastrados pela aplicação.

    O join com o fato não é decorativo: este número define o deslocamento entre
    os dois blocos da ordenação por recentes. Se contasse filmes que a listagem
    não exibe, a paginação passaria a pular ou repetir um registro na fronteira.
    """

    consulta = (
        select(func.count())
        .select_from(DimMovie)
        .join(FactMoviePerformance, FactMoviePerformance.sk_movie_id == DimMovie.sk_movie_id)
        .where(DimMovie.criado_em.is_not(None))
    )
    return await sessao.scalar(consulta) or 0


async def listar_cadastrados(sessao: AsyncSession, offset: int, limite: int) -> Sequence[DimMovie]:
    """Filmes cadastrados aqui, do mais recente para o mais antigo.

    O índice parcial ``(criado_em, sk_movie_id)`` atende esta ordenação por
    varredura reversa, sem ordenação temporária — o SQLite traduz o
    ``IS NOT NULL`` em uma busca por faixa dentro do índice.

    O desempate por ``sk_movie_id`` cobre dois cadastros no mesmo instante: sem
    ordem total, a paginação voltaria a ser indefinida entre eles.
    """

    consulta = (
        select(DimMovie)
        .join(FactMoviePerformance, FactMoviePerformance.sk_movie_id == DimMovie.sk_movie_id)
        .where(DimMovie.criado_em.is_not(None))
        .options(
            selectinload(DimMovie.genres),
            joinedload(DimMovie.reviews_summary),
        )
        .order_by(DimMovie.criado_em.desc(), DimMovie.sk_movie_id.desc())
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
# O catálogo tem 12.165 linhas com título repetido — "die hart" casa com 61
# registros, todos com id_filme distinto vindo do TMDB, porque a base de origem
# guarda entradas duplicadas do mesmo filme que ninguém mesclou. Para não
# devolver dezenas de cards idênticos, ROW_NUMBER numera as linhas dentro de
# cada grupo e a busca fica com a primeira de cada.
#
# O grupo é (titulo_chave, ano, duração). A chave ignora pontuação porque as
# grafias divergem justamente nela ("Die Hart 2: Die Harter" e "Die Hart 2 :
# Die Harter"): isso funde 181 grupos no catálogo, e "die hart" cai de 12 para
# 10 resultados. A duração fica na chave de propósito — sem ela seriam 5
# resultados, mas 752 grupos do catálogo passariam a fundir durações reais
# diferentes, juntando o curta e o longa que compartilham título e ano.
#
# Sem MATERIALIZED, o SQLite embute a subconsulta no plano externo e decide
# percorrer o índice de popularidade do fato inteiro — 95 mil linhas — antes de
# aplicar o filtro. Medido: 531 ms contra 41 ms. A palavra-chave o obriga a
# calcular os candidatos primeiro, que é o conjunto pequeno.
#
# `HasCTE.cte()` não expõe essa dica, e as alternativas medidas foram piores:
# NOT EXISTS correlacionado custou 187–388 ms e agrupar em Python, ~520 ms.
#
# Dentro do grupo, o representante é o registro mais completo, e só depois o mais
# popular: entre irmãos idênticos o TMDB costuma ter um preenchido e outros em
# branco, e eleger pela popularidade sozinha exibia cards sem sinopse nem pôster
# tendo o mesmo filme completo ao lado. "Sem descrição" é o texto que a base de
# origem grava no lugar de uma sinopse ausente.
_CANDIDATOS = """
    WITH candidatos AS MATERIALIZED (
        SELECT
            m.sk_movie_id AS sk_movie_id,
            m.titulo_chave AS titulo_chave,
            m.ano_lancamento AS ano_lancamento,
            m.duracao_minutos AS duracao_minutos,
            f.popularidade AS popularidade,
            (COALESCE(m.duracao_minutos, 0) > 0)
                + (m.url_poster IS NOT NULL)
                + (COALESCE(m.sinopse, '') NOT IN ('', 'Sem descrição')) AS completude
        FROM dim_movies AS m
        JOIN fact_movies_performance AS f ON f.sk_movie_id = m.sk_movie_id
        WHERE m.titulo_busca LIKE :padrao ESCAPE '!'
    ),
    representantes AS (
        SELECT
            sk_movie_id,
            popularidade,
            ROW_NUMBER() OVER (
                PARTITION BY titulo_chave, ano_lancamento, duracao_minutos
                ORDER BY completude DESC, popularidade DESC, sk_movie_id DESC
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


async def listar_generos(sessao: AsyncSession) -> Sequence[DimGenre]:
    """Vocabulário de gêneros, em ordem alfabética.

    São 19 valores fechados, vindos dos CSVs. O formulário precisa deles para
    oferecer uma escolha em vez de um campo livre — texto livre criaria "Ação"
    ao lado de "Action" e duplicaria a dimensão.
    """

    return (await sessao.scalars(select(DimGenre).order_by(DimGenre.nome_genero))).all()


async def buscar_generos_por_nome(sessao: AsyncSession, nomes: Sequence[str]) -> list[DimGenre]:
    """Resolve nomes de gênero em entidades, na ordem em que foram pedidos.

    Nomes desconhecidos simplesmente não aparecem no resultado. Quem chama
    compara as quantidades e decide o que fazer — o repositório não conhece o
    contrato HTTP.
    """

    if not nomes:
        return []

    encontrados = (
        await sessao.scalars(select(DimGenre).where(DimGenre.nome_genero.in_(nomes)))
    ).all()
    por_nome = {genero.nome_genero: genero for genero in encontrados}
    return [por_nome[nome] for nome in nomes if nome in por_nome]


async def obter_ou_criar_pessoa(sessao: AsyncSession, nome: str, tipo: PersonType) -> DimPerson:
    """Reaproveita a pessoa existente ou cria uma nova.

    ``(nome_pessoa, tipo_pessoa)`` é UNIQUE, e é isso que impede a dimensão de
    duplicar: digitar um diretor que já existe entre os 65.200 cadastrados
    reaproveita a linha em vez de criar uma segunda.

    A inserção usa ``ON CONFLICT DO NOTHING`` em vez de inserir e tratar o erro.
    Entre o SELECT e a escrita, outra requisição pode criar a mesma pessoa; um
    ``IntegrityError`` aqui derrubaria a transação inteira do cadastro, e o
    filme não seria gravado por causa de um diretor homônimo.
    """

    consulta = select(DimPerson).where(DimPerson.nome_pessoa == nome, DimPerson.tipo_pessoa == tipo)
    pessoa = await sessao.scalar(consulta)
    if pessoa is not None:
        return pessoa

    await sessao.execute(
        sqlite_insert(DimPerson)
        .values(
            sk_person_id=generate_surrogate_key(),
            nome_pessoa=nome,
            tipo_pessoa=tipo,
        )
        .on_conflict_do_nothing(index_elements=["nome_pessoa", "tipo_pessoa"])
    )
    pessoa = await sessao.scalar(consulta)
    if pessoa is None:  # pragma: no cover - só ocorreria com a UNIQUE ausente
        raise RuntimeError(f"Não foi possível obter a pessoa {nome!r} ({tipo}).")
    return pessoa


async def obter_filme_para_edicao(sessao: AsyncSession, filme_id: str) -> DimMovie | None:
    """Carrega o filme com as coleções que a atualização substitui.

    Só gêneros e pessoas vêm carregados. Substituir uma coleção exige conhecer o
    conteúdo atual — sem isso o SQLAlchemy não sabe quais vínculos apagar — e as
    demais relações não são tocadas pela atualização.
    """

    consulta = (
        select(DimMovie)
        .where(DimMovie.sk_movie_id == filme_id)
        .options(selectinload(DimMovie.genres), selectinload(DimMovie.people))
    )
    return await sessao.scalar(consulta)


async def gravar_filme(sessao: AsyncSession, filme: DimMovie) -> None:
    """Persiste um filme novo com tudo que pende na sessão, numa transação.

    O filme chega montado com fato, gêneros e diretores. As cinco tabelas são
    gravadas no mesmo commit: um cadastro parcial deixaria um filme fora do
    catálogo ou um vínculo apontando para o vazio.
    """

    sessao.add(filme)
    await sessao.commit()


async def confirmar(sessao: AsyncSession) -> None:
    """Fecha a transação de uma atualização já aplicada às entidades."""

    await sessao.commit()


async def remover_filme(sessao: AsyncSession, filme_id: str) -> bool:
    """Apaga o filme e tudo que depende dele. Devolve se havia o que apagar.

    Uma única instrução basta: as chaves estrangeiras usam ``ON DELETE CASCADE``
    e o ``PRAGMA foreign_keys=ON`` está ligado em cada conexão, então o próprio
    banco remove as bridges, o fato, o agregado e as avaliações. Carregar o grafo
    no ORM para apagá-lo em Python seria mais lento e mais frágil.
    """

    resultado = await sessao.execute(delete(DimMovie).where(DimMovie.sk_movie_id == filme_id))
    await sessao.commit()
    return resultado.rowcount > 0
