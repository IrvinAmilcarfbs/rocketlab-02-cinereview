"""Testes da ordenação do catálogo, em especial a concatenação de dois blocos.

"Adicionados recentemente" não é um ``ORDER BY``: é a concatenação de duas
ordenações. Primeiro os filmes cadastrados pela aplicação, do mais novo para o
mais antigo; depois o acervo carregado, por popularidade. As 95.645 linhas dos
CSVs não têm data de cadastro, e ordená-las por um nulo comum devolveria uma
lista embaralhada.

A fronteira entre os blocos é o ponto onde a aritmética de deslocamento pode
errar, e é o que a maior parte destes testes protege.
"""

from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import criar_filme, criar_generos

ROTA = "/api/v1/movies"


async def _titulos(cliente: AsyncClient, **params: object) -> list[str]:
    return [item["titulo"] for item in (await cliente.get(ROTA, params=params)).json()["items"]]


async def _acervo_e_cadastrados(sessao: AsyncSession) -> None:
    """Dois filmes cadastrados aqui e três do acervo, com popularidades distintas."""

    await criar_filme(sessao, titulo="Acervo Popular", popularidade=90.0)
    await criar_filme(sessao, titulo="Acervo Medio", popularidade=50.0)
    await criar_filme(sessao, titulo="Acervo Fraco", popularidade=10.0)
    await criar_filme(
        sessao,
        titulo="Cadastrado Antigo",
        popularidade=None,
        criado_em=datetime(2026, 1, 1, 10, 0),
    )
    await criar_filme(
        sessao,
        titulo="Cadastrado Novo",
        popularidade=None,
        criado_em=datetime(2026, 1, 2, 10, 0),
    )


async def test_recentes_exibe_os_cadastrados_antes_do_acervo(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await _acervo_e_cadastrados(sessao)

    assert await _titulos(cliente, ordenar="recentes") == [
        "Cadastrado Novo",
        "Cadastrado Antigo",
        "Acervo Popular",
        "Acervo Medio",
        "Acervo Fraco",
    ]


async def test_popularidade_segue_sendo_o_padrao(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """A primeira impressão do catálogo não mudou.

    Popularidade nula vai para o fim: no SQLite o nulo é menor que qualquer
    valor, e em ordem decrescente ele sobra no final. É justamente por isso que
    a ordenação por recentes existe — sem ela um filme cadastrado nasceria na
    última página.
    """

    await _acervo_e_cadastrados(sessao)

    titulos = await _titulos(cliente)

    assert titulos[:3] == ["Acervo Popular", "Acervo Medio", "Acervo Fraco"]
    # A ordem *entre* os dois cadastrados não é afirmada de propósito: ambos têm
    # popularidade nula e o desempate é por `sk_movie_id`, que é um SHA-256
    # aleatório. Exigir uma ordem aqui seria testar o acaso.
    assert set(titulos[3:]) == {"Cadastrado Novo", "Cadastrado Antigo"}


async def test_recentes_atravessa_a_fronteira_entre_os_blocos(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Uma página pode começar nos cadastrados e terminar no acervo."""

    await _acervo_e_cadastrados(sessao)

    assert await _titulos(cliente, ordenar="recentes", tamanho=3) == [
        "Cadastrado Novo",
        "Cadastrado Antigo",
        "Acervo Popular",
    ]


async def test_recentes_nao_repete_nem_omite_na_virada_de_pagina(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """O teste que justifica a aritmética de deslocamento.

    Se o segundo bloco não descontasse os cadastrados, ou não os excluísse da
    própria consulta, algum filme apareceria duas vezes e outro nunca.
    """

    await _acervo_e_cadastrados(sessao)

    primeira = await _titulos(cliente, ordenar="recentes", tamanho=2, pagina=1)
    segunda = await _titulos(cliente, ordenar="recentes", tamanho=2, pagina=2)
    terceira = await _titulos(cliente, ordenar="recentes", tamanho=2, pagina=3)

    reunidas = [*primeira, *segunda, *terceira]
    assert reunidas == [
        "Cadastrado Novo",
        "Cadastrado Antigo",
        "Acervo Popular",
        "Acervo Medio",
        "Acervo Fraco",
    ]
    assert len(set(reunidas)) == 5


async def test_recentes_pagina_inteiramente_dentro_do_acervo(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Quando o deslocamento já passou dos cadastrados, só o acervo responde."""

    await _acervo_e_cadastrados(sessao)

    assert await _titulos(cliente, ordenar="recentes", tamanho=2, pagina=2) == [
        "Acervo Popular",
        "Acervo Medio",
    ]


async def test_recentes_sem_nenhum_cadastrado_equivale_ao_padrao(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Catálogo recém-carregado: o primeiro bloco está vazio e não atrapalha."""

    await criar_filme(sessao, titulo="Alfa", popularidade=9.0)
    await criar_filme(sessao, titulo="Beta", popularidade=1.0)

    assert await _titulos(cliente, ordenar="recentes") == ["Alfa", "Beta"]


async def test_total_nao_depende_da_ordenacao(cliente: AsyncClient, sessao: AsyncSession) -> None:
    """As duas ordenações descrevem o mesmo conjunto, em ordem diferente."""

    await _acervo_e_cadastrados(sessao)

    padrao = (await cliente.get(ROTA)).json()
    recentes = (await cliente.get(ROTA, params={"ordenar": "recentes"})).json()

    assert padrao["total"] == recentes["total"] == 5
    assert padrao["paginas"] == recentes["paginas"]


async def test_filme_cadastrado_pela_api_aparece_em_recentes(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """O caminho completo: cadastrar e encontrar no catálogo.

    É o cenário que motivou a coluna ``criado_em`` — antes dela, um filme
    cadastrado nascia entre os 3.615 de popularidade nula, na última página.
    """

    await criar_generos(sessao, "Drama")
    await criar_filme(sessao, titulo="Acervo", popularidade=99.0)

    criado = await cliente.post(
        ROTA, json={"titulo": "Meu Filme", "generos": ["Drama"], "diretores": ["Eu"]}
    )
    assert criado.status_code == 201

    itens = (await cliente.get(ROTA, params={"ordenar": "recentes"})).json()["items"]
    assert itens[0]["titulo"] == "Meu Filme"
    assert itens[0]["id"] == criado.json()["id"]


async def test_ordenacao_invalida_e_recusada(cliente: AsyncClient) -> None:
    assert (await cliente.get(ROTA, params={"ordenar": "alfabetica"})).status_code == 422


async def test_ordenacao_e_ignorada_durante_a_busca(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Decisão documentada: a busca ordena por popularidade dentro dos grupos.

    Trocar a ordem durante a busca exigiria refazer o agrupamento de títulos
    repetidos sobre outra chave, sem ganho para quem procura um título.
    """

    await criar_filme(sessao, titulo="Serie Popular", popularidade=90.0)
    await criar_filme(
        sessao, titulo="Serie Nova", popularidade=1.0, criado_em=datetime(2026, 5, 1, 12, 0)
    )

    assert await _titulos(cliente, busca="serie", ordenar="recentes") == [
        "Serie Popular",
        "Serie Nova",
    ]
