"""DAG do Airflow: ingestão do catálogo de teses e dissertações (CAPES) na camada bronze.

O fluxo comum às fontes da CAPES está em ingestao_capes.py.
"""

import os

from datasets import BRONZE_CAPES_TESES
from ingestao_capes import criar_dag_ingestao

# o Airflow só lê arquivos que mencionam "airflow" e "dag"; a docstring cuida disso
dag = criar_dag_ingestao(
    dag_id="ingest_capes_teses",
    descricao="Ingestão do catálogo de teses e dissertações (CAPES) na camada bronze",
    dataset_ckan=os.getenv(
        "CAPES_DATASET_TESES",
        "2021-a-2024-catalogo-de-teses-e-dissertacoes-brasil",
    ),
    tabela="capes_teses",
    dataset=BRONZE_CAPES_TESES,
)
