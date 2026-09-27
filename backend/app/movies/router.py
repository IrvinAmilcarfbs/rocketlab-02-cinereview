"""Endpoints HTTP do catálogo de filmes."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagina, ParametrosPaginacao
from app.db.session import get_db
from app.movies import repository, service
from app.movies.schemas import (
    AvaliacaoResumo,
    FilmeDetalhe,
    FilmeEntrada,
    FilmeResumo,
    GeneroResumo,
)
from app.movies.service import GenerosDesconhecidos, Ordenacao

router = APIRouter()

IdFilme = Annotated[str, Path(description="Chave do filme (sk_movie_id).")]
Sessao = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "",
    response_model=Pagina[FilmeResumo],
    summary="Lista o catálogo paginado",
)
async def listar_filmes(
    parametros: Annotated[ParametrosPaginacao, Depends()],
    sessao: Sessao,
    busca: Annotated[
        str | None,
        Query(
            max_length=200,
            description="Filtra por título; ignora acentos e diferenças de caixa.",
        ),
    ] = None,
    ordenar: Annotated[
        Ordenacao,
        Query(
            description=(
                "Ordem do catálogo. `recentes` exibe primeiro os filmes "
                "cadastrados aqui e depois o acervo por popularidade. "
                "Ignorado quando há busca."
            ),
        ),
    ] = "popularidade",
) -> Pagina[FilmeResumo]:
    """Devolve uma página do catálogo, ordenada por popularidade decrescente.

    Com ``busca`` preenchida, títulos repetidos são agrupados e apenas a entrada
    mais completa de cada grupo aparece.
    """

    return await service.listar_catalogo(sessao, parametros, busca, ordenar)


@router.get(
    "/generos",
    response_model=list[GeneroResumo],
    summary="Lista os gêneros disponíveis",
)
async def listar_generos(sessao: Sessao) -> list[GeneroResumo]:
    """Vocabulário fechado de 19 gêneros, para o formulário de cadastro.

    A rota vem antes de ``/{filme_id}`` de propósito: o FastAPI resolve na ordem
    de declaração, e invertê-las faria "generos" ser lido como identificador de
    filme.
    """

    return await service.listar_generos(sessao)


@router.post(
    "",
    response_model=FilmeDetalhe,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um filme",
    responses={422: {"description": "Entrada inválida ou gênero desconhecido"}},
)
async def criar_filme(
    entrada: Annotated[FilmeEntrada, Body()],
    sessao: Sessao,
) -> FilmeDetalhe:
    """Cria o filme e a linha do fato na mesma transação.

    Responde 201 com a ficha completa, e não apenas com o identificador: o
    cliente redireciona para a ficha logo após salvar, e devolver o recurso
    pronto evita uma segunda requisição.
    """

    try:
        return await service.criar_filme(sessao, entrada)
    except GenerosDesconhecidos as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erro)
        ) from erro


@router.get(
    "/{filme_id}",
    response_model=FilmeDetalhe,
    summary="Detalha um filme",
    responses={404: {"description": "Filme não encontrado"}},
)
async def obter_filme(filme_id: IdFilme, sessao: Sessao) -> FilmeDetalhe:
    """Reúne ficha técnica, equipe, produtoras e métricas de um filme."""

    filme = await service.obter_detalhe(sessao, filme_id)
    if filme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado.")
    return filme


@router.put(
    "/{filme_id}",
    response_model=FilmeDetalhe,
    summary="Atualiza um filme",
    responses={
        404: {"description": "Filme não encontrado"},
        422: {"description": "Entrada inválida ou gênero desconhecido"},
    },
)
async def atualizar_filme(
    filme_id: IdFilme,
    entrada: Annotated[FilmeEntrada, Body()],
    sessao: Sessao,
) -> FilmeDetalhe:
    """Substitui inteiramente o subconjunto de campos que o formulário controla.

    ``PUT`` porque a substituição é total dentro desse subconjunto: o que o
    formulário mostra em branco fica em branco. O que ele não mostra —
    popularidade, notas externas, financeiro, backdrop, elenco, roteiristas e
    produtoras — não é alcançado por esta rota.
    """

    try:
        filme = await service.atualizar_filme(sessao, filme_id, entrada)
    except GenerosDesconhecidos as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erro)
        ) from erro
    if filme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado.")
    return filme


@router.delete(
    "/{filme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um filme",
    responses={404: {"description": "Filme não encontrado"}},
)
async def remover_filme(filme_id: IdFilme, sessao: Sessao) -> Response:
    """Apaga o filme junto com vínculos, métricas e avaliações.

    Responde 204 sem corpo: não há representação a devolver de um recurso que
    deixou de existir. Um filme inexistente resulta em 404, e não em 204 — para
    quem chama, "não havia nada para apagar" é informação diferente de "apagado".
    """

    if not await service.remover_filme(sessao, filme_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{filme_id}/reviews",
    response_model=Pagina[AvaliacaoResumo],
    summary="Lista as avaliações de um filme",
    responses={404: {"description": "Filme não encontrado"}},
)
async def listar_avaliacoes(
    filme_id: IdFilme,
    parametros: Annotated[ParametrosPaginacao, Depends()],
    sessao: Sessao,
) -> Pagina[AvaliacaoResumo]:
    """Devolve as avaliações da mais recente para a mais antiga.

    Um filme existente sem nenhuma avaliação responde com uma página vazia; só
    um filme inexistente resulta em 404. Sem essa distinção, o cliente não
    conseguiria diferenciar "ainda não avaliado" de "não existe".
    """

    if not await repository.filme_existe(sessao, filme_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filme não encontrado.")
    return await service.listar_avaliacoes(sessao, filme_id, parametros)
