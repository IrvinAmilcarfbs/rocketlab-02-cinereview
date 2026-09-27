"""Acrescenta o instante de cadastro dos filmes criados pela aplicação.

Diferente das revisões 0003 e 0004, esta **não** preenche as linhas existentes.
O nulo é a informação: as 95.645 linhas vindas dos CSVs não têm data de cadastro
conhecida, e atribuir uma inventaria um fato. O nulo é justamente o que separa o
acervo carregado do que foi cadastrado aqui.

O índice é parcial. Sobre a coluna inteira ele seria quase todo composto do mesmo
nulo — custo de escrita e espaço sem retorno de leitura.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_criado_em"
down_revision: str | Sequence[str] | None = "0004_titulo_chave"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "dim_movies"
INDEX_NAME = "ix_dim_movies_criado_em"


def upgrade() -> None:
    op.add_column(TABLE_NAME, sa.Column("criado_em", sa.DateTime(), nullable=True))
    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        ["criado_em", "sk_movie_id"],
        sqlite_where=sa.text("criado_em IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
    op.drop_column(TABLE_NAME, "criado_em")
