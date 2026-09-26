"""Paginação por offset, compartilhada pelos endpoints de listagem.

A escolha por offset (em vez de keyset/cursor) é deliberada: o catálogo precisa
numerar páginas e permitir saltar para uma delas, o que um cursor não oferece.
O custo é um `COUNT` por requisição e a degradação em páginas muito profundas —
irrelevante na escala deste catálogo.
"""

from math import ceil
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")

TAMANHO_PADRAO = 20
TAMANHO_MAXIMO = 100


class ParametrosPaginacao:
    """Parâmetros de paginação resolvidos por injeção de dependência.

    Declarada como classe para que o FastAPI a injete com ``Depends()`` e ainda
    assim documente cada parâmetro no OpenAPI.
    """

    def __init__(
        self,
        pagina: Annotated[int, Query(ge=1, description="Página desejada, começando em 1.")] = 1,
        tamanho: Annotated[
            int,
            Query(ge=1, le=TAMANHO_MAXIMO, description="Quantidade de itens por página."),
        ] = TAMANHO_PADRAO,
    ) -> None:
        self.pagina = pagina
        self.tamanho = tamanho

    @property
    def offset(self) -> int:
        """Quantidade de registros a pular para alcançar a página pedida."""

        return (self.pagina - 1) * self.tamanho


class Pagina(BaseModel, Generic[T]):
    """Envelope padrão das respostas paginadas."""

    items: list[T]
    total: int = Field(description="Total de registros disponíveis.")
    pagina: int = Field(description="Página atual.")
    tamanho: int = Field(description="Itens por página.")
    paginas: int = Field(description="Total de páginas.")

    @classmethod
    def montar(cls, items: list[T], total: int, parametros: ParametrosPaginacao) -> "Pagina[T]":
        return cls(
            items=items,
            total=total,
            pagina=parametros.pagina,
            tamanho=parametros.tamanho,
            paginas=ceil(total / parametros.tamanho) if total else 0,
        )
