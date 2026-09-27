"""Testes do envio e da remoção de avaliações, e da manutenção do agregado.

`movie_reviews` é a fonte de verdade e `dim_reviews` é agregado materializado.
Quase todo teste aqui existe para garantir que os dois não se separem: uma
avaliação gravada sem o agregado atualizado deixaria a média mentindo, e nada
apontaria o erro — o filme continuaria respondendo, com o valor anterior.
"""

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies import models
from tests.conftest import criar_avaliacoes, criar_filme

ROTA = "/api/v1/movies"

ENTRADA = {"nome": "Irvin", "nota": 8.0, "comentario": "Um filme necessário."}


def rota_avaliacoes(filme_id: str) -> str:
    return f"{ROTA}/{filme_id}/reviews"


async def _agregado(sessao: AsyncSession, filme_id: str) -> models.DimReview | None:
    # A sessão é a mesma da requisição, e o upsert do agregado acontece por Core:
    # sem esvaziar o identity map, um objeto em cache poderia responder no lugar
    # da linha gravada.
    sessao.expunge_all()
    return await sessao.scalar(
        select(models.DimReview).where(models.DimReview.sk_movie_id == filme_id)
    )


async def test_avaliacao_e_criada_com_a_ficha_devolvida(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    filme = await criar_filme(sessao, titulo="Bacurau", popularidade=10.0)

    resposta = await cliente.post(rota_avaliacoes(filme.sk_movie_id), json=ENTRADA)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Irvin"
    assert corpo["nota"] == 8.0
    assert corpo["comentario"] == "Um filme necessário."
    assert corpo["id"]


async def test_avaliacao_cria_o_agregado_de_filme_inedito(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """`dim_reviews` só tem linha para os filmes já avaliados.

    Avaliar um filme inédito precisa **criar** a linha. Por isso a gravação é um
    upsert, e não um update.
    """

    filme = await criar_filme(sessao, titulo="Inedito", popularidade=1.0)
    assert await _agregado(sessao, filme.sk_movie_id) is None

    await cliente.post(rota_avaliacoes(filme.sk_movie_id), json=ENTRADA)

    agregado = await _agregado(sessao, filme.sk_movie_id)
    assert agregado is not None
    assert agregado.qtd_avaliacoes_usuarios == 1
    assert agregado.nota_media_usuarios == 8.0


async def test_media_e_recalculada_a_cada_avaliacao(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    filme = await criar_filme(sessao, titulo="Com Media", popularidade=1.0)
    rota = rota_avaliacoes(filme.sk_movie_id)

    await cliente.post(rota, json={**ENTRADA, "nota": 10.0})
    await cliente.post(rota, json={**ENTRADA, "nome": "Outro", "nota": 6.0})

    agregado = await _agregado(sessao, filme.sk_movie_id)
    assert agregado is not None
    assert agregado.qtd_avaliacoes_usuarios == 2
    assert agregado.nota_media_usuarios == 8.0


async def test_agregado_reconcilia_um_valor_ja_errado(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """O recálculo corrige o agregado; a aritmética incremental o perpetuaria.

    É a vantagem concreta de recalcular em vez de somar: uma linha errada — por
    carga antiga, por migração, por qualquer motivo — se conserta na escrita
    seguinte.
    """

    filme = await criar_filme(
        sessao, titulo="Agregado Torto", popularidade=1.0, nota_media=2.0, qtd_avaliacoes=99
    )

    await cliente.post(rota_avaliacoes(filme.sk_movie_id), json={**ENTRADA, "nota": 7.0})

    agregado = await _agregado(sessao, filme.sk_movie_id)
    assert agregado is not None
    assert agregado.qtd_avaliacoes_usuarios == 1
    assert agregado.nota_media_usuarios == 7.0


async def test_media_aparece_na_ficha_e_no_catalogo(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """O requisito 7 lê o agregado que o requisito 6 escreve."""

    filme = await criar_filme(sessao, titulo="Visivel", popularidade=5.0)
    rota = rota_avaliacoes(filme.sk_movie_id)

    await cliente.post(rota, json={**ENTRADA, "nota": 9.0})
    await cliente.post(rota, json={**ENTRADA, "nome": "Outro", "nota": 7.0})

    ficha = (await cliente.get(f"{ROTA}/{filme.sk_movie_id}")).json()
    assert ficha["nota_media"] == 8.0
    assert ficha["qtd_avaliacoes"] == 2

    item = (await cliente.get(ROTA)).json()["items"][0]
    assert item["nota_media"] == 8.0
    assert item["qtd_avaliacoes"] == 2


async def test_avaliacao_nova_aparece_primeiro_na_lista(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    filme = await criar_filme(sessao, titulo="Ordem", popularidade=1.0)
    await criar_avaliacoes(sessao, filme, 3)

    await cliente.post(rota_avaliacoes(filme.sk_movie_id), json={**ENTRADA, "nome": "Recente"})

    pagina = (await cliente.get(rota_avaliacoes(filme.sk_movie_id))).json()
    assert pagina["total"] == 4
    assert pagina["items"][0]["nome"] == "Recente"


async def test_instante_e_devolvido_com_fuso(cliente: AsyncClient, sessao: AsyncSession) -> None:
    """Sem fuso, o navegador leria o instante como hora local.

    `created_at` usa `CURRENT_TIMESTAMP` do SQLite, que é UTC, e volta do banco
    sem fuso. Em UTC-3, uma avaliação criada agora apareceria três horas no
    futuro.
    """

    filme = await criar_filme(sessao, titulo="Com Fuso", popularidade=1.0)

    corpo = (await cliente.post(rota_avaliacoes(filme.sk_movie_id), json=ENTRADA)).json()

    criado = datetime.fromisoformat(corpo["criado_em"])
    assert criado.tzinfo is not None
    assert criado.utcoffset() is not None
    assert criado.utcoffset().total_seconds() == 0
    # E o instante descreve o presente, não um deslocamento de três horas.
    assert abs((datetime.now(UTC) - criado).total_seconds()) < 120


async def test_avaliacao_normaliza_espacos(cliente: AsyncClient, sessao: AsyncSession) -> None:
    filme = await criar_filme(sessao, titulo="Espacos", popularidade=1.0)

    corpo = (
        await cliente.post(
            rota_avaliacoes(filme.sk_movie_id),
            json={"nome": "  Irvin  ", "nota": 5, "comentario": "  Bom.  "},
        )
    ).json()

    assert corpo["nome"] == "Irvin"
    assert corpo["comentario"] == "Bom."


async def test_avaliacao_recusa_entrada_invalida(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    filme = await criar_filme(sessao, titulo="Validacao", popularidade=1.0)
    rota = rota_avaliacoes(filme.sk_movie_id)

    assert (await cliente.post(rota, json={**ENTRADA, "nota": 11})).status_code == 422
    assert (await cliente.post(rota, json={**ENTRADA, "nota": -1})).status_code == 422
    assert (await cliente.post(rota, json={**ENTRADA, "nome": "   "})).status_code == 422
    assert (await cliente.post(rota, json={**ENTRADA, "comentario": "  "})).status_code == 422
    assert (await cliente.post(rota, json={"nome": "X", "nota": 5})).status_code == 422

    # Nenhuma tentativa inválida criou agregado.
    assert await _agregado(sessao, filme.sk_movie_id) is None


async def test_avaliacao_aceita_os_extremos_da_escala(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """A escala do banco vai de 0 a 10, e o contrato acompanha o CheckConstraint.

    A interface produz inteiros de 1 a 10 pelas estrelas, mas 39.432 avaliações
    carregadas têm valores fracionários como 1,27 — restringir o contrato ao que
    a tela digita tornaria parte dos dados impossível de reenviar.
    """

    filme = await criar_filme(sessao, titulo="Extremos", popularidade=1.0)
    rota = rota_avaliacoes(filme.sk_movie_id)

    assert (await cliente.post(rota, json={**ENTRADA, "nota": 0})).status_code == 201
    assert (await cliente.post(rota, json={**ENTRADA, "nota": 10})).status_code == 201
    assert (await cliente.post(rota, json={**ENTRADA, "nota": 7.33})).status_code == 201


async def test_avaliar_filme_inexistente_responde_404(cliente: AsyncClient) -> None:
    resposta = await cliente.post(rota_avaliacoes("nao-existe"), json=ENTRADA)

    assert resposta.status_code == 404


async def test_remocao_recalcula_a_media(cliente: AsyncClient, sessao: AsyncSession) -> None:
    filme = await criar_filme(sessao, titulo="Remover Uma", popularidade=1.0)
    rota = rota_avaliacoes(filme.sk_movie_id)

    alvo = (await cliente.post(rota, json={**ENTRADA, "nota": 2.0})).json()["id"]
    await cliente.post(rota, json={**ENTRADA, "nome": "Fica", "nota": 8.0})

    resposta = await cliente.delete(f"{rota}/{alvo}")

    assert resposta.status_code == 204
    agregado = await _agregado(sessao, filme.sk_movie_id)
    assert agregado is not None
    assert agregado.qtd_avaliacoes_usuarios == 1
    assert agregado.nota_media_usuarios == 8.0


async def test_remover_a_ultima_avaliacao_apaga_o_agregado(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Existe agregado se, e somente se, existem avaliações.

    Deixar a linha com contagem zero criaria um segundo jeito de dizer "sem
    avaliações", divergindo da invariante que a carga inicial produz.
    """

    filme = await criar_filme(sessao, titulo="Ultima", popularidade=1.0)
    rota = rota_avaliacoes(filme.sk_movie_id)
    alvo = (await cliente.post(rota, json=ENTRADA)).json()["id"]

    await cliente.delete(f"{rota}/{alvo}")

    assert await _agregado(sessao, filme.sk_movie_id) is None
    ficha = (await cliente.get(f"{ROTA}/{filme.sk_movie_id}")).json()
    assert ficha["nota_media"] is None
    assert ficha["qtd_avaliacoes"] == 0


async def test_remocao_exige_que_a_avaliacao_seja_do_filme(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Sem esse filtro, o agregado reconciliado seria o do filme errado."""

    um = await criar_filme(sessao, titulo="Filme Um", popularidade=2.0)
    outro = await criar_filme(sessao, titulo="Filme Dois", popularidade=1.0)
    alvo = (await cliente.post(rota_avaliacoes(um.sk_movie_id), json=ENTRADA)).json()["id"]

    resposta = await cliente.delete(f"{rota_avaliacoes(outro.sk_movie_id)}/{alvo}")

    assert resposta.status_code == 404
    # A avaliação do outro filme segue intacta.
    assert (await cliente.get(rota_avaliacoes(um.sk_movie_id))).json()["total"] == 1


async def test_remover_avaliacao_inexistente_responde_404(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    filme = await criar_filme(sessao, titulo="Sem Avaliacao", popularidade=1.0)

    resposta = await cliente.delete(f"{rota_avaliacoes(filme.sk_movie_id)}/nao-existe")

    assert resposta.status_code == 404


async def test_apagar_filme_leva_avaliacoes_e_agregado(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Interação entre as etapas 6 e 7: o cascade cobre as avaliações novas."""

    filme = await criar_filme(sessao, titulo="Tudo Junto", popularidade=1.0)
    filme_id = filme.sk_movie_id
    await cliente.post(rota_avaliacoes(filme_id), json=ENTRADA)

    await cliente.delete(f"{ROTA}/{filme_id}")

    sessao.expunge_all()
    assert (
        await sessao.scalar(
            select(func.count())
            .select_from(models.MovieReview)
            .where(models.MovieReview.sk_movie_id == filme_id)
        )
    ) == 0
    assert await _agregado(sessao, filme_id) is None


async def test_avaliacoes_no_mesmo_segundo_mantem_a_ordem(
    cliente: AsyncClient, sessao: AsyncSession
) -> None:
    """Três envios seguidos saem na ordem inversa do envio, sem exceção.

    `CURRENT_TIMESTAMP` do SQLite tem precisão de segundo, e os três cairiam no
    mesmo valor. O desempate é a chave, um SHA-256 aleatório que não codifica
    recência — a ordem seria sorteada. O padrão em Python, com microssegundos, é
    o que torna a garantia real.
    """

    filme = await criar_filme(sessao, titulo="Mesmo Segundo", popularidade=1.0)
    rota = rota_avaliacoes(filme.sk_movie_id)

    for nome in ("Primeiro", "Segundo", "Terceiro"):
        await cliente.post(rota, json={**ENTRADA, "nome": nome})

    nomes = [item["nome"] for item in (await cliente.get(rota)).json()["items"]]
    assert nomes == ["Terceiro", "Segundo", "Primeiro"]
