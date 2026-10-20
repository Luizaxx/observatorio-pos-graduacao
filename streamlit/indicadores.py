"""Indicadores que o painel calcula a partir das contagens da camada ouro."""

import pandas as pd

# coluna -> (rótulo, casas decimais, sufixo)
INDICADORES = {
    "total_programas": ("Programas", 0, ""),
    "conceito_medio": ("Conceito médio", 2, ""),
    "pct_doutorado": ("% com doutorado", 1, "%"),
    "pct_nota_6_7": ("% nota 6 ou 7", 1, "%"),
    "pct_profissionais": ("% profissionais", 1, "%"),
}

CONTAGENS = [
    "total_programas",
    "programas_profissionais",
    "programas_com_doutorado",
    "programas_avaliados",
    "programas_nota_6_7",
]


def com_percentuais(df: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta os percentuais que não vêm prontos da camada ouro."""
    return df.assign(
        pct_doutorado=100 * df["programas_com_doutorado"] / df["total_programas"],
        pct_profissionais=100 * df["programas_profissionais"] / df["total_programas"],
    )


def agregar(df: pd.DataFrame, por: str | list[str]) -> pd.DataFrame:
    """Soma as contagens por grupo e refaz médias e percentuais. O conceito
    médio é ponderado pelos programas avaliados, o que equivale à média sobre
    todos os programas do grupo."""
    grupos = (
        df.assign(peso=df["conceito_medio"] * df["programas_avaliados"])
        .groupby(por)[[*CONTAGENS, "peso"]]
        .sum()
    )
    grupos["conceito_medio"] = grupos.pop("peso") / grupos["programas_avaliados"]
    grupos["pct_nota_6_7"] = 100 * grupos["programas_nota_6_7"] / grupos["programas_avaliados"]
    return com_percentuais(grupos)
