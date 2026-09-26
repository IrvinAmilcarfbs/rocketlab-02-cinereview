"""Fixtures compartilhadas pelos testes que tocam o banco.

Cada teste roda contra um SQLite em memória criado do zero. O ``StaticPool`` é
necessário porque um banco ``:memory:`` pertence à conexão que o abriu — sem ele,
cada conexão do pool enxergaria um banco vazio e diferente.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
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
    nota_media: float | None = None,
    qtd_avaliacoes: int = 0,
    com_fato: bool = True,
) -> models.DimMovie:
    """Cria um filme com suas relações, refletindo o que a carga produz.

    ``com_fato=False`` simula o caso em que o fato não foi gravado, que o
    catálogo deliberadamente não exibe.
    """

    filme = models.DimMovie(
        id_filme=f"id-{titulo}",
        titulo=titulo,
        ano_lancamento=2024,
        url_poster=f"https://exemplo/{titulo}.jpg",
    )
    for nome in generos:
        existente = await sessao.get(models.DimGenre, nome)
        filme.genres.append(existente or models.DimGenre(sk_genre_id=nome, nome_genero=nome))

    if com_fato:
        filme.performance = models.FactMoviePerformance(popularidade=popularidade)
    if qtd_avaliacoes:
        filme.reviews_summary = models.DimReview(
            qtd_avaliacoes_usuarios=qtd_avaliacoes, nota_media_usuarios=nota_media
        )

    sessao.add(filme)
    await sessao.commit()
    return filme
