"""Indexa a ordenação padrão do catálogo.

O catálogo ordena por popularidade decrescente, com a chave do filme como
desempate — necessário porque 86.372 filmes compartilham valor de popularidade,
e sem um critério único a paginação repetiria e omitiria registros.

O índice cobre as duas colunas em ordem ascendente. O SQLite o percorre ao
contrário para atender ``ORDER BY popularidade DESC, sk_movie_id DESC``, o que
dispensa a ordenação temporária das 95 mil linhas do fato a cada página.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_index_popularidade"
down_revision: str | Sequence[str] | None = "0001_initial_movie_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_fact_movies_performance_popularidade"
TABLE_NAME = "fact_movies_performance"


def upgrade() -> None:
    op.create_index(INDEX_NAME, TABLE_NAME, ["popularidade", "sk_movie_id"])


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
