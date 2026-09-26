"""Gera uma amostra reduzida dos CSVs oficiais preservando integridade referencial.

Executado uma única vez pelo mantenedor: lê a base completa em ``data/full`` e
escreve o recorte em ``data/sample``, que é versionado para que o projeto rode
logo após o clone.

O ponto delicado é a ordem das operações. Recortar as primeiras N linhas de cada
arquivo produziria chaves estrangeiras órfãs — avaliações apontando para filmes
ausentes, bridges apontando para pessoas inexistentes. Como o banco liga
``PRAGMA foreign_keys=ON`` em toda conexão, a carga falharia. Por isso o recorte
segue o grafo do schema: sorteia filmes, filtra as bridges por eles e só então
filtra as dimensões pelos identificadores que sobraram nas bridges.
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from random import Random

# O campo `sinopse` de alguns filmes ultrapassa o limite padrão do módulo csv.
csv.field_size_limit(10_000_000)

DIM_MOVIES = "dim_movies.csv"
DIM_GENRES = "dim_genres.csv"
DIM_COMPANIES = "dim_companies.csv"
DIM_PEOPLE = "dim_people.csv"
DIM_REVIEWS = "dim_reviews.csv"
BRIDGE_GENRE = "bridge_movie_genre.csv"
BRIDGE_COMPANY = "bridge_movie_company.csv"
BRIDGE_PERSON = "bridge_movie_person.csv"
FACT_PERFORMANCE = "fact_movies_performance.csv"
MOVIE_REVIEWS = "movies_reviews.csv"

ARQUIVOS_ESPERADOS = (
    DIM_MOVIES,
    DIM_GENRES,
    DIM_COMPANIES,
    DIM_PEOPLE,
    DIM_REVIEWS,
    BRIDGE_GENRE,
    BRIDGE_COMPANY,
    BRIDGE_PERSON,
    FACT_PERFORMANCE,
    MOVIE_REVIEWS,
)

QTD_FILMES_PADRAO = 2_000
SEMENTE_PADRAO = 42


def localizar_csvs(origem: Path) -> dict[str, Path]:
    """Mapeia cada CSV esperado para seu caminho real dentro de ``origem``.

    A busca é recursiva porque os arquivos oficiais chegam distribuídos em
    subpastas (``bases-1/`` e ``bases-2/``), mas nada impede que sejam copiados
    soltos na raiz.
    """

    encontrados: dict[str, Path] = {}
    for caminho in origem.rglob("*.csv"):
        if caminho.name in ARQUIVOS_ESPERADOS and caminho.name not in encontrados:
            encontrados[caminho.name] = caminho

    ausentes = [nome for nome in ARQUIVOS_ESPERADOS if nome not in encontrados]
    if ausentes:
        raise SystemExit(
            f"CSVs não encontrados em {origem}: {', '.join(ausentes)}\n"
            "Coloque os 10 arquivos oficiais nessa pasta (subpastas são aceitas)."
        )
    return encontrados


def abrir_leitura(caminho: Path):
    return caminho.open("r", encoding="utf-8", newline="")


def abrir_escrita(caminho: Path):
    return caminho.open("w", encoding="utf-8", newline="")


def contar_reviews_por_filme(caminho: Path) -> Counter[str]:
    """Conta avaliações individuais por filme, para guiar a amostragem."""

    contagem: Counter[str] = Counter()
    with abrir_leitura(caminho) as arquivo:
        for linha in csv.DictReader(arquivo):
            contagem[linha["sk_movie_id"]] += 1
    return contagem


def selecionar_filmes(
    caminho: Path, reviews_por_filme: Counter[str], quantidade: int, semente: int
) -> set[str]:
    """Sorteia filmes priorizando os que rendem uma demonstração completa.

    A amostra é enviesada de propósito: um sorteio uniforme sobre os 95 mil
    filmes encheria o catálogo de registros sem pôster, sem sinopse e sem
    nenhuma avaliação. Os candidatos são separados em faixas de qualidade e
    sorteados em ordem de preferência, com semente fixa para que o recorte seja
    reprodutível.
    """

    completos: list[str] = []
    com_avaliacao: list[str] = []
    com_midia: list[str] = []
    restantes: list[str] = []

    with abrir_leitura(caminho) as arquivo:
        for linha in csv.DictReader(arquivo):
            sk_movie_id = linha["sk_movie_id"]
            tem_avaliacao = reviews_por_filme[sk_movie_id] > 0
            tem_midia = bool(linha["sinopse"].strip()) and bool(linha["url_poster"].strip())

            if tem_avaliacao and tem_midia:
                completos.append(sk_movie_id)
            elif tem_avaliacao:
                com_avaliacao.append(sk_movie_id)
            elif tem_midia:
                com_midia.append(sk_movie_id)
            else:
                restantes.append(sk_movie_id)

    gerador = Random(semente)
    selecionados: list[str] = []
    for faixa in (completos, com_avaliacao, com_midia, restantes):
        if len(selecionados) >= quantidade:
            break
        gerador.shuffle(faixa)
        selecionados.extend(faixa[: quantidade - len(selecionados)])

    print(
        f"  faixas disponíveis: {len(completos)} completos, "
        f"{len(com_avaliacao)} só com avaliação, {len(com_midia)} só com mídia"
    )
    return set(selecionados)


def filtrar(
    origem: Path,
    destino: Path,
    coluna_filtro: str,
    aceitos: set[str],
    coluna_coletada: str | None = None,
) -> set[str]:
    """Copia as linhas cujo ``coluna_filtro`` pertence a ``aceitos``.

    Quando ``coluna_coletada`` é informada, devolve os valores dessa coluna nas
    linhas mantidas — é assim que as bridges revelam quais gêneros, produtoras e
    pessoas precisam sobreviver ao recorte.
    """

    coletados: set[str] = set()
    mantidas = 0

    with abrir_leitura(origem) as entrada, abrir_escrita(destino) as saida:
        leitor = csv.DictReader(entrada)
        if leitor.fieldnames is None:
            raise SystemExit(f"Arquivo sem cabeçalho: {origem}")

        escritor = csv.DictWriter(saida, fieldnames=leitor.fieldnames)
        escritor.writeheader()
        for linha in leitor:
            if linha[coluna_filtro] not in aceitos:
                continue
            escritor.writerow(linha)
            mantidas += 1
            if coluna_coletada:
                coletados.add(linha[coluna_coletada])

    print(f"  {destino.name}: {mantidas} linhas")
    return coletados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    raiz_backend = Path(__file__).resolve().parent.parent
    parser.add_argument("--origem", type=Path, default=raiz_backend / "data" / "full")
    parser.add_argument("--destino", type=Path, default=raiz_backend / "data" / "sample")
    parser.add_argument("--filmes", type=int, default=QTD_FILMES_PADRAO)
    parser.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    args = parser.parse_args()

    origem: Path = args.origem
    destino: Path = args.destino
    if not origem.is_dir():
        raise SystemExit(f"Pasta de origem não encontrada: {origem}")
    destino.mkdir(parents=True, exist_ok=True)

    csvs = localizar_csvs(origem)
    print(f"Lendo base completa de {origem}")

    print("Contando avaliações por filme...")
    reviews_por_filme = contar_reviews_por_filme(csvs[MOVIE_REVIEWS])

    print(f"Sorteando {args.filmes} filmes (semente {args.semente})...")
    filmes = selecionar_filmes(csvs[DIM_MOVIES], reviews_por_filme, args.filmes, args.semente)
    print(f"  {len(filmes)} filmes selecionados")

    print("Recortando filmes e tabelas dependentes...")
    filtrar(csvs[DIM_MOVIES], destino / DIM_MOVIES, "sk_movie_id", filmes)
    filtrar(csvs[FACT_PERFORMANCE], destino / FACT_PERFORMANCE, "sk_movie_id", filmes)
    filtrar(csvs[DIM_REVIEWS], destino / DIM_REVIEWS, "sk_movie_id", filmes)
    filtrar(csvs[MOVIE_REVIEWS], destino / MOVIE_REVIEWS, "sk_movie_id", filmes)

    # As bridges são filtradas pelos filmes e, de quebra, informam quais
    # registros das dimensões continuam sendo referenciados.
    print("Recortando bridges...")
    generos = filtrar(
        csvs[BRIDGE_GENRE], destino / BRIDGE_GENRE, "sk_movie_id", filmes, "sk_genre_id"
    )
    produtoras = filtrar(
        csvs[BRIDGE_COMPANY], destino / BRIDGE_COMPANY, "sk_movie_id", filmes, "sk_company_id"
    )
    pessoas = filtrar(
        csvs[BRIDGE_PERSON], destino / BRIDGE_PERSON, "sk_movie_id", filmes, "sk_person_id"
    )

    print("Recortando dimensões pelo que as bridges referenciam...")
    filtrar(csvs[DIM_GENRES], destino / DIM_GENRES, "sk_genre_id", generos)
    filtrar(csvs[DIM_COMPANIES], destino / DIM_COMPANIES, "sk_company_id", produtoras)
    filtrar(csvs[DIM_PEOPLE], destino / DIM_PEOPLE, "sk_person_id", pessoas)

    total_bytes = sum(caminho.stat().st_size for caminho in destino.glob("*.csv"))
    print(f"\nAmostra gravada em {destino} ({total_bytes / 1_048_576:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
