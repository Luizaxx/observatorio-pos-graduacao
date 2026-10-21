import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dags"))

from capes_utils import (  # noqa: E402
    detectar_encoding,
    filtrar_csvs,
    ler_cabecalho,
    normalizar_coluna,
    sql_copy,
    uniao_colunas,
)


def test_normalizar_coluna_remove_acentos_e_espacos():
    assert normalizar_coluna("NM_ÁREA AVALIAÇÃO") == "nm_area_avaliacao"
    assert normalizar_coluna("  CD_PROGRAMA_IES ") == "cd_programa_ies"


def test_filtrar_csvs_ignora_pdf():
    recursos = [
        {"name": "Programas 2022", "format": "CSV", "url": "https://x/p2022.csv"},
        {"name": "Metadados", "format": "PDF", "url": "https://x/meta.pdf"},
        {"name": "Programas 2023", "format": "", "url": "https://x/p2023.CSV"},
    ]
    assert [r["nome"] for r in filtrar_csvs(recursos)] == ["Programas 2022", "Programas 2023"]


def test_detectar_encoding(tmp_path):
    latin = tmp_path / "latin.csv"
    latin.write_bytes("NM_REGIAO\nNORDESTE;SÃO LUÍS\n".encode("latin-1"))
    utf8 = tmp_path / "utf8.csv"
    utf8.write_bytes("NM_REGIAO\nNORDESTE;SÃO LUÍS\n".encode("utf-8"))
    assert detectar_encoding(latin) == "latin-1"
    assert detectar_encoding(utf8) == "utf-8"


def test_detectar_encoding_amostra_cortando_caractere(tmp_path):
    # "Ã" ocupa 2 bytes em utf-8; a amostra de 2 bytes corta no meio dele
    arquivo = tmp_path / "corte.csv"
    arquivo.write_bytes("AÃ".encode("utf-8"))
    assert detectar_encoding(arquivo, amostra=2) == "utf-8"


def test_ler_cabecalho_normaliza_e_ignora_bom(tmp_path):
    arquivo = tmp_path / "bom.csv"
    arquivo.write_bytes("﻿AN_BASE;NM_ÁREA AVALIAÇÃO\n2024;EDUCAÇÃO\n".encode("utf-8"))
    assert ler_cabecalho(arquivo) == (["an_base", "nm_area_avaliacao"], "utf-8")


def test_ler_cabecalho_recusa_colunas_repetidas(tmp_path):
    arquivo = tmp_path / "repetida.csv"
    arquivo.write_bytes("NM_AREA;NM ÁREA\nx;y\n".encode("latin-1"))
    with pytest.raises(ValueError, match="nm_area"):
        ler_cabecalho(arquivo)


def test_uniao_colunas_mantem_ordem_e_inclui_colunas_novas():
    assert uniao_colunas([["a", "b"], ["a", "c", "b"], ["d"]]) == ["a", "b", "c", "d"]


def test_sql_copy():
    sql = sql_copy("bronze.capes_teses", ["an_base", "nm_producao"], "latin-1")
    assert sql == (
        'COPY bronze.capes_teses ("an_base", "nm_producao") FROM STDIN '
        "WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'LATIN1')"
    )
