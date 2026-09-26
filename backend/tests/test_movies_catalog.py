"""Testes do catálogo paginado."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import criar_filme

ROTA = "/api/v1/movies"


async def test_catalogo_vazio_responde_envelope_coerente(cliente: AsyncClient) -> None:
    resposta = await cliente.get(ROTA)

    assert resposta.status_code == 200
    assert resposta.json() == {"items": [], "total": 0, "pagina": 1, "tamanho": 20, "paginas": 0}


async def test_catalogo_ordena_por_popularidade_decrescente(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_filme(sessao, titulo="Menos popular", popularidade=1.0)
    await criar_filme(sessao, titulo="Mais popular", popularidade=99.0)
    await criar_filme(sessao, titulo="Intermediario", popularidade=50.0)

    corpo = (await cliente.get(ROTA)).json()

    assert [item["titulo"] for item in corpo["items"]] == [
        "Mais popular",
        "Intermediario",
        "Menos popular",
    ]


async def test_pagina_vem_completa_mesmo_com_varios_generos(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Protege contra a armadilha do ``joinedload`` com LIMIT.

    Se a coleção de gêneros fosse carregada por JOIN, o LIMIT recairia sobre as
    linhas do resultado e não sobre os filmes: com três gêneros cada, uma página
    de cinco traria menos de dois filmes.
    """

    for indice in range(5):
        await criar_filme(
            sessao,
            titulo=f"Filme {indice}",
            popularidade=float(indice),
            generos=(f"Genero A{indice}", f"Genero B{indice}", f"Genero C{indice}"),
        )

    corpo = (await cliente.get(ROTA, params={"tamanho": 5})).json()

    assert len(corpo["items"]) == 5
    assert all(len(item["generos"]) == 3 for item in corpo["items"])


async def test_paginas_nao_repetem_nem_omitem_filmes_empatados(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Sem o desempate pela chave, filmes de igual popularidade oscilariam."""

    for indice in range(10):
        await criar_filme(sessao, titulo=f"Empatado {indice}", popularidade=7.0)

    primeira = (await cliente.get(ROTA, params={"tamanho": 5, "pagina": 1})).json()
    segunda = (await cliente.get(ROTA, params={"tamanho": 5, "pagina": 2})).json()

    ids_primeira = {item["id"] for item in primeira["items"]}
    ids_segunda = {item["id"] for item in segunda["items"]}

    assert len(ids_primeira) == 5
    assert not ids_primeira & ids_segunda
    assert len(ids_primeira | ids_segunda) == 10
    assert primeira["total"] == 10
    assert primeira["paginas"] == 2


async def test_filme_sem_avaliacao_tem_media_nula(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Ausência de avaliação é nulo, não zero — são informações diferentes."""

    await criar_filme(sessao, titulo="Sem avaliacao", popularidade=1.0)
    await criar_filme(sessao, titulo="Avaliado", popularidade=2.0, nota_media=8.5, qtd_avaliacoes=4)

    itens = {item["titulo"]: item for item in (await cliente.get(ROTA)).json()["items"]}

    assert itens["Sem avaliacao"]["nota_media"] is None
    assert itens["Sem avaliacao"]["qtd_avaliacoes"] == 0
    assert itens["Avaliado"]["nota_media"] == 8.5
    assert itens["Avaliado"]["qtd_avaliacoes"] == 4


async def test_filme_sem_fato_nao_aparece_no_catalogo(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Documenta a consequência do join interno usado para atender ao índice.

    O cadastro de filmes precisa gravar o fato junto com a dimensão.
    """

    await criar_filme(sessao, titulo="Com fato", popularidade=1.0)
    await criar_filme(sessao, titulo="Sem fato", popularidade=None, com_fato=False)

    corpo = (await cliente.get(ROTA)).json()

    assert [item["titulo"] for item in corpo["items"]] == ["Com fato"]
    assert corpo["total"] == 1, "o total precisa descrever o mesmo conjunto que a listagem"
    assert corpo["paginas"] == 1


async def test_parametros_invalidos_sao_rejeitados(cliente: AsyncClient) -> None:
    assert (await cliente.get(ROTA, params={"pagina": 0})).status_code == 422
    assert (await cliente.get(ROTA, params={"tamanho": 0})).status_code == 422
    assert (await cliente.get(ROTA, params={"tamanho": 101})).status_code == 422
    assert (await cliente.get(ROTA, params={"tamanho": 100})).status_code == 200
