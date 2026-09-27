"""Regras do catálogo e tradução do esquema estrela para o contrato da API.

Esta camada é a fronteira entre os dois modelos. O banco guarda um filme
espalhado por dimensões e bridges; a API entrega um recurso plano. Concentrar a
tradução aqui evita que o formato do banco vaze para o contrato — e que uma
mudança no contrato exija mexer nas consultas.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagina, ParametrosPaginacao
from app.core.texto import normalizar_busca
from app.movies import repository
from app.movies.models import DimMovie, MovieReview
from app.movies.schemas import (
    AvaliacaoResumo,
    FilmeDetalhe,
    FilmeResumo,
    GeneroResumo,
    MetricasFilme,
    PessoaResumo,
    ProdutoraResumo,
)


def para_resumo(filme: DimMovie) -> FilmeResumo:
    """Achata um filme do esquema estrela no item exibido no catálogo."""

    agregado = filme.reviews_summary
    return FilmeResumo(
        id=filme.sk_movie_id,
        titulo=filme.titulo,
        ano=filme.ano_lancamento,
        poster_url=filme.url_poster,
        generos=[
            GeneroResumo(id=genero.sk_genre_id, nome=genero.nome_genero) for genero in filme.genres
        ],
        # Filmes sem avaliação não têm linha no agregado: a média vira nula, que
        # é diferente de zero — "sem informação" não é "todos detestaram".
        nota_media=agregado.nota_media_usuarios if agregado else None,
        qtd_avaliacoes=agregado.qtd_avaliacoes_usuarios if agregado else 0,
    )


async def listar_catalogo(
    sessao: AsyncSession,
    parametros: ParametrosPaginacao,
    busca: str | None = None,
) -> Pagina[FilmeResumo]:
    """Monta uma página do catálogo, filtrada por título quando houver busca.

    O termo digitado passa pela mesma normalização aplicada a ``titulo_busca``
    na carga — é o que permite "cancao" encontrar "Canção". Um termo que sobra
    vazio depois disso (só espaços, por exemplo) equivale a não buscar.
    """

    termo = normalizar_busca(busca) if busca else ""

    if termo:
        total = await repository.contar_busca(sessao, termo)
        filmes = await repository.buscar_filmes(
            sessao, termo, parametros.offset, parametros.tamanho
        )
    else:
        total = await repository.contar_filmes(sessao)
        filmes = await repository.listar_filmes(sessao, parametros.offset, parametros.tamanho)

    return Pagina.montar([para_resumo(filme) for filme in filmes], total, parametros)


def _pessoas(filme: DimMovie, papel: str) -> list[PessoaResumo]:
    """Separa por papel as pessoas creditadas no filme.

    A bridge liga filme e pessoa sem qualificar a relação: o papel mora em
    ``dim_people.tipo_pessoa``. Como as pessoas já vieram carregadas, filtrar em
    memória evita três consultas adicionais — e um filme tem oito pessoas em
    média.
    """

    return sorted(
        (
            PessoaResumo(id=pessoa.sk_person_id, nome=pessoa.nome_pessoa)
            for pessoa in filme.people
            if pessoa.tipo_pessoa == papel
        ),
        key=lambda pessoa: pessoa.nome,
    )


def _metricas(filme: DimMovie) -> MetricasFilme | None:
    desempenho = filme.performance
    if desempenho is None:
        return None

    def numero(valor: object) -> float | None:
        return float(valor) if valor is not None else None

    return MetricasFilme(
        popularidade=desempenho.popularidade,
        nota_tmdb=desempenho.nota_tmdb,
        qtd_tmdb=desempenho.qtd_tmdb,
        nota_imdb=desempenho.nota_imdb,
        qtd_imdb=desempenho.qtd_imdb,
        orcamento_usd=numero(desempenho.orcamento_usd),
        receita_usd=numero(desempenho.receita_usd),
        lucro_usd=numero(desempenho.lucro_usd),
    )


def para_detalhe(filme: DimMovie) -> FilmeDetalhe:
    """Reúne num recurso único o que o esquema estrela mantém espalhado."""

    agregado = filme.reviews_summary
    return FilmeDetalhe(
        id=filme.sk_movie_id,
        titulo=filme.titulo,
        ano=filme.ano_lancamento,
        data_lancamento=filme.data_lancamento,
        duracao_minutos=filme.duracao_minutos or None,
        status=filme.status_filme,
        sinopse=filme.sinopse,
        poster_url=filme.url_poster,
        backdrop_url=filme.url_backdrop,
        generos=[
            GeneroResumo(id=genero.sk_genre_id, nome=genero.nome_genero) for genero in filme.genres
        ],
        diretores=_pessoas(filme, "Diretor"),
        roteiristas=_pessoas(filme, "Roteirista"),
        elenco=_pessoas(filme, "Ator"),
        produtoras=[
            ProdutoraResumo(id=produtora.sk_company_id, nome=produtora.nome_produtora)
            for produtora in filme.companies
        ],
        metricas=_metricas(filme),
        nota_media=agregado.nota_media_usuarios if agregado else None,
        qtd_avaliacoes=agregado.qtd_avaliacoes_usuarios if agregado else 0,
    )


async def obter_detalhe(sessao: AsyncSession, filme_id: str) -> FilmeDetalhe | None:
    filme = await repository.obter_filme(sessao, filme_id)
    return para_detalhe(filme) if filme else None


def para_avaliacao(avaliacao: MovieReview) -> AvaliacaoResumo:
    return AvaliacaoResumo(
        id=avaliacao.sk_movie_review_id,
        nome=avaliacao.nome,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario,
        criado_em=avaliacao.created_at,
    )


async def listar_avaliacoes(
    sessao: AsyncSession, filme_id: str, parametros: ParametrosPaginacao
) -> Pagina[AvaliacaoResumo]:
    total = await repository.contar_avaliacoes(sessao, filme_id)
    avaliacoes = await repository.listar_avaliacoes(
        sessao, filme_id, parametros.offset, parametros.tamanho
    )
    return Pagina.montar([para_avaliacao(item) for item in avaliacoes], total, parametros)
