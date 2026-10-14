import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dags"))

from capes_utils import filtrar_csvs, ler_csv, normalizar_coluna  # noqa: E402


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


def test_ler_csv_latin1_com_ponto_e_virgula(tmp_path):
    arquivo = tmp_path / "amostra.csv"
    arquivo.write_bytes("AN_BASE;NM_REGIAO\n2022;CENTRO-OESTE\n2023;NORDESTE\n".encode("latin-1"))
    df = ler_csv(arquivo)
    assert list(df.columns) == ["AN_BASE", "NM_REGIAO"]
    assert len(df) == 2
