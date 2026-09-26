"""Contrato HTTP do domínio de filmes.

Os schemas são deliberadamente planos. A persistência é um esquema estrela, com
o filme espalhado por dimensões, bridges e um fato — mas a API expõe um recurso
``Filme`` coeso, que é o que o consumidor espera. A tradução entre os dois
modelos acontece no serviço, não aqui.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class GeneroResumo(BaseModel):
    """Gênero associado a um filme."""

    id: str
    nome: str


class PessoaResumo(BaseModel):
    """Pessoa creditada em um filme, já separada por papel no serviço."""

    id: str
    nome: str


class ProdutoraResumo(BaseModel):
    """Produtora ou estúdio associado ao filme."""

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


class MetricasFilme(BaseModel):
    """Métricas externas e financeiras vindas da tabela fato.

    Todos os campos são opcionais porque a cobertura varia muito: as notas
    externas existem para a maioria dos filmes, enquanto orçamento e receita
    aparecem em menos de 10% do catálogo.
    """

    popularidade: float | None = None
    nota_tmdb: float | None = None
    qtd_tmdb: int | None = None
    nota_imdb: float | None = None
    qtd_imdb: int | None = None
    orcamento_usd: float | None = None
    receita_usd: float | None = None
    lucro_usd: float | None = None


class FilmeDetalhe(BaseModel):
    """Ficha completa de um filme.

    Reúne em um único recurso o que o banco mantém espalhado por três bridges,
    uma tabela fato e um agregado.
    """

    id: str
    titulo: str
    ano: int | None = None
    data_lancamento: date | None = None
    duracao_minutos: int | None = None
    status: str | None = None
    sinopse: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None

    generos: list[GeneroResumo] = Field(default_factory=list)
    diretores: list[PessoaResumo] = Field(default_factory=list)
    roteiristas: list[PessoaResumo] = Field(default_factory=list)
    elenco: list[PessoaResumo] = Field(default_factory=list)
    produtoras: list[ProdutoraResumo] = Field(default_factory=list)

    metricas: MetricasFilme | None = None
    nota_media: float | None = None
    qtd_avaliacoes: int = 0


class AvaliacaoResumo(BaseModel):
    """Avaliação individual feita por um usuário."""

    id: str
    nome: str
    nota: float = Field(description="Nota na escala 0–10.")
    comentario: str
    criado_em: datetime
