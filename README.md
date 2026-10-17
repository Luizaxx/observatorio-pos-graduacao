# Observatório da Pós-Graduação Brasileira

Pipeline de dados de ponta a ponta sobre os dados abertos da CAPES (Plataforma Sucupira): ingestão orquestrada com **Apache Airflow**, armazenamento em **PostgreSQL** com arquitetura medalhão (bronze → prata → ouro), transformação e testes de qualidade com **dbt** e, na próxima etapa, painel em **Streamlit**. Tudo sobe com Docker e usa apenas ferramentas open source.

## Arquitetura

```
 Portal de Dados Abertos CAPES (API CKAN)
              │
              ▼
 ┌──────────────────────── Airflow ────────────────────────┐
 │                                                         │
 │  ingest_capes_programas            transform_dbt        │
 │  ─────────────────────             ─────────────        │
 │  descobrir_recursos                dbt_deps             │
 │    └─► baixar_csv (1 por ano)        └─► dbt_build      │
 │          └─► carregar_bronze               ▲            │
 │                └─► validar_bronze ─────────┘            │
 │                       (Dataset)                         │
 └─────────┬──────────────────────────────────┬────────────┘
           ▼                                  ▼
       data/raw/              PostgreSQL (observatorio)
                          bronze ─► prata ─► ouro
                                              │
                                              ▼
                                    Streamlit (etapa 3)
```

A DAG de ingestão roda semanalmente. Quando ela termina com sucesso, publica o Dataset da tabela bronze, e isso dispara a `transform_dbt`, que reconstrói a prata e a ouro e roda os testes.

## Camadas

| Camada | Schema | Conteúdo | Quem escreve |
|---|---|---|---|
| Bronze | `bronze` | CSVs da CAPES como vieram, tudo em texto, com colunas de linhagem | Airflow |
| Prata | `prata` | `stg_capes__programas`: dado tipado, com nomes legíveis e uma linha por programa por ano-base | dbt |
| Ouro | `ouro` | `dim_programas`, `fct_programas_por_uf_ano` e `fct_programas_por_area_ano`, prontas para o painel | dbt |

As tabelas de fatos têm as mesmas métricas: total de programas, em funcionamento, acadêmicos, profissionais, com doutorado, conceito médio e programas nota 6 ou 7 (quantidade e percentual).

## Estrutura

```
observatorio-pos-graduacao/
├── dags/
│   ├── ingest_capes_programas.py   # DAG de ingestão
│   ├── transform_dbt.py            # DAG que roda o dbt
│   ├── datasets.py                 # Dataset que liga as duas DAGs
│   └── capes_utils.py              # funções puras (testadas)
├── dbt/
│   ├── models/staging/             # bronze → prata
│   ├── models/marts/               # prata → ouro
│   ├── macros/                     # métricas compartilhadas e nome dos schemas
│   ├── tests/                      # testes singulares
│   └── profiles.yml                # conexão via variáveis de ambiente
├── sql/init/                       # cria banco do Airflow e schemas bronze/prata/ouro
├── tests/                          # testes com pytest
├── Dockerfile                      # Airflow + dbt
├── docker-compose.yml
├── .env.example
└── requirements-dev.txt
```

## Como rodar

Pré-requisitos: Docker e Docker Compose.

```bash
cp .env.example .env
# Linux: coloque o resultado de `id -u` em AIRFLOW_UID no .env
mkdir -p data logs
docker compose up -d --build
```

1. Acesse http://localhost:8080 (usuário e senha: `admin` / `admin`).
2. Ative as DAGs **`ingest_capes_programas`** e **`transform_dbt`**.
3. Dispare a ingestão com ▶ *Trigger DAG*. Quando ela terminar, a `transform_dbt` começa sozinha.
4. Confira o resultado:

```bash
docker compose exec postgres psql -U obs -d observatorio \
  -c "SELECT ano_base, uf, total_programas, conceito_medio FROM ouro.fct_programas_por_uf_ano ORDER BY 1 DESC, 3 DESC LIMIT 5;"
```

O Postgres fica exposto no host na porta **5434**, para não conflitar com outros bancos locais.

## Transformação com dbt

No dia a dia o dbt roda pelo Airflow. Para desenvolver os modelos, dá para rodar no host com o compose no ar:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r dbt/requirements.txt
cd dbt
../.venv/bin/dbt deps --profiles-dir .
../.venv/bin/dbt build --profiles-dir .
```

A conexão usa `localhost:5434` e o usuário do `.env` por padrão. Dá para trocar com `DBT_HOST`, `DBT_PORT`, `POSTGRES_USER` e `POSTGRES_PASSWORD`.

### Documentação dos modelos

Todos os modelos e colunas estão descritos nos arquivos `.yml`. Para ver a documentação com o grafo de linhagem:

```bash
cd dbt
../.venv/bin/dbt docs generate --profiles-dir .
../.venv/bin/dbt docs serve --profiles-dir . --port 8081
```

E abra http://localhost:8081.

### Testes de qualidade

O `dbt build` roda 26 testes junto com os modelos. Se algum falhar, a `transform_dbt` falha e os modelos seguintes não são atualizados.

- **Prata:** chave única por programa e ano-base, campos obrigatórios, valores aceitos para UF, região, modalidade, grau e situação, e conceito entre 1 e 7.
- **Ouro:** chave única em cada tabela e métricas dentro da faixa esperada.
- **`assert_ouro_total_igual_prata`:** a soma de programas por ano nas tabelas agregadas tem que bater com a prata.

## Testes das funções Python

```bash
pip install pandas pytest
pytest tests/
```

## Decisões técnicas

- **Descoberta via API CKAN:** a DAG lista os CSVs do dataset em vez de ter URLs fixas, então anos novos publicados pela CAPES entram sem mudar código.
- **Dynamic Task Mapping:** um download por arquivo, em paralelo e com retentativas independentes.
- **Bronze como texto:** todas as colunas entram como `text`, preservando o dado bruto; tipagem e limpeza ficam para a camada prata (dbt).
- **Colunas de linhagem:** `_arquivo_origem` e `_carregado_em` permitem rastrear cada linha até a fonte.
- **Validação após a carga:** a DAG falha se a contagem no banco divergir do que foi lido.
- **Conceito "A":** cursos novos aprovados ainda sem nota vêm com conceito `A`. Na prata eles ficam com `conceito` nulo e `sem_avaliacao = true`, e não entram no conceito médio.
- **Início dos cursos em texto:** `an_inicio_curso` vem como `2014/2019` (mestrado/doutorado), mas a ordem está invertida em parte dos registros. Por isso fica em texto, em vez de ser separado com uma regra que estaria errada nesses casos.
- **Áreas renomeadas:** algumas áreas de avaliação mudaram de nome entre os anos (ex.: Ciência da Computação para Computação). Os agregados usam o código da área e o nome mais recente, para a série histórica não quebrar.
- **Prata como tabela, não view:** a ingestão recria a bronze a cada carga, e o Postgres não deixa dropar uma tabela com views dependentes.
- **Dataset em vez de horário fixo:** a `transform_dbt` roda logo depois de cada ingestão bem-sucedida, sem depender de acertar horários entre as DAGs.
- **dbt num venv separado na imagem:** evita conflito de dependências com o Airflow.

## Roadmap

- [x] Etapa 1 — Ingestão dos programas de pós-graduação na camada bronze
- [x] Etapa 2 — Modelos dbt (prata e ouro) com testes de qualidade
- [ ] Etapa 3 — Painel em Streamlit com indicadores por UF, área e ano
- [ ] Etapa 4 — Novas fontes (discentes, teses e dissertações) e busca semântica com embeddings
- [ ] Etapa 5 — CI com GitHub Actions e MinIO como data lake

## Fonte dos dados

[Portal de Dados Abertos da CAPES](https://dadosabertos.capes.gov.br/) — Coleta de Dados da Plataforma Sucupira, licença aberta.
