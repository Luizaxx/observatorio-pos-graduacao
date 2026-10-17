"""
DAG de ingestão: Programas da Pós-Graduação Stricto Sensu (CAPES / Plataforma Sucupira).

Fluxo:
    descobrir_recursos  ->  baixar_csv (mapeada, 1 task por arquivo)  ->  carregar_bronze  ->  validar_bronze

Ao final, validar_bronze atualiza o Dataset da bronze, o que dispara a DAG transform_dbt.

- Os arquivos são descobertos via API CKAN do portal de dados abertos da CAPES,
  então novos anos publicados entram no pipeline sem mudar código.
- A camada bronze guarda os dados brutos (todas as colunas como texto) + metadados de carga.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pendulum
import requests
from airflow.decorators import dag, task

from capes_utils import filtrar_csvs, ler_csv, normalizar_coluna
from datasets import BRONZE_CAPES_PROGRAMAS

log = logging.getLogger(__name__)

CKAN_API = os.getenv("CAPES_CKAN_API", "https://dadosabertos.capes.gov.br/api/3/action")
DATASET_SLUG = os.getenv(
    "CAPES_DATASET_PROGRAMAS",
    "2021-a-2024-programas-da-pos-graduacao-stricto-sensu-no-brasil",
)
RAW_DIR = Path(os.getenv("RAW_DATA_DIR", "/opt/airflow/data/raw")) / "capes" / "programas"
WAREHOUSE_CONN = os.getenv(
    "WAREHOUSE_CONN", "postgresql+psycopg2://obs:obs@postgres:5432/observatorio"
)
BRONZE_SCHEMA = "bronze"
BRONZE_TABLE = "capes_programas"
HTTP_TIMEOUT = 120


@dag(
    dag_id="ingest_capes_programas",
    description="Ingestão dos programas de pós-graduação (CAPES) na camada bronze",
    schedule="@weekly",
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=5)},
    tags=["capes", "bronze", "ingestao"],
)
def ingest_capes_programas():
    @task
    def descobrir_recursos() -> list[dict]:
        resp = requests.get(
            f"{CKAN_API}/package_show", params={"id": DATASET_SLUG}, timeout=HTTP_TIMEOUT
        )
        resp.raise_for_status()
        recursos = resp.json()["result"]["resources"]
        csvs = filtrar_csvs(recursos)
        if not csvs:
            raise ValueError(f"Nenhum CSV encontrado no dataset {DATASET_SLUG}")
        log.info("%d arquivos CSV encontrados: %s", len(csvs), [c["nome"] for c in csvs])
        return csvs

    @task
    def baixar_csv(recurso: dict) -> str:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        destino = RAW_DIR / f"{normalizar_coluna(recurso['nome'])}.csv"
        with requests.get(recurso["url"], stream=True, timeout=HTTP_TIMEOUT) as resp:
            resp.raise_for_status()
            with open(destino, "wb") as f:
                for bloco in resp.iter_content(chunk_size=1 << 20):
                    f.write(bloco)
        log.info("Baixado %s (%.1f MB)", destino.name, destino.stat().st_size / 1e6)
        return str(destino)

    @task
    def carregar_bronze(caminhos: list[str]) -> int:
        import pandas as pd
        from sqlalchemy import create_engine, text

        engine = create_engine(WAREHOUSE_CONN)
        carregado_em = datetime.now(timezone.utc)

        with engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {BRONZE_SCHEMA}"))
            conn.execute(text(f"DROP TABLE IF EXISTS {BRONZE_SCHEMA}.{BRONZE_TABLE}"))

        quadros = []
        for caminho in caminhos:
            df = ler_csv(Path(caminho))
            df.columns = [normalizar_coluna(c) for c in df.columns]
            df["_arquivo_origem"] = Path(caminho).name
            df["_carregado_em"] = carregado_em
            quadros.append(df)
            log.info("%s: %d linhas", Path(caminho).name, len(df))

        # concat alinha colunas que mudam entre anos (as ausentes viram nulo)
        bronze = pd.concat(quadros, ignore_index=True, sort=False)
        bronze.to_sql(
            BRONZE_TABLE,
            engine,
            schema=BRONZE_SCHEMA,
            if_exists="replace",
            index=False,
            chunksize=5_000,
            method="multi",
        )
        total = len(bronze)
        log.info("Carregadas %d linhas em %s.%s", total, BRONZE_SCHEMA, BRONZE_TABLE)
        return total

    # ao terminar com sucesso, atualiza o Dataset e dispara a DAG transform_dbt
    @task(outlets=[BRONZE_CAPES_PROGRAMAS])
    def validar_bronze(linhas_carregadas: int) -> None:
        from sqlalchemy import create_engine, text

        engine = create_engine(WAREHOUSE_CONN)
        with engine.connect() as conn:
            linhas = conn.execute(
                text(f"SELECT COUNT(*) FROM {BRONZE_SCHEMA}.{BRONZE_TABLE}")
            ).scalar_one()
            por_arquivo = conn.execute(
                text(
                    f"SELECT _arquivo_origem, COUNT(*) FROM {BRONZE_SCHEMA}.{BRONZE_TABLE} "
                    "GROUP BY 1 ORDER BY 1"
                )
            ).all()

        if linhas == 0 or linhas != linhas_carregadas:
            raise ValueError(f"Validação falhou: esperado {linhas_carregadas}, encontrado {linhas}")
        for arquivo, qtd in por_arquivo:
            log.info("  %s -> %d linhas", arquivo, qtd)
        log.info("Validação OK: %d linhas na bronze", linhas)

    recursos = descobrir_recursos()
    caminhos = baixar_csv.expand(recurso=recursos)
    validar_bronze(carregar_bronze(caminhos))


ingest_capes_programas()
