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


def detectar_encoding(caminho: Path, amostra: int = 4 << 20) -> str:
    """Olha o começo do arquivo: se for utf-8 válido, é utf-8; senão, latin-1."""
    with open(caminho, "rb") as f:
        bloco = f.read(amostra)
    # o corte da amostra pode cair no meio de um caractere de vários bytes
    try:
        bloco.decode("utf-8")
    except UnicodeDecodeError as erro:
        if erro.start < len(bloco) - 3:
            return "latin-1"
    return "utf-8"


def ler_cabecalho(caminho: Path) -> tuple[list[str], str]:
    """Colunas normalizadas e encoding de um CSV da CAPES, sem ler o arquivo todo."""
    import csv

    encoding = detectar_encoding(caminho)
    # utf-8-sig descarta o BOM, que de outro modo grudaria na primeira coluna
    with open(caminho, encoding="utf-8-sig" if encoding == "utf-8" else encoding) as f:
        cabecalho = next(csv.reader(f, delimiter=";"))
    colunas = [normalizar_coluna(c) for c in cabecalho]
    repetidas = {c for c in colunas if colunas.count(c) > 1}
    if repetidas:
        raise ValueError(f"{caminho.name}: colunas repetidas após normalizar: {sorted(repetidas)}")
    return colunas, encoding


def uniao_colunas(cabecalhos: list[list[str]]) -> list[str]:
    """Todas as colunas dos arquivos, na ordem em que aparecem pela primeira vez.
    Alguns anos têm colunas que outros não têm."""
    vistas: dict[str, None] = {}
    for colunas in cabecalhos:
        vistas.update(dict.fromkeys(colunas))
    return list(vistas)


def sql_copy(tabela: str, colunas: list[str], encoding: str) -> str:
    """Comando COPY que lê um CSV da CAPES direto do arquivo, sem pandas."""
    lista = ", ".join(f'"{c}"' for c in colunas)
    encoding_pg = {"utf-8": "UTF8", "latin-1": "LATIN1"}[encoding]
    return (
        f"COPY {tabela} ({lista}) FROM STDIN "
        f"WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING '{encoding_pg}')"
    )
