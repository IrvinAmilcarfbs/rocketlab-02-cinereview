# Cinelog — sistema de avaliação de filmes

Atividade 02 (DEV) do Rocket Lab 2026 da Visagio. Um catálogo de filmes
inspirado no Letterboxd, onde o usuário atua como administrador: cadastra,
edita e remove filmes, navega por um catálogo paginado, busca por título,
avalia com nota e resenha e acompanha a média de cada filme.

O catálogo real tem **95.645 filmes** e **43.666 avaliações** vindos dos CSVs
oficiais da atividade. O repositório já traz uma amostra de 2.000 filmes
versionada, então um clone recém-feito sobe com dados de verdade — sem precisar
baixar nada.

| Camada | Tecnologia |
|---|---|
| Frontend | Vite + React 19 + TypeScript |
| Backend | FastAPI + SQLAlchemy 2.0 (assíncrono) |
| Banco | SQLite, migrado com Alembic |

---

## Pré-requisitos

- **Python 3.11 ou superior** (testado em 3.13)
- **Node.js 20.19+ ou 22.12+** (testado em 22.14) — exigência do Vite 8

Nada além disso. O banco é um arquivo SQLite criado pelas migrações, e os dados
já estão no repositório.

---

## Execução

São dois processos: a API e o servidor de desenvolvimento do front. Abra **dois
terminais**.

### 1. Backend

```bash
cd backend
```

Crie o ambiente virtual e instale as dependências:

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env

# Linux / macOS
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

Crie o schema do banco:

```bash
# Windows
.venv\Scripts\python -m alembic upgrade head

# Linux / macOS
.venv/bin/python -m alembic upgrade head
```

Carregue os dados:

```bash
# Windows
.venv\Scripts\python scripts\load_data.py

# Linux / macOS
.venv/bin/python scripts/load_data.py
```

A saída esperada:

```
Carregando CSVs de .../backend/data/sample
  dim_genres: 19 linhas
  dim_movies: 2000 linhas
  ...
  integridade referencial conferida: nenhuma violação
Carga concluída em 0.5s
```

Suba a API:

```bash
# Windows
.venv\Scripts\python -m uvicorn app.main:app --reload

# Linux / macOS
.venv/bin/python -m uvicorn app.main:app --reload
```

A API fica em **http://localhost:8000**, com documentação interativa em
**http://localhost:8000/docs**.

### 2. Frontend

No segundo terminal, a partir da raiz do repositório:

```bash
cd frontend
npm install
npm run dev
```

A interface fica em **http://localhost:5173**. É esse o endereço para usar a
aplicação.

> O Vite encaminha `/api` para `localhost:8000`, então o navegador enxerga uma
> única origem e não há configuração de CORS a fazer em desenvolvimento.

---

## Como usar

| Para... | Faça |
|---|---|
| **Navegar** | A página inicial lista o catálogo paginado, ordenado por popularidade. Passe o ponteiro sobre um cartão para ver título, ano e nota. |
| **Buscar** | Digite na barra de busca. Ela ignora acentos e maiúsculas: `cancao` encontra *Canção*. |
| **Cadastrar** | Botão **+ Novo filme**. Só o título é obrigatório. Ao salvar, você vai para a ficha do filme. |
| **Encontrar o que cadastrou** | Alterne o catálogo para **Adicionados recentemente** — os filmes cadastrados aqui aparecem primeiro. |
| **Ver detalhes** | Clique em qualquer cartão: ficha técnica, direção, roteiro, elenco, produtoras, notas externas e a lista de avaliações. |
| **Editar ou remover** | Botões **Editar** e **Excluir** no topo da ficha. A exclusão pede confirmação e informa quantas avaliações serão removidas junto. |
| **Avaliar** | Na ficha, o formulário **Avaliar**: escolha de ½ a 5 estrelas, informe seu nome e escreva a resenha. A média do filme é recalculada na hora. |

---

## Os dados

### Amostra versionada x base completa

O repositório traz `backend/data/sample/` com **2.000 filmes**, versionada para
que um clone já funcione. A base completa não é versionada — são 223 MB.

Para usar a base completa, copie os 10 CSVs oficiais para `backend/data/full/` e
rode a carga de novo. O script detecta sozinho qual pasta usar:

```bash
.venv/bin/python scripts/load_data.py           # usa full se houver, senão sample
.venv/bin/python scripts/load_data.py --sample  # força a amostra
.venv/bin/python scripts/load_data.py --full    # força a base completa
```

### A amostra preserva integridade referencial

Ela não é um `head -2000` de cada CSV, e isso importa. Recortar as primeiras
linhas de cada arquivo produziria avaliações apontando para filmes ausentes e
bridges ligando pessoas que não foram carregadas — o banco recusaria a carga, ou
pior, aceitaria dados quebrados.

O script `scripts/sample_data.py` sorteia N filmes e **filtra todas as outras
tabelas por esses identificadores**, seguindo as dependências até o fim: das
bridges saem os gêneros, produtoras e pessoas que sobrevivem, e só esses entram
nas dimensões. A carga confere o resultado com `PRAGMA foreign_key_check` e
falha se houver qualquer violação.

O sorteio é enviesado para filmes mais completos, para que a amostra mostre a
aplicação em boas condições — com pôster, sinopse e avaliações.

---

## Requisitos da atividade

| # | Requisito | Onde |
|---|---|---|
| 1 | Cadastrar filmes (título, diretor, ano, gênero, sinopse) | `POST /movies` · botão **+ Novo filme** |
| 2 | Catálogo paginado | `GET /movies` · página inicial |
| 3 | Detalhes com lista de avaliações | `GET /movies/{id}` e `/reviews` · ficha do filme |
| 4 | Busca por título | `GET /movies?busca=` · barra de busca |
| 5 | Atualizar e remover filmes | `PUT` e `DELETE /movies/{id}` · botões na ficha |
| 6 | Adicionar avaliação (nota + resenha) | `POST /movies/{id}/reviews` · formulário na ficha |
| 7 | Média geral das avaliações | Exibida no cartão e na ficha |

**Extras implementados:** testes automatizados (84 no backend), cache de
consultas (TanStack Query, com invalidação a cada escrita), responsividade
(grade fluida e media queries) e ordenação do catálogo.

---

## API

Prefixo `/api/v1`. Documentação interativa em `/docs`.

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/movies` | Catálogo paginado. Aceita `pagina`, `tamanho`, `busca` e `ordenar` |
| `GET` | `/movies/generos` | Os 19 gêneros disponíveis |
| `POST` | `/movies` | Cadastra um filme |
| `GET` | `/movies/{id}` | Ficha completa |
| `PUT` | `/movies/{id}` | Atualiza os campos editáveis |
| `DELETE` | `/movies/{id}` | Remove o filme e tudo que depende dele |
| `GET` | `/movies/{id}/reviews` | Avaliações paginadas |
| `POST` | `/movies/{id}/reviews` | Publica uma avaliação |
| `DELETE` | `/movies/{id}/reviews/{id}` | Remove uma avaliação |

---

## Arquitetura

O banco é um **esquema estrela**: o filme vive em `dim_movies`, as métricas em
`fact_movies_performance`, e gêneros, pessoas e produtoras em dimensões próprias
ligadas por tabelas de associação. É um modelo desenhado para análise.

A API, porém, entrega um recurso **plano** — um `Filme` coeso, que é o que o
consumidor espera. A tradução entre os dois modelos acontece em uma única
camada, o serviço, o que impede o formato do banco de vazar para o contrato.

```
backend/app/movies/
├── models.py       # tabelas e relações (SQLAlchemy)
├── schemas.py      # contrato HTTP (Pydantic)
├── repository.py   # consultas — conhece o esquema estrela
├── service.py      # traduz estrela <-> recurso plano, e as regras
└── router.py       # endpoints
```

Consequência prática: cadastrar um filme escreve em **cinco tabelas numa única
transação** — dimensão, fato, gêneros e pessoas com suas bridges. A linha do fato
é obrigatória porque a listagem usa junção interna; sem ela o filme existiria no
banco e seria invisível no catálogo.

---

## Testes e qualidade

```bash
# Backend — 84 testes
cd backend
.venv/bin/python -m pytest              # Windows: .venv\Scripts\python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m alembic check       # confirma que o schema e os modelos estão sincronizados

# Frontend
cd frontend
npx tsc -b        # tipos
npx oxlint        # lint
npm run build     # build de produção
```

---

## Estrutura

```text
.
├── backend/
│   ├── app/
│   │   ├── core/          # configuração, paginação, normalização de texto
│   │   ├── db/            # Base ORM, engine e sessões
│   │   └── movies/        # o domínio: models, schemas, repository, service, router
│   ├── data/
│   │   ├── sample/        # amostra de 2.000 filmes (versionada)
│   │   └── full/          # base completa (não versionada)
│   ├── migrations/        # revisões Alembic
│   ├── scripts/
│   │   ├── sample_data.py # gera a amostra preservando integridade referencial
│   │   └── load_data.py   # carga em massa dos CSVs
│   └── tests/
└── frontend/
    └── src/
        ├── api/           # cliente HTTP, tipos do contrato e hooks de dados
        ├── components/    # cartão, estrelas, paginação, formulários
        ├── pages/         # catálogo, ficha do filme, formulário de filme
        └── styles/        # tokens de design e estilos globais
```

---

## Notas

- O banco padrão é `backend/rocketlab.db`, criado pelas migrações. Ele está no
  `.gitignore`: o que se versiona são os CSVs e as migrações, não o arquivo.
- Recarregar os dados é seguro e idempotente — `load_data.py` limpa as tabelas
  antes de inserir. Se você apagar filmes testando, basta rodá-lo de novo.
- Para evoluir o schema, crie uma revisão em vez de alterar o banco à mão:
  `python -m alembic revision --autogenerate -m "descreva a alteração"`.
