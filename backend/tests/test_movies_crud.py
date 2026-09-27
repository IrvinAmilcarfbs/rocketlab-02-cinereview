"""Testes do cadastro, atualização e remoção de filmes."""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies import models
from tests.conftest import criar_avaliacoes, criar_filme, criar_generos

ROTA = "/api/v1/movies"

ENTRADA = {
    "titulo": "Cidade de Deus",
    "ano": 2002,
    "sinopse": "A vida na favela carioca ao longo de três décadas.",
    "duracao_minutos": 130,
    "status": "Lançado",
    "poster_url": "https://exemplo/cidade.jpg",
    "generos": ["Crime", "Drama"],
    "diretores": ["Fernando Meirelles"],
}


async def test_cadastro_devolve_a_ficha_completa(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_generos(sessao, "Crime", "Drama")

    resposta = await cliente.post(ROTA, json=ENTRADA)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == "Cidade de Deus"
    assert corpo["ano"] == 2002
    assert corpo["duracao_minutos"] == 130
    assert [genero["nome"] for genero in corpo["generos"]] == ["Crime", "Drama"]
    assert [pessoa["nome"] for pessoa in corpo["diretores"]] == ["Fernando Meirelles"]
    # Sem avaliações, a média é nula e não zero: "sem informação" não é "nota 0".
    assert corpo["nota_media"] is None
    assert corpo["qtd_avaliacoes"] == 0


async def test_cadastro_grava_a_linha_do_fato(cliente: AsyncClient, sessao: AsyncSession) -> None:
    """Sem fato o filme existiria no banco e seria invisível no catálogo.

    A listagem usa join interno com ``fact_movies_performance``. Este teste é o
    que impede o cadastro de criar um filme inalcançável.
    """

    await criar_generos(sessao, "Crime", "Drama")
    filme_id = (await cliente.post(ROTA, json=ENTRADA)).json()["id"]

    fato = await sessao.get(models.FactMoviePerformance, filme_id)
    assert fato is not None
    assert fato.popularidade is None

    # E o filme aparece de fato no catálogo.
    catalogo = (await cliente.get(ROTA)).json()
    assert filme_id in {item["id"] for item in catalogo["items"]}


async def test_cadastro_marca_a_procedencia_no_id_filme(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Os 95.645 valores do acervo são identificadores numéricos do TMDB."""

    await criar_generos(sessao, "Crime", "Drama")
    filme_id = (await cliente.post(ROTA, json=ENTRADA)).json()["id"]

    filme = await sessao.get(models.DimMovie, filme_id)
    assert filme is not None
    assert filme.id_filme.startswith("local-")
    assert filme.criado_em is not None


async def test_cadastro_preenche_as_colunas_derivadas(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """O evento do ORM cobre o cadastro: o filme nasce encontrável pela busca."""

    await criar_generos(sessao, "Drama")
    resposta = await cliente.post(
        ROTA, json={**ENTRADA, "titulo": "A Canção: Do Asfalto", "generos": ["Drama"]}
    )
    filme_id = resposta.json()["id"]

    filme = await sessao.get(models.DimMovie, filme_id)
    assert filme is not None
    assert filme.titulo_busca == "a cancao: do asfalto"
    assert filme.titulo_chave == "acancaodoasfalto"

    assert (await cliente.get(ROTA, params={"busca": "cancao"})).json()["total"] == 1


async def test_cadastro_reaproveita_diretor_existente(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """``(nome, tipo)`` é UNIQUE: é o que impede a dimensão de duplicar."""

    await criar_generos(sessao, "Drama")
    entrada = {**ENTRADA, "generos": ["Drama"], "diretores": ["Fernando Meirelles"]}

    primeiro = (await cliente.post(ROTA, json=entrada)).json()
    segundo = (await cliente.post(ROTA, json={**entrada, "titulo": "Outro Filme"})).json()

    total = await sessao.scalar(
        select(func.count())
        .select_from(models.DimPerson)
        .where(models.DimPerson.nome_pessoa == "Fernando Meirelles")
    )
    assert total == 1
    assert primeiro["diretores"][0]["id"] == segundo["diretores"][0]["id"]


async def test_cadastro_cria_diretor_com_papel_de_diretor(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """O papel mora em ``dim_people.tipo_pessoa``, não na bridge."""

    await criar_generos(sessao, "Drama")
    await cliente.post(
        ROTA, json={**ENTRADA, "generos": ["Drama"], "diretores": ["Kleber Mendonca"]}
    )

    pessoa = await sessao.scalar(
        select(models.DimPerson).where(models.DimPerson.nome_pessoa == "Kleber Mendonca")
    )
    assert pessoa is not None
    assert pessoa.tipo_pessoa == "Diretor"


async def test_cadastro_recusa_genero_fora_do_vocabulario(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Criar o gênero faltante deixaria um erro de digitação virar dimensão."""

    await criar_generos(sessao, "Drama")

    resposta = await cliente.post(ROTA, json={**ENTRADA, "generos": ["Drama", "Comedia"]})

    assert resposta.status_code == 422
    assert "Comedia" in resposta.json()["detail"]
    # Nada foi gravado: os gêneros são resolvidos antes de qualquer alteração.
    assert (await cliente.get(ROTA)).json()["total"] == 0


async def test_cadastro_remove_repeticoes_da_entrada(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """As bridges têm chave composta: o mesmo gênero duas vezes daria 500."""

    await criar_generos(sessao, "Drama")

    resposta = await cliente.post(
        ROTA,
        json={**ENTRADA, "generos": ["Drama", "Drama"], "diretores": ["Ana", "Ana"]},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert len(corpo["generos"]) == 1
    assert len(corpo["diretores"]) == 1


async def test_cadastro_normaliza_espacos_nos_nomes(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """ " Ana" e "Ana" criariam duas linhas em ``dim_people`` por um espaço."""

    await criar_generos(sessao, "Drama")
    await cliente.post(ROTA, json={**ENTRADA, "generos": ["Drama"], "diretores": ["Ana Silva"]})
    await cliente.post(
        ROTA,
        json={**ENTRADA, "titulo": "Outro", "generos": ["Drama"], "diretores": ["  Ana Silva  "]},
    )

    total = await sessao.scalar(select(func.count()).select_from(models.DimPerson))
    assert total == 1


async def test_cadastro_trata_texto_em_branco_como_ausencia(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_generos(sessao, "Drama")

    corpo = (
        await cliente.post(
            ROTA,
            json={**ENTRADA, "generos": ["Drama"], "sinopse": "   ", "poster_url": ""},
        )
    ).json()

    assert corpo["sinopse"] is None
    assert corpo["poster_url"] is None


async def test_cadastro_recusa_entrada_invalida(cliente: AsyncClient) -> None:
    assert (await cliente.post(ROTA, json={**ENTRADA, "titulo": "   "})).status_code == 422
    assert (await cliente.post(ROTA, json={**ENTRADA, "ano": 1500})).status_code == 422
    assert (await cliente.post(ROTA, json={**ENTRADA, "status": "Inventado"})).status_code == 422
    assert (await cliente.post(ROTA, json={**ENTRADA, "duracao_minutos": 0})).status_code == 422


async def test_cadastro_aceita_sem_genero_e_sem_diretor(cliente: AsyncClient) -> None:
    """20.037 filmes do acervo não têm gênero e 16.181 não têm diretor.

    Exigi-los tornaria esses filmes impossíveis de editar, porque o formulário
    abriria vazio e o PUT recusaria o que ele mesmo carregou.
    """

    resposta = await cliente.post(
        ROTA, json={"titulo": "Filme Sem Ficha", "generos": [], "diretores": []}
    )

    assert resposta.status_code == 201
    assert resposta.json()["generos"] == []


async def test_listar_generos_devolve_o_vocabulario(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_generos(sessao, "Drama", "Action", "Crime")

    corpo = (await cliente.get(f"{ROTA}/generos")).json()

    assert [genero["nome"] for genero in corpo] == ["Action", "Crime", "Drama"]


async def test_atualizacao_substitui_o_subconjunto_editavel(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_generos(sessao, "Drama", "Crime", "Action")
    filme_id = (await cliente.post(ROTA, json=ENTRADA)).json()["id"]

    resposta = await cliente.put(
        f"{ROTA}/{filme_id}",
        json={**ENTRADA, "titulo": "Cidade de Deus (Remaster)", "generos": ["Action"]},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["titulo"] == "Cidade de Deus (Remaster)"
    assert [genero["nome"] for genero in corpo["generos"]] == ["Action"]
    assert corpo["id"] == filme_id


async def test_atualizacao_esvazia_campo_omitido_do_subconjunto(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """PUT substitui: o que o formulário mostra em branco fica em branco."""

    await criar_generos(sessao, "Drama", "Crime")
    filme_id = (await cliente.post(ROTA, json=ENTRADA)).json()["id"]

    corpo = (await cliente.put(f"{ROTA}/{filme_id}", json={"titulo": "Só o título"})).json()

    assert corpo["sinopse"] is None
    assert corpo["generos"] == []
    assert corpo["diretores"] == []


async def test_atualizacao_preserva_elenco_e_roteiristas(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Substituir ``filme.people`` inteiro apagaria quem o formulário não mostra.

    Um filme do acervo chega a 150 pessoas creditadas; a troca tem de alcançar
    apenas as linhas de papel "Diretor".
    """

    await criar_generos(sessao, "Drama")
    filme = await criar_filme(
        sessao,
        titulo="Filme do Acervo",
        popularidade=5.0,
        pessoas=(
            ("Diretor Antigo", "Diretor"),
            ("Ator Um", "Ator"),
            ("Roteirista Um", "Roteirista"),
        ),
    )

    corpo = (
        await cliente.put(
            f"{ROTA}/{filme.sk_movie_id}",
            json={
                "titulo": "Filme do Acervo",
                "generos": ["Drama"],
                "diretores": ["Diretor Novo"],
            },
        )
    ).json()

    assert [pessoa["nome"] for pessoa in corpo["diretores"]] == ["Diretor Novo"]
    assert [pessoa["nome"] for pessoa in corpo["elenco"]] == ["Ator Um"]
    assert [pessoa["nome"] for pessoa in corpo["roteiristas"]] == ["Roteirista Um"]


async def test_atualizacao_nao_toca_no_que_o_formulario_nao_controla(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_generos(sessao, "Drama")
    filme = await criar_filme(sessao, titulo="Com Metricas", popularidade=42.5)

    corpo = (
        await cliente.put(
            f"{ROTA}/{filme.sk_movie_id}",
            json={"titulo": "Com Metricas", "generos": ["Drama"], "diretores": []},
        )
    ).json()

    assert corpo["metricas"]["popularidade"] == 42.5


async def test_atualizacao_de_filme_inexistente_responde_404(cliente: AsyncClient) -> None:
    resposta = await cliente.put(f"{ROTA}/nao-existe", json={"titulo": "Qualquer"})

    assert resposta.status_code == 404


async def test_atualizacao_recusa_genero_desconhecido(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    await criar_generos(sessao, "Drama")
    filme = await criar_filme(sessao, titulo="Qualquer", popularidade=1.0)

    resposta = await cliente.put(
        f"{ROTA}/{filme.sk_movie_id}", json={"titulo": "Qualquer", "generos": ["Inexistente"]}
    )

    assert resposta.status_code == 422


async def test_remocao_apaga_o_filme_e_suas_dependencias(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Uma instrução basta: o ON DELETE CASCADE do banco faz o resto.

    As chaves estrangeiras exigem ``PRAGMA foreign_keys=ON``, ligado por conexão
    em ``app.db.session``. Este teste é o que garante que o pragma continua lá.
    """

    filme = await criar_filme(
        sessao, titulo="Para Apagar", popularidade=1.0, generos=("Drama",), qtd_avaliacoes=3
    )
    await criar_avaliacoes(sessao, filme, 3)
    filme_id = filme.sk_movie_id

    resposta = await cliente.delete(f"{ROTA}/{filme_id}")

    assert resposta.status_code == 204
    assert resposta.content == b""

    # O DELETE do ORM sincroniza a sessão apenas para a entidade da instrução:
    # `DimMovie` sai do identity map, mas as linhas que o banco removeu por
    # cascade continuam em cache e `sessao.get` as devolveria sem consultar nada.
    # Esvaziar o mapa é o que faz as asserções abaixo falarem do banco.
    sessao.expunge_all()

    assert await sessao.get(models.DimMovie, filme_id) is None
    assert await sessao.get(models.FactMoviePerformance, filme_id) is None
    assert await sessao.get(models.DimReview, filme_id) is None
    assert (
        await sessao.scalar(
            select(func.count())
            .select_from(models.MovieReview)
            .where(models.MovieReview.sk_movie_id == filme_id)
        )
    ) == 0
    assert (
        await sessao.scalar(
            select(func.count())
            .select_from(models.bridge_movie_genre)
            .where(models.bridge_movie_genre.c.sk_movie_id == filme_id)
        )
    ) == 0
    # O gênero sobrevive: a dimensão é compartilhada, não propriedade do filme.
    assert await sessao.scalar(select(func.count()).select_from(models.DimGenre)) == 1


async def test_remocao_de_filme_inexistente_responde_404(cliente: AsyncClient) -> None:
    resposta = await cliente.delete(f"{ROTA}/nao-existe")

    assert resposta.status_code == 404


async def test_remocao_tira_o_filme_do_catalogo(cliente: AsyncClient, sessao: AsyncSession) -> None:
    await criar_filme(sessao, titulo="Fica", popularidade=2.0)
    vai = await criar_filme(sessao, titulo="Sai", popularidade=1.0)

    await cliente.delete(f"{ROTA}/{vai.sk_movie_id}")

    corpo = (await cliente.get(ROTA)).json()
    assert corpo["total"] == 1
    assert [item["titulo"] for item in corpo["items"]] == ["Fica"]
