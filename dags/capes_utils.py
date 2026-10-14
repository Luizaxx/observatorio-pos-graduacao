"""Funções puras usadas pelas DAGs da CAPES (sem dependência do Airflow, fáceis de testar)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def normalizar_coluna(nome: str) -> str:
    """'NM_ÁREA AVALIAÇÃO' -> 'nm_area_avaliacao'."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.strip().lower()).strip("_")


def filtrar_csvs(recursos: list[dict]) -> list[dict]:
    """Mantém só os recursos CSV de um dataset CKAN."""
    return [
        {"nome": r["name"], "url": r["url"]}
        for r in recursos
        if (r.get("format") or "").upper() == "CSV" or r.get("url", "").lower().endswith(".csv")
    ]


def ler_csv(caminho: Path):
    """Arquivos da CAPES costumam vir com ';' e latin-1; tenta utf-8 antes."""
    import pandas as pd

    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(caminho, sep=";", dtype=str, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível decodificar {caminho}")
