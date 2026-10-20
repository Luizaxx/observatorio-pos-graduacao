import unicodedata

import pandas as pd
import streamlit as st

from db import consultar
from graficos import FONTE, nome, numero

SEM_AVALIACAO = "Sem avaliação"


def sem_acento(serie: pd.Series) -> pd.Series:
    """Minúsculas e sem acentos, para a busca achar "ciencia" em "CIÊNCIA"."""
    return serie.map(
        lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    )


@st.cache_data(ttl=600, show_spinner=False)
def programas() -> pd.DataFrame:
    df = consultar("select * from ouro.dim_programas order by nome_programa, sigla_ies")
    # Nomes de programas e instituições ficam como a CAPES publica: eles têm
    # muitas siglas (PPGECN, UFPA...) que a formatação de nomes estragaria.
    for coluna in ["grande_area", "area_avaliacao", "modalidade"]:
        df[coluna] = df[coluna].map(nome)
    df["grau"] = df["grau"].str.capitalize()
    # A CAPES grafa "EM DESATIVACAO", sem acento
    df["situacao"] = df["situacao"].str.capitalize().str.replace("desativacao", "desativação")
    df["conceito"] = df["conceito"].map(
        lambda c: SEM_AVALIACAO if pd.isna(c) else str(int(c))
    )
    df["texto_busca"] = sem_acento(
        df["nome_programa"] + " " + df["sigla_ies"] + " " + df["nome_ies"]
    )
    return df


dados = programas()

st.title("Busca de programas")
st.caption("Consulte os programas de pós-graduação com os dados da coleta mais recente de cada um.")

busca = st.text_input(
    "Programa ou instituição",
    placeholder="Ex.: computação, UFMG, saúde coletiva",
)

f1, f2, f3, f4 = st.columns([2, 3, 2, 2])
ufs = f1.multiselect("UF", sorted(dados["uf"].unique()), placeholder="Todas")
grandes_areas = f2.multiselect(
    "Grande área", sorted(dados["grande_area"].unique(), key=str.lower), placeholder="Todas"
)
modalidades = f3.multiselect(
    "Modalidade", sorted(dados["modalidade"].unique()), placeholder="Todas"
)
conceitos = f4.multiselect(
    "Conceito", ["7", "6", "5", "4", "3", "2", "1", SEM_AVALIACAO], placeholder="Todos"
)
so_atuais = st.toggle(
    "Só programas da coleta mais recente",
    value=True,
    help="Desligue para incluir programas que saíram da base em anos anteriores.",
)

filtro = pd.Series(True, index=dados.index)
# Cada palavra precisa aparecer no nome do programa ou da instituição
for palavra in sem_acento(pd.Series([busca])).iloc[0].split():
    filtro &= dados["texto_busca"].str.contains(palavra, regex=False)
if ufs:
    filtro &= dados["uf"].isin(ufs)
if grandes_areas:
    filtro &= dados["grande_area"].isin(grandes_areas)
if modalidades:
    filtro &= dados["modalidade"].isin(modalidades)
if conceitos:
    filtro &= dados["conceito"].isin(conceitos)
if so_atuais:
    filtro &= dados["presente_na_ultima_coleta"]

# Ordem pensada para a tela: o essencial primeiro, o nome completo da IES no fim
colunas = {
    "codigo_programa": "Código",
    "nome_programa": "Programa",
    "sigla_ies": "Sigla IES",
    "uf": "UF",
    "conceito": "Conceito",
    "modalidade": "Modalidade",
    "grau": "Grau",
    "area_avaliacao": "Área de avaliação",
    "grande_area": "Grande área",
    "municipio": "Município",
    "situacao": "Situação",
    "ano_inicio_programa": "Início",
    "ultimo_ano_base": "Último ano-base",
    "nome_ies": "Instituição",
}
resultado = dados.loc[filtro, list(colunas)].rename(columns=colunas)

st.divider()

esq, dir_ = st.columns([4, 1], vertical_alignment="bottom")
total = len(resultado)
esq.markdown(f"**{numero(total)} {'programa' if total == 1 else 'programas'}**")
# Separador ";" e BOM para o Excel em português abrir o arquivo direto
dir_.download_button(
    "Baixar CSV",
    resultado.to_csv(index=False, sep=";").encode("utf-8-sig"),
    file_name="programas_pos_graduacao.csv",
    mime="text/csv",
    disabled=total == 0,
    use_container_width=True,
)

if total:
    st.dataframe(
        resultado,
        hide_index=True,
        use_container_width=True,
        height=600,
        column_config={
            "Código": None,
            "Programa": st.column_config.TextColumn(width="large"),
            "Início": st.column_config.NumberColumn(format="%d"),
            "Último ano-base": st.column_config.NumberColumn(format="%d"),
        },
    )
else:
    st.info("Nenhum programa encontrado com esses filtros.")

st.caption(FONTE)
