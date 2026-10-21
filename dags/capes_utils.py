"""Funções puras usadas pelas DAGs da CAPES (sem dependência do Airflow, fáceis de testar)."""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path
from typing import TextIO


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
    encoding = detectar_encoding(caminho)
    with abrir_csv(caminho, encoding) as f:
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


def abrir_csv(caminho: Path, encoding: str) -> TextIO:
    # utf-8-sig descarta o BOM, que de outro modo grudaria na primeira coluna;
    # newline="" deixa o módulo csv tratar quebras dentro de aspas
    return open(
        caminho, encoding="utf-8-sig" if encoding == "utf-8" else encoding, newline=""
    )


class LeitorCopy:
    """Entrega um CSV da CAPES ao COPY aos poucos, já em utf-8 e sem o cabeçalho.

    Linhas com campos faltando no fim são completadas com nulos (o catálogo de
    teses de 2021 tem uma linha truncada) e ficam anotadas em `completadas`.
    Linhas com campos a mais indicam erro de leitura e interrompem a carga.
    """

    def __init__(self, arquivo: TextIO, n_colunas: int, linhas_por_lote: int = 2000):
        self._linhas = csv.reader(arquivo, delimiter=";")
        next(self._linhas, None)
        self._n_colunas = n_colunas
        self._linhas_por_lote = linhas_por_lote
        self._dados = b""
        self._posicao = 0
        self.completadas: list[int] = []

    def _proximo_lote(self) -> bytes:
        saida = io.StringIO()
        escritor = csv.writer(saida, delimiter=";", lineterminator="\n")
        for _, linha in zip(range(self._linhas_por_lote), self._linhas):
            if len(linha) < self._n_colunas:
                self.completadas.append(self._linhas.line_num)
                linha += [""] * (self._n_colunas - len(linha))
            elif len(linha) > self._n_colunas:
                raise ValueError(
                    f"linha {self._linhas.line_num}: {len(linha)} campos, "
                    f"esperados {self._n_colunas}"
                )
            escritor.writerow(linha)
        return saida.getvalue().encode("utf-8")

    def read(self, tamanho: int = -1) -> bytes:
        if self._posicao >= len(self._dados):
            self._dados, self._posicao = self._proximo_lote(), 0
        fim = len(self._dados) if tamanho < 0 else self._posicao + tamanho
        bloco = self._dados[self._posicao : fim]
        self._posicao += len(bloco)
        return bloco


def sql_copy(tabela: str, colunas: list[str]) -> str:
    """Comando COPY para os dados entregues pelo LeitorCopy."""
    lista = ", ".join(f'"{c}"' for c in colunas)
    return (
        f"COPY {tabela} ({lista}) FROM STDIN "
        "WITH (FORMAT csv, DELIMITER ';', ENCODING 'UTF8')"
    )
