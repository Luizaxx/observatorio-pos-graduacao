"""Datasets compartilhados entre DAGs (usados para disparar uma DAG quando outra termina)."""

from airflow.datasets import Dataset

BRONZE_CAPES_PROGRAMAS = Dataset("postgres://postgres:5432/observatorio/bronze/capes_programas")
