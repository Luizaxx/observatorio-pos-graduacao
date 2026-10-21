"""DAG do Airflow: ingestão dos programas de pós-graduação (CAPES) na camada bronze.

O fluxo comum às fontes da CAPES está em ingestao_capes.py.
"""

import os

from datasets import BRONZE_CAPES_PROGRAMAS
from ingestao_capes import criar_dag_ingestao

# o Airflow só lê arquivos que mencionam "airflow" e "dag"; a docstring cuida disso
dag = criar_dag_ingestao(
    dag_id="ingest_capes_programas",
    descricao="Ingestão dos programas de pós-graduação (CAPES) na camada bronze",
    dataset_ckan=os.getenv(
        "CAPES_DATASET_PROGRAMAS",
        "2021-a-2024-programas-da-pos-graduacao-stricto-sensu-no-brasil",
    ),
    tabela="capes_programas",
    dataset=BRONZE_CAPES_PROGRAMAS,
)
