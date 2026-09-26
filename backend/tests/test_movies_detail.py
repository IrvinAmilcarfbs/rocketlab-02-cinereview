"""Testes da ficha do filme e da listagem de avaliações."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import criar_avaliacoes, criar_filme

ROTA = "/api/v1/movies"


async def test_detalhe_separa_pessoas_por_papel(cliente: AsyncClient, sessao: AsyncSession) -> None:
    """O papel mora em `dim_people`, não na bridge: o serviço é quem separa."""

    filme = await criar_filme(
        sessao,
        titulo="Cidade de Deus",
        popularidade=10.0,
        generos=("Drama",),
        produtoras=("O2 Filmes",),
        pessoas=(
            ("Fernando Meirelles", "Diretor"),
            ("Katia Lund", "Diretor"),
            ("Braulio Mantovani", "Roteirista"),
            ("Alexandre Rodrigues", "Ator"),
            ("Leandro Firmino", "Ator"),
        ),
    )

    corpo = (await cliente.get(f"{ROTA}/{filme.sk_movie_id}")).json()

    assert [pessoa["nome"] for pessoa in corpo["diretores"]] == [
        "Fernando Meirelles",
        "Katia Lund",
    ]
    assert [pessoa["nome"] for pessoa in corpo["roteiristas"]] == ["Braulio Mantovani"]
    assert [pessoa["nome"] for pessoa in corpo["elenco"]] == [
        "Alexandre Rodrigues",
        "Leandro Firmino",
    ]
    assert [produtora["nome"] for produtora in corpo["produtoras"]] == ["O2 Filmes"]
    assert [genero["nome"] for genero in corpo["generos"]] == ["Drama"]


async def test_detalhe_de_filme_inexistente_responde_404(cliente: AsyncClient) -> None:
    resposta = await cliente.get(f"{ROTA}/inexistente")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Filme não encontrado."


async def test_detalhe_sem_avaliacao_traz_media_nula(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    filme = await criar_filme(sessao, titulo="Sem avaliacao", popularidade=1.0)

    corpo = (await cliente.get(f"{ROTA}/{filme.sk_movie_id}")).json()

    assert corpo["nota_media"] is None
    assert corpo["qtd_avaliacoes"] == 0
    assert corpo["elenco"] == []


async def test_avaliacoes_paginam_sem_repetir_com_data_identica(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Todas as avaliações compartilham `created_at`, como na carga real."""

    filme = await criar_filme(sessao, titulo="Muito avaliado", popularidade=5.0)
    await criar_avaliacoes(sessao, filme, quantidade=12)

    primeira = (
        await cliente.get(f"{ROTA}/{filme.sk_movie_id}/reviews", params={"tamanho": 5})
    ).json()
    segunda = (
        await cliente.get(f"{ROTA}/{filme.sk_movie_id}/reviews", params={"tamanho": 5, "pagina": 2})
    ).json()

    ids_primeira = {item["id"] for item in primeira["items"]}
    ids_segunda = {item["id"] for item in segunda["items"]}

    assert primeira["total"] == 12
    assert primeira["paginas"] == 3
    assert len(ids_primeira) == 5
    assert not ids_primeira & ids_segunda


async def test_filme_sem_avaliacoes_responde_pagina_vazia(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Existir sem avaliações é diferente de não existir: 200 vazio, não 404."""

    filme = await criar_filme(sessao, titulo="Ninguem viu", popularidade=1.0)

    resposta = await cliente.get(f"{ROTA}/{filme.sk_movie_id}/reviews")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "items": [],
        "total": 0,
        "pagina": 1,
        "tamanho": 20,
        "paginas": 0,
    }


async def test_avaliacoes_de_filme_inexistente_respondem_404(cliente: AsyncClient) -> None:
    assert (await cliente.get(f"{ROTA}/inexistente/reviews")).status_code == 404


async def test_avaliacoes_de_um_filme_nao_vazam_para_outro(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    primeiro = await criar_filme(sessao, titulo="Primeiro", popularidade=2.0)
    segundo = await criar_filme(sessao, titulo="Segundo", popularidade=1.0)
    await criar_avaliacoes(sessao, primeiro, quantidade=3)

    corpo = (await cliente.get(f"{ROTA}/{segundo.sk_movie_id}/reviews")).json()

    assert corpo["total"] == 0
