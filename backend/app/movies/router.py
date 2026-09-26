"""Endpoints HTTP do catálogo de filmes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagina, ParametrosPaginacao
from app.db.session import get_db
from app.movies import repository, service
from app.movies.schemas import AvaliacaoResumo, FilmeDetalhe, FilmeResumo

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
) -> Pagina[FilmeResumo]:
    """Devolve uma página do catálogo, ordenada por popularidade decrescente."""

    return await service.listar_catalogo(sessao, parametros)


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
