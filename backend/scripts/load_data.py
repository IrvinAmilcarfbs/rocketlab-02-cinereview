"""Carrega os CSVs do catálogo no banco criado pelo Alembic.

Usa ``data/full`` quando há CSVs lá e ``data/sample`` caso contrário, de modo
que um clone recém-feito já sobe com dados. As flags ``--full`` e ``--sample``
forçam uma das origens.

Duas escolhas deste script merecem explicação:

* **Conexão síncrona.** A aplicação é toda assíncrona (``aiosqlite``), mas
  inserir 745 mil linhas pelo ORM assíncrono, uma a uma, levaria horas. A carga
  abre sua própria engine síncrona e usa ``executemany`` em lotes.
* **A ``dim_reviews`` é recalculada, não importada.** Na base oficial esse
  agregado está dessincronizado: 14.561 filmes possuem avaliação individual sem
  linha correspondente, e 898 linhas apontam para filmes sem nenhuma avaliação.
  Derivá-lo de ``movie_reviews`` faz o banco nascer consistente e usa a mesma
  regra que a API aplicará a cada nova avaliação.

O schema é responsabilidade exclusiva do Alembic; este script apenas insere
dados e aborta se as tabelas ainda não existirem.
"""

import argparse
import csv
import sys
import time
from collections.abc import Callable, Iterator
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import Date, Float, Integer, Numeric, Table, create_engine, event, inspect, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.db.base import Base
from app.movies import models  # noqa: F401  (registra as tabelas em Base.metadata)

csv.field_size_limit(10_000_000)

# Ordem de inserção compatível com as chaves estrangeiras: dimensões, depois
# filmes, depois tudo que depende deles. `dim_reviews` fica de fora de propósito.
CARGA: tuple[tuple[str, str], ...] = (
    ("dim_genres.csv", "dim_genres"),
    ("dim_companies.csv", "dim_companies"),
    ("dim_people.csv", "dim_people"),
    ("dim_movies.csv", "dim_movies"),
    ("fact_movies_performance.csv", "fact_movies_performance"),
    ("bridge_movie_genre.csv", "bridge_movie_genre"),
    ("bridge_movie_company.csv", "bridge_movie_company"),
    ("bridge_movie_person.csv", "bridge_movie_person"),
    ("movies_reviews.csv", "movie_reviews"),
)

TAMANHO_LOTE_PADRAO = 5_000


def _texto(valor: str) -> str | None:
    limpo = valor.strip()
    return limpo or None


def _inteiro(valor: str) -> int | None:
    limpo = valor.strip()
    if not limpo:
        return None
    # Os CSVs exportam inteiros em notação decimal ("2375.0").
    return int(float(limpo))


def _flutuante(valor: str) -> float | None:
    limpo = valor.strip()
    return float(limpo) if limpo else None


def _decimal(valor: str) -> Decimal | None:
    limpo = valor.strip()
    if not limpo:
        return None
    try:
        return Decimal(limpo)
    except InvalidOperation:
        return None


def _data(valor: str) -> date | None:
    limpo = valor.strip()
    if not limpo:
        return None
    try:
        return date.fromisoformat(limpo)
    except ValueError:
        return None


def conversores_da_tabela(tabela: Table) -> dict[str, Callable[[str], object]]:
    """Escolhe um conversor por coluna a partir do tipo declarado no ORM.

    Sem isso o SQLite aceitaria string vazia numa coluna numérica e gravaria
    ``''`` em vez de ``NULL``, corrompendo silenciosamente as médias.
    """

    mapa: dict[str, Callable[[str], object]] = {}
    for coluna in tabela.columns:
        tipo = coluna.type
        if isinstance(tipo, Integer):
            mapa[coluna.name] = _inteiro
        elif isinstance(tipo, Date):
            mapa[coluna.name] = _data
        elif isinstance(tipo, Float):  # Double herda de Float
            mapa[coluna.name] = _flutuante
        elif isinstance(tipo, Numeric):
            mapa[coluna.name] = _decimal
        else:
            mapa[coluna.name] = _texto
    return mapa


def ler_lotes(caminho: Path, tabela: Table, tamanho: int) -> Iterator[list[dict[str, object]]]:
    """Percorre o CSV em lotes, convertendo cada campo para o tipo da coluna."""

    conversores = conversores_da_tabela(tabela)
    colunas = set(tabela.columns.keys())

    with caminho.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames is None:
            raise SystemExit(f"Arquivo sem cabeçalho: {caminho}")

        ignoradas = [nome for nome in leitor.fieldnames if nome not in colunas]
        if ignoradas:
            print(f"    aviso: colunas ignoradas em {caminho.name}: {', '.join(ignoradas)}")

        lote: list[dict[str, object]] = []
        for linha in leitor:
            lote.append(
                {
                    nome: conversores[nome](valor or "")
                    for nome, valor in linha.items()
                    if nome in colunas
                }
            )
            if len(lote) >= tamanho:
                yield lote
                lote = []
        if lote:
            yield lote


def localizar_csvs(origem: Path) -> dict[str, Path]:
    """Mapeia os CSVs de ``origem``, aceitando arquivos em subpastas."""

    encontrados: dict[str, Path] = {}
    for caminho in origem.rglob("*.csv"):
        encontrados.setdefault(caminho.name, caminho)
    return encontrados


def url_sincrona(url: str, raiz: Path) -> str:
    """Converte a URL assíncrona da aplicação em equivalente síncrona.

    O caminho relativo é resolvido contra a raiz do backend para que a carga
    atinja o mesmo arquivo que o Alembic, independente do diretório atual.
    """

    url = url.replace("+aiosqlite", "")
    prefixo = "sqlite:///"
    if not url.startswith(prefixo):
        return url

    caminho = url[len(prefixo) :]
    if caminho == ":memory:" or Path(caminho).is_absolute():
        return url
    return prefixo + str((raiz / caminho).resolve())


def criar_engine(url: str) -> Engine:
    """Cria a engine de carga com PRAGMAs voltados para escrita em massa."""

    motor = create_engine(url, echo=False, future=True)

    @event.listens_for(motor, "connect")
    def _configurar(dbapi_connection: object, connection_record: object) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        # As FKs ficam desligadas durante a inserção e são conferidas ao final
        # com PRAGMA foreign_key_check — prática usual de carga em lote.
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.close()

    return motor


def verificar_schema(motor: Engine) -> None:
    existentes = set(inspect(motor).get_table_names())
    faltando = [t.name for t in Base.metadata.sorted_tables if t.name not in existentes]
    if faltando:
        raise SystemExit(
            f"Tabelas ausentes no banco: {', '.join(faltando)}\n"
            "Rode as migrações antes da carga:  alembic upgrade head"
        )


def limpar_tabelas(motor: Engine) -> None:
    """Esvazia as tabelas na ordem inversa das dependências (recarga total)."""

    with motor.begin() as conexao:
        for tabela in reversed(Base.metadata.sorted_tables):
            conexao.execute(tabela.delete())


def carregar_tabela(motor: Engine, caminho: Path, tabela: Table, tamanho_lote: int) -> int:
    total = 0
    with motor.begin() as conexao:
        for lote in ler_lotes(caminho, tabela, tamanho_lote):
            conexao.execute(tabela.insert(), lote)
            total += len(lote)
    return total


def recalcular_dim_reviews(motor: Engine) -> int:
    """Deriva o agregado de avaliações a partir das avaliações individuais.

    Mantém a convenção da base oficial de usar o próprio ``sk_movie_id`` como
    chave do agregado, o que torna o resultado determinístico.
    """

    with motor.begin() as conexao:
        conexao.execute(text("DELETE FROM dim_reviews"))
        conexao.execute(
            text(
                """
                INSERT INTO dim_reviews (
                    sk_review_id, sk_movie_id, qtd_avaliacoes_usuarios, nota_media_usuarios
                )
                SELECT sk_movie_id, sk_movie_id, COUNT(*), AVG(nota)
                FROM movie_reviews
                GROUP BY sk_movie_id
                """
            )
        )
        return conexao.execute(text("SELECT COUNT(*) FROM dim_reviews")).scalar_one()


def verificar_integridade(motor: Engine) -> None:
    with motor.connect() as conexao:
        violacoes = conexao.execute(text("PRAGMA foreign_key_check")).fetchall()
    if violacoes:
        raise SystemExit(f"Integridade referencial violada em {len(violacoes)} linha(s).")
    print("  integridade referencial conferida: nenhuma violação")


def resolver_origem(raiz: Path, modo: str, explicita: Path | None = None) -> Path:
    completa = raiz / "data" / "full"
    amostra = raiz / "data" / "sample"

    if explicita is not None:
        escolhida = explicita
    elif modo == "full":
        escolhida = completa
    elif modo == "sample":
        escolhida = amostra
    else:
        escolhida = completa if localizar_csvs(completa) else amostra

    if not localizar_csvs(escolhida):
        raise SystemExit(
            f"Nenhum CSV encontrado em {escolhida}.\n"
            "Para a base completa, copie os 10 arquivos oficiais para data/full/."
        )
    return escolhida


def main() -> int:
    raiz_backend = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Carga dos CSVs do catálogo de filmes.")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--full", action="store_const", const="full", dest="modo", help="força data/full"
    )
    grupo.add_argument(
        "--sample", action="store_const", const="sample", dest="modo", help="força data/sample"
    )
    parser.add_argument("--origem", type=Path, default=None, help="pasta alternativa com os CSVs")
    parser.add_argument("--lote", type=int, default=TAMANHO_LOTE_PADRAO)
    parser.set_defaults(modo="auto")
    args = parser.parse_args()

    origem = resolver_origem(raiz_backend, args.modo, args.origem)
    csvs = localizar_csvs(origem)

    ausentes = [nome for nome, _ in CARGA if nome not in csvs]
    if ausentes:
        raise SystemExit(f"CSVs ausentes em {origem}: {', '.join(ausentes)}")

    url = url_sincrona(get_settings().database_url, raiz_backend)
    motor = criar_engine(url)
    verificar_schema(motor)

    print(f"Carregando CSVs de {origem}")
    inicio = time.perf_counter()

    print("Limpando tabelas...")
    limpar_tabelas(motor)

    for nome_arquivo, nome_tabela in CARGA:
        tabela = Base.metadata.tables[nome_tabela]
        total = carregar_tabela(motor, csvs[nome_arquivo], tabela, args.lote)
        print(f"  {nome_tabela}: {total} linhas")

    print("Recalculando dim_reviews a partir de movie_reviews...")
    agregados = recalcular_dim_reviews(motor)
    print(f"  dim_reviews: {agregados} linhas")

    verificar_integridade(motor)
    motor.dispose()

    print(f"\nCarga concluída em {time.perf_counter() - inicio:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
