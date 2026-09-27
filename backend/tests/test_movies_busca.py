"""Testes da busca por título."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import criar_filme

ROTA = "/api/v1/movies"


async def _titulos(cliente: AsyncClient, **params: object) -> list[str]:
    corpo = (await cliente.get(ROTA, params=params)).json()
    return [item["titulo"] for item in corpo["items"]]


async def test_busca_encontra_por_parte_do_titulo(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_filme(sessao, titulo="O Poderoso Chefao", popularidade=9.0)
    await criar_filme(sessao, titulo="Matrix", popularidade=8.0)

    assert await _titulos(cliente, busca="chefao") == ["O Poderoso Chefao"]
    assert await _titulos(cliente, busca="POD") == ["O Poderoso Chefao"]


async def test_busca_ignora_acentos_nos_dois_sentidos(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """3.650 títulos do catálogo têm acento; exigir digitação exata os esconderia."""

    await criar_filme(sessao, titulo="A Canção Da Chuva", popularidade=5.0)

    assert await _titulos(cliente, busca="cancao") == ["A Canção Da Chuva"]
    assert await _titulos(cliente, busca="Canção") == ["A Canção Da Chuva"]
    assert await _titulos(cliente, busca="CANCAO") == ["A Canção Da Chuva"]


async def test_busca_agrupa_titulos_repetidos(cliente: AsyncClient, sessao: AsyncSession) -> None:
    """Mantém apenas a entrada mais popular de cada título repetido.

    Na base real "Die Hart 2: Die Harter" aparece 30 vezes, com identificadores
    distintos vindos do TMDB.
    """

    for popularidade in (1.0, 50.0, 7.0):
        await criar_filme(sessao, titulo="Die Hart", popularidade=popularidade)
    await criar_filme(sessao, titulo="Outro Filme", popularidade=99.0)

    corpo = (await cliente.get(ROTA, params={"busca": "die hart"})).json()

    assert corpo["total"] == 1
    assert len(corpo["items"]) == 1


async def test_agrupamento_preserva_o_mais_popular(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_filme(sessao, titulo="Repetido", popularidade=1.0, generos=("Drama",))
    await criar_filme(sessao, titulo="Repetido", popularidade=99.0, generos=("Acao",))

    itens = (await cliente.get(ROTA, params={"busca": "repetido"})).json()["items"]

    assert len(itens) == 1
    assert [genero["nome"] for genero in itens[0]["generos"]] == ["Acao"]


async def test_catalogo_sem_busca_nao_agrupa(cliente: AsyncClient, sessao: AsyncSession) -> None:
    """O agrupamento vale só para a busca: o acervo é exibido como ele é."""

    for popularidade in (1.0, 2.0, 3.0):
        await criar_filme(sessao, titulo="Repetido", popularidade=popularidade)

    assert (await cliente.get(ROTA)).json()["total"] == 3


async def test_busca_em_branco_equivale_a_nao_buscar(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_filme(sessao, titulo="Unico", popularidade=1.0)

    assert (await cliente.get(ROTA, params={"busca": "   "})).json()["total"] == 1
    assert (await cliente.get(ROTA, params={"busca": ""})).json()["total"] == 1


async def test_curingas_do_like_nao_sao_interpretados(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Sem escapar, "%" casaria com tudo e "_" com qualquer caractere."""

    await criar_filme(sessao, titulo="100% Wolf", popularidade=5.0)
    await criar_filme(sessao, titulo="Outro Filme", popularidade=4.0)

    assert await _titulos(cliente, busca="100%") == ["100% Wolf"]
    # Como literal, "%" encontra só o título que realmente o contém. Fosse
    # curinga, casaria com os dois filmes.
    assert await _titulos(cliente, busca="%") == ["100% Wolf"]
    # Nenhum título tem "_": como curinga, casaria com todos.
    assert (await cliente.get(ROTA, params={"busca": "_"})).json()["total"] == 0


async def test_busca_sem_resultados_responde_pagina_vazia(cliente: AsyncClient) -> None:
    corpo = (await cliente.get(ROTA, params={"busca": "zzzqx"})).json()

    assert corpo["items"] == []
    assert corpo["total"] == 0
    assert corpo["paginas"] == 0


async def test_busca_ordena_por_popularidade_e_pagina(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    for indice in range(6):
        await criar_filme(sessao, titulo=f"Serie Filme {indice}", popularidade=float(indice))

    primeira = (await cliente.get(ROTA, params={"busca": "serie", "tamanho": 3})).json()
    segunda = (await cliente.get(ROTA, params={"busca": "serie", "tamanho": 3, "pagina": 2})).json()

    assert primeira["total"] == 6
    assert [item["titulo"] for item in primeira["items"]] == [
        "Serie Filme 5",
        "Serie Filme 4",
        "Serie Filme 3",
    ]
    ids_primeira = {item["id"] for item in primeira["items"]}
    assert not ids_primeira & {item["id"] for item in segunda["items"]}
