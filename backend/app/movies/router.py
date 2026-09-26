"""Endpoints HTTP do catálogo de filmes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagina, ParametrosPaginacao
from app.db.session import get_db
from app.movies import service
from app.movies.schemas import FilmeResumo

router = APIRouter()


@router.get(
    "",
    response_model=Pagina[FilmeResumo],
    summary="Lista o catálogo paginado",
)
async def listar_filmes(
    parametros: Annotated[ParametrosPaginacao, Depends()],
    sessao: Annotated[AsyncSession, Depends(get_db)],
) -> Pagina[FilmeResumo]:
    """Devolve uma página do catálogo, ordenada por popularidade decrescente."""

    return await service.listar_catalogo(sessao, parametros)
