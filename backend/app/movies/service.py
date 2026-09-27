"""Regras do catálogo e tradução do esquema estrela para o contrato da API.

Esta camada é a fronteira entre os dois modelos. O banco guarda um filme
espalhado por dimensões e bridges; a API entrega um recurso plano. Concentrar a
tradução aqui evita que o formato do banco vaze para o contrato — e que uma
mudança no contrato exija mexer nas consultas.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagina, ParametrosPaginacao
from app.core.texto import normalizar_busca
from app.movies import repository
from app.movies.models import DimGenre, DimMovie, FactMoviePerformance, MovieReview
from app.movies.schemas import (
    AvaliacaoEntrada,
    AvaliacaoResumo,
    FilmeDetalhe,
    FilmeEntrada,
    FilmeResumo,
    GeneroResumo,
    MetricasFilme,
    PessoaResumo,
    ProdutoraResumo,
)

Ordenacao = Literal["popularidade", "recentes"]

# Papel dos nomes que o formulário envia. A bridge não qualifica a relação: o
# papel mora em `dim_people.tipo_pessoa`, e é ele que separa diretor de ator.
PAPEL_DIRETOR = "Diretor"


class GenerosDesconhecidos(Exception):
    """Algum gênero enviado não existe no vocabulário de 19 valores.

    É erro de entrada, não falha do servidor: o roteador o traduz em 422. Criar
    o gênero faltante seria pior — bastaria um erro de digitação para nascer um
    vigésimo gênero e contaminar a dimensão para sempre.
    """

    def __init__(self, nomes: list[str]) -> None:
        self.nomes = nomes
        super().__init__(f"Gêneros desconhecidos: {', '.join(nomes)}")


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


async def _pagina_por_recentes(
    sessao: AsyncSession, parametros: ParametrosPaginacao
) -> list[DimMovie]:
    """Pagina sobre a concatenação de duas ordenações.

    "Adicionados recentemente" significa: primeiro o que foi cadastrado aqui,
    do mais novo para o mais antigo; depois o acervo carregado, na ordem padrão
    de popularidade. As 95.645 linhas dos CSVs não têm data de cadastro, e
    ordená-las por um nulo comum devolveria uma lista embaralhada.

    Isso não pode ser um único ``ORDER BY``: a primeira chave vive em
    ``dim_movies`` e a segunda no fato, e nenhum índice cobre as duas tabelas.
    Uma ordenação mista forçaria o SQLite a ordenar 95 mil linhas a cada página
    — exatamente a regressão de 2.165 ms medida na Etapa 2. Concatenar duas
    consultas rápidas troca essa ordenação por aritmética de deslocamento.

    A fronteira entre os blocos é o único ponto delicado: uma página pode
    começar no primeiro bloco e terminar no segundo.
    """

    cadastrados = await repository.contar_cadastrados(sessao)
    offset, tamanho = parametros.offset, parametros.tamanho

    if offset >= cadastrados:
        # A página inteira cai no acervo; o deslocamento desconta o bloco anterior.
        return list(
            await repository.listar_filmes(
                sessao, offset - cadastrados, tamanho, somente_acervo=True
            )
        )

    recentes = list(await repository.listar_cadastrados(sessao, offset, tamanho))
    faltam = tamanho - len(recentes)
    if faltam <= 0:
        return recentes

    # Página de fronteira: completa com o começo do acervo.
    complemento = await repository.listar_filmes(sessao, 0, faltam, somente_acervo=True)
    return [*recentes, *complemento]


async def listar_catalogo(
    sessao: AsyncSession,
    parametros: ParametrosPaginacao,
    busca: str | None = None,
    ordenar: Ordenacao = "popularidade",
) -> Pagina[FilmeResumo]:
    """Monta uma página do catálogo, filtrada por título quando houver busca.

    O termo digitado passa pela mesma normalização aplicada a ``titulo_busca``
    na carga — é o que permite "cancao" encontrar "Canção". Um termo que sobra
    vazio depois disso (só espaços, por exemplo) equivale a não buscar.

    ``ordenar`` vale apenas para o catálogo sem busca. Durante uma busca a ordem
    segue a popularidade dentro dos grupos de título repetido, e trocá-la
    exigiria refazer o agrupamento em outra chave sem ganho para quem procura um
    título específico.
    """

    termo = normalizar_busca(busca) if busca else ""

    if termo:
        total = await repository.contar_busca(sessao, termo)
        filmes: Sequence[DimMovie] = await repository.buscar_filmes(
            sessao, termo, parametros.offset, parametros.tamanho
        )
    elif ordenar == "recentes":
        total = await repository.contar_filmes(sessao)
        filmes = await _pagina_por_recentes(sessao, parametros)
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
    """Achata uma avaliação no item exibido, marcando o instante como UTC.

    ``created_at`` usa ``server_default=func.now()``, que no SQLite é
    ``CURRENT_TIMESTAMP`` — sempre UTC — e volta do banco como data-hora **sem
    fuso**. Serializada assim, o JavaScript a interpretaria como hora local:
    em UTC-3, uma avaliação criada agora apareceria três horas no futuro.

    Marcar o fuso aqui é o que torna o instante interpretável fora do servidor.
    Vale para as 43.666 linhas carregadas também, porque elas receberam o mesmo
    ``CURRENT_TIMESTAMP`` no momento da carga.
    """

    return AvaliacaoResumo(
        id=avaliacao.sk_movie_review_id,
        nome=avaliacao.nome,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario,
        criado_em=avaliacao.created_at.replace(tzinfo=UTC),
    )


async def listar_avaliacoes(
    sessao: AsyncSession, filme_id: str, parametros: ParametrosPaginacao
) -> Pagina[AvaliacaoResumo]:
    total = await repository.contar_avaliacoes(sessao, filme_id)
    avaliacoes = await repository.listar_avaliacoes(
        sessao, filme_id, parametros.offset, parametros.tamanho
    )
    return Pagina.montar([para_avaliacao(item) for item in avaliacoes], total, parametros)


async def listar_generos(sessao: AsyncSession) -> list[GeneroResumo]:
    """Vocabulário de gêneros, para o formulário oferecer uma escolha fechada."""

    generos = await repository.listar_generos(sessao)
    return [GeneroResumo(id=genero.sk_genre_id, nome=genero.nome_genero) for genero in generos]


async def _resolver_generos(sessao: AsyncSession, nomes: list[str]) -> list[DimGenre]:
    """Traduz nomes de gênero em entidades, recusando os desconhecidos."""

    generos = await repository.buscar_generos_por_nome(sessao, nomes)
    if len(generos) != len(nomes):
        achados = {genero.nome_genero for genero in generos}
        raise GenerosDesconhecidos([nome for nome in nomes if nome not in achados])
    return list(generos)


async def _aplicar_entrada(sessao: AsyncSession, filme: DimMovie, entrada: FilmeEntrada) -> None:
    """Escreve o subconjunto editável no filme, resolvendo as dimensões.

    Os gêneros são resolvidos antes de qualquer alteração: se um nome for
    inválido, nada foi modificado ainda e a transação morre sem efeito colateral.
    """

    generos = await _resolver_generos(sessao, entrada.generos)
    diretores = [
        await repository.obter_ou_criar_pessoa(sessao, nome, PAPEL_DIRETOR)
        for nome in entrada.diretores
    ]

    filme.titulo = entrada.titulo
    filme.ano_lancamento = entrada.ano
    filme.sinopse = entrada.sinopse
    filme.duracao_minutos = entrada.duracao_minutos
    filme.status_filme = entrada.status
    filme.url_poster = entrada.poster_url
    filme.genres = generos

    # Substituir `filme.people` inteiro apagaria o elenco e os roteiristas, que
    # o formulário não controla — um filme do acervo pode ter 150 pessoas
    # creditadas. A troca alcança apenas as linhas de papel "Diretor".
    outros_papeis = [pessoa for pessoa in filme.people if pessoa.tipo_pessoa != PAPEL_DIRETOR]
    filme.people = [*outros_papeis, *diretores]


async def criar_filme(sessao: AsyncSession, entrada: FilmeEntrada) -> FilmeDetalhe:
    """Cadastra um filme, gravando as cinco tabelas numa única transação.

    Dois cuidados que o esquema estrela impõe:

    * A linha do fato é criada junto, ainda que vazia. A listagem do catálogo
      usa join interno com ``fact_movies_performance``, então um filme sem fato
      existiria no banco e seria invisível no catálogo.
    * ``id_filme`` recebe o prefixo ``local-``. É a chave natural da dimensão, e
      todos os 95.645 valores existentes são identificadores numéricos do TMDB;
      o prefixo registra a procedência no próprio dado e afasta qualquer
      colisão com um identificador de origem.

    ``criado_em`` é o que torna o filme encontrável: é a chave da ordenação por
    recentes, e permanece nulo no acervo carregado.
    """

    filme = DimMovie(
        id_filme=f"local-{uuid4().hex}",
        criado_em=datetime.now(UTC).replace(tzinfo=None),
    )
    filme.performance = FactMoviePerformance()
    await _aplicar_entrada(sessao, filme, entrada)
    await repository.gravar_filme(sessao, filme)

    # Relê com todas as relações carregadas. Devolver o objeto recém-gravado
    # convidaria a um carregamento tardio de `reviews_summary`, que nunca foi
    # atribuído — e carregamento tardio em sessão assíncrona é exceção, não
    # consulta silenciosa.
    return await _detalhe_obrigatorio(sessao, filme.sk_movie_id)


async def atualizar_filme(
    sessao: AsyncSession, filme_id: str, entrada: FilmeEntrada
) -> FilmeDetalhe | None:
    """Substitui o subconjunto editável de um filme existente.

    Nada fora desse subconjunto é tocado: popularidade, notas externas, valores
    financeiros, backdrop, elenco, roteiristas e produtoras permanecem como
    estavam. É o que distingue "o formulário substitui o que ele mostra" de "o
    formulário apaga o que ele não mostra".
    """

    filme = await repository.obter_filme_para_edicao(sessao, filme_id)
    if filme is None:
        return None

    await _aplicar_entrada(sessao, filme, entrada)
    await repository.confirmar(sessao)
    return await _detalhe_obrigatorio(sessao, filme_id)


async def _detalhe_obrigatorio(sessao: AsyncSession, filme_id: str) -> FilmeDetalhe:
    filme = await repository.obter_filme(sessao, filme_id)
    if filme is None:  # pragma: no cover - a transação acabou de gravá-lo
        raise RuntimeError(f"Filme {filme_id!r} desapareceu após a gravação.")
    return para_detalhe(filme)


async def remover_filme(sessao: AsyncSession, filme_id: str) -> bool:
    """Apaga o filme e tudo que depende dele. Devolve se o filme existia."""

    return await repository.remover_filme(sessao, filme_id)


async def criar_avaliacao(
    sessao: AsyncSession, filme_id: str, entrada: AvaliacaoEntrada
) -> AvaliacaoResumo | None:
    """Registra uma avaliação. Devolve ``None`` se o filme não existir.

    A existência do filme é verificada antes da escrita. A chave estrangeira
    também a garantiria, mas o erro chegaria como falha de integridade — e o
    cliente precisa distinguir "esse filme não existe" de "algo deu errado".
    """

    if not await repository.filme_existe(sessao, filme_id):
        return None

    avaliacao = await repository.criar_avaliacao(
        sessao,
        filme_id,
        nome=entrada.nome,
        nota=entrada.nota,
        comentario=entrada.comentario,
    )
    return para_avaliacao(avaliacao)


async def remover_avaliacao(sessao: AsyncSession, filme_id: str, avaliacao_id: str) -> bool:
    """Apaga uma avaliação do filme. Devolve se havia o que apagar."""

    avaliacao = await repository.obter_avaliacao(sessao, filme_id, avaliacao_id)
    if avaliacao is None:
        return False

    await repository.remover_avaliacao(sessao, avaliacao)
    return True
