"""Contrato HTTP do domínio de filmes.

Os schemas são deliberadamente planos. A persistência é um esquema estrela, com
o filme espalhado por dimensões, bridges e um fato — mas a API expõe um recurso
``Filme`` coeso, que é o que o consumidor espera. A tradução entre os dois
modelos acontece no serviço, não aqui.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator


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


StatusFilme = Literal["Lançado", "Pós-Produção", "Em Produção", "Planejado"]

# Nome de pessoa ou gênero: espaços nas pontas são removidos antes de qualquer
# comparação. Sem isso, " Nolan" criaria uma segunda linha em `dim_people` ao
# lado de "Nolan", e a dimensão duplicaria por um espaço invisível.
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class FilmeEntrada(BaseModel):
    """Campos que o formulário controla, no cadastro e na atualização.

    Este schema define o **subconjunto editável** do filme. O ``PUT`` substitui
    esse subconjunto inteiro e não toca em nada fora dele: popularidade, notas
    do TMDB e do IMDb, valores financeiros e backdrop continuam como estão,
    porque não são informação que um administrador digita.

    Gêneros e diretores são listas e aceitam vazio, ainda que o enunciado os
    trate como informação básica. O motivo é concreto: 20.037 filmes do acervo
    não têm gênero e 16.181 não têm diretor. Exigi-los aqui tornaria esses
    filmes impossíveis de editar, porque o formulário abriria vazio e o ``PUT``
    recusaria o que ele mesmo carregou.
    """

    titulo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    ano: int | None = Field(default=None, ge=1888, le=2100)
    sinopse: str | None = Field(default=None, max_length=4000)
    duracao_minutos: int | None = Field(default=None, ge=1, le=1000)
    status: StatusFilme | None = None
    poster_url: str | None = Field(default=None, max_length=2048)
    generos: list[Nome] = Field(
        default_factory=list,
        max_length=19,
        description="Nomes de gêneros existentes; valores desconhecidos são recusados.",
    )
    diretores: list[Nome] = Field(
        default_factory=list,
        max_length=10,
        description="Nomes de diretores; os que ainda não existem são criados.",
    )

    @field_validator("generos", "diretores")
    @classmethod
    def _sem_repetidos(cls, valores: list[str]) -> list[str]:
        """Remove repetições preservando a ordem digitada.

        As bridges têm chave primária composta: o mesmo gênero duas vezes na
        mesma requisição violaria a restrição e devolveria 500 em vez de um
        erro de entrada.
        """

        vistos: dict[str, None] = dict.fromkeys(valores)
        return list(vistos)

    @field_validator("sinopse", "poster_url")
    @classmethod
    def _vazio_e_ausente(cls, valor: str | None) -> str | None:
        """Trata texto em branco como ausência.

        Um campo de formulário esvaziado chega como ``""``, e guardar string
        vazia criaria um terceiro estado além de "tem" e "não tem".
        """

        if valor is None:
            return None
        limpo = valor.strip()
        return limpo or None


class AvaliacaoResumo(BaseModel):
    """Avaliação individual feita por um usuário."""

    id: str
    nome: str
    nota: float = Field(description="Nota na escala 0–10.")
    comentario: str
    criado_em: datetime
