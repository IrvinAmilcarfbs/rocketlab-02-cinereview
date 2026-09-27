"""Acrescenta a coluna de título normalizado usada pela busca.

Além de criar a coluna e seu índice, esta revisão preenche as linhas já
existentes — é uma migração de dados, não apenas de schema. Sem isso, um banco
já carregado ficaria com a coluna vazia e a busca não encontraria nada até uma
recarga completa.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.texto import normalizar_busca

revision: str = "0003_titulo_busca"
down_revision: str | Sequence[str] | None = "0002_index_popularidade"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_dim_movies_titulo_busca"
TABLE_NAME = "dim_movies"
LOTE = 5_000


def upgrade() -> None:
    op.add_column(TABLE_NAME, sa.Column("titulo_busca", sa.String(500), nullable=True))

    conexao = op.get_bind()
    linhas = conexao.execute(
        sa.text("SELECT sk_movie_id, titulo FROM dim_movies")
    ).fetchall()

    atualizacao = sa.text(
        "UPDATE dim_movies SET titulo_busca = :titulo_busca WHERE sk_movie_id = :sk_movie_id"
    )
    for inicio in range(0, len(linhas), LOTE):
        conexao.execute(
            atualizacao,
            [
                {"sk_movie_id": sk_movie_id, "titulo_busca": normalizar_busca(titulo)}
                for sk_movie_id, titulo in linhas[inicio : inicio + LOTE]
            ],
        )

    # O índice é criado depois do preenchimento: manter um índice atualizado
    # durante 95 mil UPDATEs custaria mais do que construí-lo de uma vez.
    op.create_index(INDEX_NAME, TABLE_NAME, ["titulo_busca"])


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
    op.drop_column(TABLE_NAME, "titulo_busca")
