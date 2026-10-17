"""
DAG de transformação: roda o projeto dbt (bronze -> prata -> ouro).

É disparada automaticamente quando a ingestão atualiza bronze.capes_programas.
O `dbt build` executa modelos e testes na ordem do grafo; se algum teste falhar,
a DAG falha e os modelos que dependem dele não são atualizados.
"""

from __future__ import annotations

import pendulum
from airflow.decorators import dag
from airflow.operators.bash import BashOperator

from datasets import BRONZE_CAPES_PROGRAMAS

DBT_BIN = "/home/airflow/dbt-venv/bin/dbt"
DBT_DIR = "/opt/airflow/dbt"

# target/ e logs/ ficam fora da pasta montada para não sujar o repositório
DBT_ENV = {
    "DBT_PROFILES_DIR": DBT_DIR,
    "DBT_TARGET_PATH": "/tmp/dbt/target",
    "DBT_LOG_PATH": "/tmp/dbt/logs",
    "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
}


@dag(
    dag_id="transform_dbt",
    description="Transformações dbt das camadas prata e ouro",
    schedule=[BRONZE_CAPES_PROGRAMAS],
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    tags=["dbt", "prata", "ouro"],
)
def transform_dbt():
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT_BIN} deps",
        cwd=DBT_DIR,
        env=DBT_ENV,
        append_env=True,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT_BIN} build",
        cwd=DBT_DIR,
        env=DBT_ENV,
        append_env=True,
    )

    dbt_deps >> dbt_build


transform_dbt()
