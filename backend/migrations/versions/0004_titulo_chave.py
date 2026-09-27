"""Acrescenta a chave usada para agrupar os registros repetidos do mesmo filme.

Como a 0003, é uma migração de dados: cria a coluna e preenche as linhas já
existentes. Sem o preenchimento, a busca agruparia todos os filmes numa chave
vazia e devolveria um único resultado por ano e duração.

Não há índice a criar. A coluna só é lida no PARTITION BY da busca, sobre o
conjunto que o LIKE já reduziu, e um índice sobre 95 mil linhas custaria espaço
e escrita sem economizar leitura.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.texto import chave_agrupamento

revision: str = "0004_titulo_chave"
down_revision: str | Sequence[str] | None = "0003_titulo_busca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "dim_movies"
LOTE = 5_000


def upgrade() -> None:
    op.add_column(TABLE_NAME, sa.Column("titulo_chave", sa.String(500), nullable=True))

    conexao = op.get_bind()
    linhas = conexao.execute(sa.text("SELECT sk_movie_id, titulo FROM dim_movies")).fetchall()

    atualizacao = sa.text(
        "UPDATE dim_movies SET titulo_chave = :titulo_chave WHERE sk_movie_id = :sk_movie_id"
    )
    for inicio in range(0, len(linhas), LOTE):
        conexao.execute(
            atualizacao,
            [
                {"sk_movie_id": sk_movie_id, "titulo_chave": chave_agrupamento(titulo)}
                for sk_movie_id, titulo in linhas[inicio : inicio + LOTE]
            ],
        )


def downgrade() -> None:
    op.drop_column(TABLE_NAME, "titulo_chave")
