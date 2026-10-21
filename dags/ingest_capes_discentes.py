"""DAG do Airflow: ingestão dos discentes da pós-graduação (CAPES) na camada bronze.

O fluxo comum às fontes da CAPES está em ingestao_capes.py.
"""

import os

from datasets import BRONZE_CAPES_DISCENTES
from ingestao_capes import criar_dag_ingestao

# o Airflow só lê arquivos que mencionam "airflow" e "dag"; a docstring cuida disso
dag = criar_dag_ingestao(
    dag_id="ingest_capes_discentes",
    descricao="Ingestão dos discentes da pós-graduação (CAPES) na camada bronze",
    dataset_ckan=os.getenv(
        "CAPES_DATASET_DISCENTES",
        "2021-a-2024-discentes-da-pos-graduacao-stricto-sensu-do-brasil",
    ),
    tabela="capes_discentes",
    dataset=BRONZE_CAPES_DISCENTES,
)
