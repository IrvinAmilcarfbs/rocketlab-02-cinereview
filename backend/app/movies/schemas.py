"""Contrato HTTP do domínio de filmes.

Os schemas são deliberadamente planos. A persistência é um esquema estrela, com
o filme espalhado por dimensões, bridges e um fato — mas a API expõe um recurso
``Filme`` coeso, que é o que o consumidor espera. A tradução entre os dois
modelos acontece no serviço, não aqui.
"""

from pydantic import BaseModel, Field


class GeneroResumo(BaseModel):
    """Gênero associado a um filme."""

    id: str
    nome: str


class FilmeResumo(BaseModel):
    """Item do catálogo paginado.

    Traz apenas o necessário para montar um card. A sinopse fica de fora por
    peso (até 4.000 caracteres por filme) e o elenco, para a tela de detalhe.
    """

    id: str
    titulo: str
    ano: int | None = None
    poster_url: str | None = None
    generos: list[GeneroResumo] = Field(default_factory=list)
    nota_media: float | None = Field(
        default=None, description="Média das avaliações na escala 0–10; nulo se não houver."
    )
    qtd_avaliacoes: int = Field(default=0, description="Quantidade de avaliações recebidas.")
