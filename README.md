# Observatório da Pós-Graduação Brasileira

Pipeline de dados de ponta a ponta sobre os dados abertos da CAPES (Plataforma Sucupira): ingestão orquestrada com **Apache Airflow**, armazenamento em **PostgreSQL** com arquitetura medalhão (bronze → prata → ouro) e, nas próximas etapas, transformação com **dbt** e painel em **Streamlit**. Tudo sobe com Docker e usa apenas ferramentas open source.

## Arquitetura

```
 Portal de Dados Abertos CAPES (API CKAN)
              │
              ▼
 ┌─────────── Airflow ───────────┐
 │ descobrir_recursos            │
 │   └─► baixar_csv (1 por ano)  │──► data/raw/  (arquivos brutos)
 │         └─► carregar_bronze   │
 │               └─► validar     │
 └───────────────┬───────────────┘
                 ▼
        PostgreSQL  (observatorio)
        bronze ─► prata ─► ouro        ← dbt  (etapa 2)
                                 │
                                 ▼
                           Streamlit   (etapa 3)
```

## Estrutura

```
observatorio-pos-graduacao/
├── dags/
│   ├── ingest_capes_programas.py   # DAG de ingestão
│   └── capes_utils.py              # funções puras (testadas)
├── dbt/
│   ├── models/staging/             # bronze → prata
│   ├── models/marts/               # prata → ouro
│   └── profiles.yml                # conexão via variáveis de ambiente
├── sql/init/                       # cria banco do Airflow e schemas bronze/prata/ouro
├── tests/                          # testes com pytest
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
docker compose up -d
```

1. Acesse http://localhost:8080 (usuário e senha: `admin` / `admin`).
2. Ative a DAG **`ingest_capes_programas`** e clique em ▶ *Trigger DAG*.
3. Quando terminar, confira os dados:

```bash
docker compose exec postgres psql -U obs -d observatorio \
  -c "SELECT _arquivo_origem, COUNT(*) FROM bronze.capes_programas GROUP BY 1;"
```

## Transformação com dbt

O projeto dbt fica em `dbt/` e lê a tabela `bronze.capes_programas`. Para rodar no host, com o compose no ar:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r dbt/requirements.txt
cd dbt
../.venv/bin/dbt deps --profiles-dir .
../.venv/bin/dbt debug --profiles-dir .
../.venv/bin/dbt source freshness --profiles-dir .
```

A conexão usa `localhost:5434` e o usuário do `.env` por padrão. Dá para trocar com `DBT_HOST`, `DBT_PORT`, `POSTGRES_USER` e `POSTGRES_PASSWORD`.

## Testes

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

## Roadmap

- [x] Etapa 1 — Ingestão dos programas de pós-graduação na camada bronze
- [ ] Etapa 2 — Modelos dbt (prata e ouro) com testes de qualidade
- [ ] Etapa 3 — Painel em Streamlit com indicadores por UF, área e ano
- [ ] Etapa 4 — Novas fontes (discentes, teses e dissertações) e busca semântica com embeddings
- [ ] Etapa 5 — CI com GitHub Actions e MinIO como data lake

## Fonte dos dados

[Portal de Dados Abertos da CAPES](https://dadosabertos.capes.gov.br/) — Coleta de Dados da Plataforma Sucupira, licença aberta.
