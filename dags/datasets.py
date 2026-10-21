"""Datasets compartilhados entre DAGs (usados para disparar uma DAG quando outra termina)."""

from airflow.datasets import Dataset

_BRONZE = "postgres://postgres:5432/observatorio/bronze"

BRONZE_CAPES_PROGRAMAS = Dataset(f"{_BRONZE}/capes_programas")
BRONZE_CAPES_DISCENTES = Dataset(f"{_BRONZE}/capes_discentes")
BRONZE_CAPES_TESES = Dataset(f"{_BRONZE}/capes_teses")
