"""Fixtures compartilhadas pelos testes que tocam o banco.

Cada teste roda contra um SQLite em memória criado do zero. O ``StaticPool`` é
necessário porque um banco ``:memory:`` pertence à conexão que o abriu — sem ele,
cada conexão do pool enxergaria um banco vazio e diferente.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import enable_sqlite_foreign_keys, get_db
from app.main import app
from app.movies import models


@pytest.fixture
async def sessao() -> AsyncIterator[AsyncSession]:
    """Sessão ligada a um banco em memória com o schema recém-criado."""

    motor = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    # Mesmo pragma que a aplicação aplica em cada conexão. Sem ele o banco de
    # teste ignora ON DELETE CASCADE, e uma remoção deixaria fato, agregado,
    # avaliações e vínculos órfãos sem que nenhum teste percebesse — o ambiente
    # de teste diria "passou" sobre um comportamento que produção não tem.
    enable_sqlite_foreign_keys(motor)
    async with motor.begin() as conexao:
        await conexao.run_sync(Base.metadata.create_all)

    fabrica = async_sessionmaker(bind=motor, expire_on_commit=False)
    async with fabrica() as aberta:
        yield aberta

    await motor.dispose()


@pytest.fixture
async def cliente(sessao: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP com a dependência de banco apontada para a sessão de teste."""

    async def sobrepor_get_db() -> AsyncIterator[AsyncSession]:
        yield sessao

    app.dependency_overrides[get_db] = sobrepor_get_db
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as aberto:
        yield aberto
    app.dependency_overrides.clear()


async def criar_filme(
    sessao: AsyncSession,
    *,
    titulo: str,
    popularidade: float | None,
    generos: tuple[str, ...] = (),
    pessoas: tuple[tuple[str, str], ...] = (),
    produtoras: tuple[str, ...] = (),
    nota_media: float | None = None,
    qtd_avaliacoes: int = 0,
    com_fato: bool = True,
    criado_em: datetime | None = None,
) -> models.DimMovie:
    """Cria um filme com suas relações, refletindo o que a carga produz.

    ``pessoas`` recebe pares ``(nome, tipo_pessoa)``, como na base real, onde o
    papel mora na dimensão e não na bridge.

    ``com_fato=False`` simula o caso em que o fato não foi gravado, que o
    catálogo deliberadamente não exibe.
    """

    filme = models.DimMovie(
        # Título não serve como identificador: os testes de agrupamento criam
        # vários filmes homônimos de propósito, e `id_filme` é único.
        id_filme=uuid4().hex,
        titulo=titulo,
        ano_lancamento=2024,
        url_poster=f"https://exemplo/{titulo}.jpg",
        # Nulo reproduz o acervo carregado; preenchido, um filme cadastrado aqui.
        # Os testes de ordenação passam o instante de propósito: dois cadastros
        # no mesmo microssegundo desempatariam pela chave, que é aleatória.
        criado_em=criado_em,
    )
    for nome in generos:
        existente = await sessao.get(models.DimGenre, nome)
        filme.genres.append(existente or models.DimGenre(sk_genre_id=nome, nome_genero=nome))

    for nome, tipo in pessoas:
        chave = f"{nome}-{tipo}"
        existente = await sessao.get(models.DimPerson, chave)
        filme.people.append(
            existente or models.DimPerson(sk_person_id=chave, nome_pessoa=nome, tipo_pessoa=tipo)
        )

    for nome in produtoras:
        existente = await sessao.get(models.DimCompany, nome)
        filme.companies.append(
            existente or models.DimCompany(sk_company_id=nome, nome_produtora=nome)
        )

    if com_fato:
        filme.performance = models.FactMoviePerformance(popularidade=popularidade)
    if qtd_avaliacoes:
        filme.reviews_summary = models.DimReview(
            qtd_avaliacoes_usuarios=qtd_avaliacoes, nota_media_usuarios=nota_media
        )

    sessao.add(filme)
    await sessao.commit()
    return filme


async def criar_generos(sessao: AsyncSession, *nomes: str) -> list[models.DimGenre]:
    """Popula o vocabulário fechado de gêneros.

    O banco em memória nasce vazio, e o cadastro recusa gêneros que não existem
    na dimensão — então os testes de escrita precisam declarar o vocabulário que
    vão usar.
    """

    generos = [models.DimGenre(sk_genre_id=nome, nome_genero=nome) for nome in nomes]
    sessao.add_all(generos)
    await sessao.commit()
    return generos


async def criar_avaliacoes(
    sessao: AsyncSession, filme: models.DimMovie, quantidade: int
) -> list[models.MovieReview]:
    """Cria avaliações para um filme, todas no mesmo instante.

    Reproduz de propósito a condição da carga real, em que as 43.666 avaliações
    importadas compartilham apenas dois valores de ``created_at`` — é o cenário
    que exige desempate pela chave na ordenação.
    """

    avaliacoes = [
        models.MovieReview(
            sk_movie_review_id=f"{filme.sk_movie_id}-{indice}",
            sk_movie_id=filme.sk_movie_id,
            nome=f"Avaliador {indice}",
            nota=float(indice % 11),
            comentario=f"Comentário {indice}",
        )
        for indice in range(quantidade)
    ]
    sessao.add_all(avaliacoes)
    await sessao.commit()
    return avaliacoes
