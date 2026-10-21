"""
Fluxo de ingestão comum aos conjuntos de dados da CAPES (Plataforma Sucupira).

    descobrir_recursos  ->  baixar_csv (mapeada, 1 task por arquivo)  ->  carregar_bronze  ->  validar_bronze

- Os arquivos são descobertos via API CKAN do portal de dados abertos da CAPES,
  então novos anos publicados entram no pipeline sem mudar código.
- A carga usa COPY arquivo por arquivo, sem passar pelo pandas: os CSVs de teses
  passam de 400 MB por ano e não caberiam na memória do container.
- A bronze guarda os dados brutos (todas as colunas como texto) + metadados de carga.
  A tabela é recriada numa única transação: se um arquivo falhar, a versão anterior fica.
- Ao final, validar_bronze atualiza o Dataset da tabela, o que dispara a transform_dbt.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pendulum
import requests
from airflow.datasets import Dataset
from airflow.decorators import dag, task

from capes_utils import filtrar_csvs, ler_cabecalho, normalizar_coluna, sql_copy, uniao_colunas

log = logging.getLogger(__name__)

CKAN_API = os.getenv("CAPES_CKAN_API", "https://dadosabertos.capes.gov.br/api/3/action")
RAW_DIR = Path(os.getenv("RAW_DATA_DIR", "/opt/airflow/data/raw")) / "capes"
WAREHOUSE_CONN = os.getenv(
    "WAREHOUSE_CONN", "postgresql+psycopg2://obs:obs@postgres:5432/observatorio"
)
BRONZE_SCHEMA = "bronze"
HTTP_TIMEOUT = 120


def criar_dag_ingestao(
    *, dag_id: str, descricao: str, dataset_ckan: str, tabela: str, dataset: Dataset
):
    """Cria a DAG que leva um conjunto de dados da CAPES para bronze.<tabela>."""
    pasta_raw = RAW_DIR / tabela.removeprefix("capes_")
    tabela_bronze = f"{BRONZE_SCHEMA}.{tabela}"

    @dag(
        dag_id=dag_id,
        description=descricao,
        schedule="@weekly",
        start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
        catchup=False,
        max_active_runs=1,
        default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=5)},
        tags=["capes", "bronze", "ingestao"],
    )
    def ingestao():
        @task
        def descobrir_recursos() -> list[dict]:
            resp = requests.get(
                f"{CKAN_API}/package_show", params={"id": dataset_ckan}, timeout=HTTP_TIMEOUT
            )
            resp.raise_for_status()
            csvs = filtrar_csvs(resp.json()["result"]["resources"])
            if not csvs:
                raise ValueError(f"Nenhum CSV encontrado no dataset {dataset_ckan}")
            log.info("%d arquivos CSV encontrados: %s", len(csvs), [c["nome"] for c in csvs])
            return csvs

        # O servidor da CAPES derruba conexões longas e não aceita Range, então
        # não dá para retomar: a task tenta de novo, com poucos downloads por vez.
        @task(
            retries=6,
            retry_delay=pendulum.duration(minutes=1),
            max_active_tis_per_dagrun=2,
        )
        def baixar_csv(recurso: dict) -> str:
            pasta_raw.mkdir(parents=True, exist_ok=True)
            destino = pasta_raw / f"{normalizar_coluna(recurso['nome'])}.csv"
            cabeca = requests.head(recurso["url"], allow_redirects=True, timeout=HTTP_TIMEOUT)
            cabeca.raise_for_status()
            tamanho = cabeca.headers.get("Content-Length")
            tamanho = int(tamanho) if tamanho else None
            if tamanho and destino.exists() and destino.stat().st_size == tamanho:
                log.info("%s já está completo (%.1f MB); download pulado", destino.name, tamanho / 1e6)
                return str(destino)

            # baixa num arquivo temporário para nunca deixar um CSV pela metade no destino
            parcial = destino.with_suffix(".csv.part")
            with requests.get(recurso["url"], stream=True, timeout=HTTP_TIMEOUT) as resp:
                resp.raise_for_status()
                with open(parcial, "wb") as f:
                    for bloco in resp.iter_content(chunk_size=1 << 20):
                        f.write(bloco)
            if tamanho and parcial.stat().st_size != tamanho:
                raise OSError(
                    f"{destino.name}: baixados {parcial.stat().st_size} de {tamanho} bytes"
                )
            parcial.replace(destino)
            log.info("Baixado %s (%.1f MB)", destino.name, destino.stat().st_size / 1e6)
            return str(destino)

        @task
        def carregar_bronze(caminhos: list[str]) -> int:
            from sqlalchemy import create_engine

            arquivos = [Path(c) for c in sorted(caminhos)]
            cabecalhos = {a: ler_cabecalho(a) for a in arquivos}
            colunas = uniao_colunas([cols for cols, _ in cabecalhos.values()])
            definicoes = ", ".join(f'"{c}" text' for c in colunas)

            conn = create_engine(WAREHOUSE_CONN).raw_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {BRONZE_SCHEMA}")
                    cur.execute(f"DROP TABLE IF EXISTS {tabela_bronze}")
                    cur.execute(
                        f"CREATE TABLE {tabela_bronze} ({definicoes}, "
                        "_arquivo_origem text, _carregado_em timestamptz DEFAULT %s)",
                        (datetime.now(timezone.utc),),
                    )
                    total = 0
                    for arquivo in arquivos:
                        cols, encoding = cabecalhos[arquivo]
                        # o COPY não preenche colunas fora do CSV; o default faz isso
                        cur.execute(
                            f"ALTER TABLE {tabela_bronze} ALTER COLUMN _arquivo_origem SET DEFAULT %s",
                            (arquivo.name,),
                        )
                        with open(arquivo, "rb") as f:
                            cur.copy_expert(sql_copy(tabela_bronze, cols, encoding), f)
                        log.info("%s: %d linhas (%s)", arquivo.name, cur.rowcount, encoding)
                        total += cur.rowcount
                    cur.execute(
                        f"ALTER TABLE {tabela_bronze} ALTER COLUMN _arquivo_origem DROP DEFAULT"
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

            log.info("Carregadas %d linhas em %s", total, tabela_bronze)
            return total

        # ao terminar com sucesso, atualiza o Dataset e dispara a DAG transform_dbt
        @task(outlets=[dataset])
        def validar_bronze(linhas_carregadas: int) -> None:
            from sqlalchemy import create_engine, text

            with create_engine(WAREHOUSE_CONN).connect() as conn:
                linhas = conn.execute(text(f"SELECT COUNT(*) FROM {tabela_bronze}")).scalar_one()
                por_arquivo = conn.execute(
                    text(
                        f"SELECT _arquivo_origem, COUNT(*) FROM {tabela_bronze} "
                        "GROUP BY 1 ORDER BY 1"
                    )
                ).all()

            if linhas == 0 or linhas != linhas_carregadas:
                raise ValueError(
                    f"Validação falhou: esperado {linhas_carregadas}, encontrado {linhas}"
                )
            for arquivo, qtd in por_arquivo:
                log.info("  %s -> %d linhas", arquivo, qtd)
            log.info("Validação OK: %d linhas em %s", linhas, tabela_bronze)

        recursos = descobrir_recursos()
        caminhos = baixar_csv.expand(recurso=recursos)
        validar_bronze(carregar_bronze(caminhos))

    return ingestao()
