import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import consultar
from graficos import AZUL, FONTE, estilo, numero

CINZA = "#8a8a85"

# Rampa sequencial de um só tom: do claro (menor valor) ao escuro (maior)
ESCALA = [[0, "#cde2fb"], [0.5, AZUL], [1, "#0d366b"]]

# coluna -> (rótulo, casas decimais, sufixo)
INDICADORES = {
    "total_programas": ("Programas", 0, ""),
    "conceito_medio": ("Conceito médio", 2, ""),
    "pct_doutorado": ("% com doutorado", 1, "%"),
    "pct_nota_6_7": ("% nota 6 ou 7", 1, "%"),
    "pct_profissionais": ("% profissionais", 1, "%"),
}


@st.cache_data
def malha_ufs() -> dict:
    caminho = Path(__file__).parent.parent / "dados" / "ufs.geojson"
    return json.loads(caminho.read_text())


dados = consultar("select * from ouro.fct_programas_por_uf_ano order by ano_base, uf")
dados["pct_doutorado"] = 100 * dados["programas_com_doutorado"] / dados["total_programas"]
dados["pct_profissionais"] = 100 * dados["programas_profissionais"] / dados["total_programas"]

# Referência nacional por ano, somando as UFs (mesma regra da visão geral)
somas = dados.groupby("ano_base").sum(numeric_only=True)
somas["peso_conceito"] = (
    dados.assign(p=dados["conceito_medio"] * dados["programas_avaliados"])
    .groupby("ano_base")["p"].sum()
)
brasil = somas.assign(
    conceito_medio=somas["peso_conceito"] / somas["programas_avaliados"],
    pct_doutorado=100 * somas["programas_com_doutorado"] / somas["total_programas"],
    pct_nota_6_7=100 * somas["programas_nota_6_7"] / somas["programas_avaliados"],
    pct_profissionais=100 * somas["programas_profissionais"] / somas["total_programas"],
)

st.title("Indicadores por UF")
st.caption("Compare os estados em um ano-base e acompanhe a evolução de cada um.")

anos = sorted(dados["ano_base"].unique(), reverse=True)
f1, f2, _ = st.columns([1, 2, 3])
ano = f1.selectbox("Ano-base", anos)
indicador = f2.selectbox(
    "Indicador", list(INDICADORES), format_func=lambda c: INDICADORES[c][0]
)
rotulo, casas, sufixo = INDICADORES[indicador]
formato = f",.{casas}f"

do_ano = dados[dados["ano_base"] == ano].sort_values(indicador)
media = brasil.loc[ano, indicador]

st.divider()

esq, dir_ = st.columns([3, 2], gap="large")

with esq:
    st.subheader(f"{rotulo} em {ano}")
    fig = go.Figure(
        go.Choropleth(
            geojson=malha_ufs(),
            featureidkey="properties.uf",
            locations=do_ano["uf"],
            z=do_ano[indicador],
            colorscale=ESCALA,
            marker=dict(line=dict(color="white", width=1)),
            colorbar=dict(thickness=10, len=0.6, tickformat=formato, ticksuffix=sufixo),
            hovertemplate=f"%{{location}}: %{{z:{formato}}}{sufixo}<extra></extra>",
        )
    )
    # Enquadramento fixo no Brasil: o fitbounds deixa o mapa pequeno no quadro
    fig.update_geos(
        visible=False,
        projection_type="mercator",
        lonaxis_range=[-74.5, -34],
        lataxis_range=[-34, 6],
        bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(estilo(fig, altura=620), use_container_width=True)

with dir_:
    st.subheader("Ranking")
    ranking = do_ano[["uf", indicador]]
    # Para o total, a soma nacional não serve de referência ao lado de uma UF
    if indicador != "total_programas":
        ranking = pd.concat(
            [ranking, pd.DataFrame({"uf": ["Brasil"], indicador: [media]})]
        ).sort_values(indicador)
    cores = [CINZA if uf == "Brasil" else AZUL for uf in ranking["uf"]]
    fig = go.Figure(
        go.Bar(
            x=ranking[indicador],
            y=ranking["uf"],
            orientation="h",
            marker=dict(color=cores, cornerradius=4),
            text=ranking[indicador],
            texttemplate=f"%{{text:{formato}}}{sufixo}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"%{{y}}: %{{x:{formato}}}{sufixo}<extra></extra>",
        )
    )
    fig.update_xaxes(visible=False, range=[0, ranking[indicador].max() * 1.18])
    fig.update_yaxes(showgrid=False)
    fig.update_layout(bargap=0.3)
    st.plotly_chart(estilo(fig, altura=620), use_container_width=True)

with st.expander(f"Ver todos os indicadores das UFs em {ano}"):
    colunas = ["uf", "regiao", "programas_avaliados", *INDICADORES]
    st.dataframe(
        do_ano.sort_values("total_programas", ascending=False)[colunas],
        hide_index=True,
        use_container_width=True,
        column_config={
            "uf": "UF",
            "regiao": "Região",
            "programas_avaliados": st.column_config.NumberColumn("Avaliados"),
            "total_programas": st.column_config.NumberColumn("Programas"),
            "conceito_medio": st.column_config.NumberColumn("Conceito médio", format="%.2f"),
            "pct_doutorado": st.column_config.NumberColumn("% com doutorado", format="%.1f"),
            "pct_nota_6_7": st.column_config.NumberColumn("% nota 6 ou 7", format="%.1f"),
            "pct_profissionais": st.column_config.NumberColumn("% profissionais", format="%.1f"),
        },
    )

st.divider()

st.subheader("Evolução de uma UF")
ufs = sorted(dados["uf"].unique())
uf = st.columns([1, 5])[0].selectbox("UF", ufs, index=ufs.index("SP"))
serie = dados[dados["uf"] == uf]

fig = go.Figure(
    go.Scatter(
        x=serie["ano_base"],
        y=serie[indicador],
        name=uf,
        mode="lines+markers",
        line=dict(color=AZUL, width=2),
        marker=dict(size=9),
        hovertemplate=f"{uf} em %{{x}}: %{{y:{formato}}}{sufixo}<extra></extra>",
    )
)
# Como no ranking, a referência nacional só aparece para médias e percentuais.
if indicador != "total_programas":
    fig.add_trace(
        go.Scatter(
            x=brasil.index,
            y=brasil[indicador],
            name="Brasil",
            mode="lines+markers",
            line=dict(color=CINZA, width=2, dash="dash"),
            marker=dict(size=8),
            hovertemplate=f"Brasil em %{{x}}: %{{y:{formato}}}{sufixo}<extra></extra>",
        )
    )
fig.update_xaxes(tickmode="array", tickvals=serie["ano_base"])
fig.update_yaxes(tickformat=formato, ticksuffix=sufixo)
if indicador == "total_programas":
    fig.update_yaxes(rangemode="tozero")
estilo(fig)
fig.update_layout(
    showlegend=True,
    legend=dict(orientation="h", y=1.08, x=0),
    margin=dict(t=40),
)
st.plotly_chart(fig, use_container_width=True)

st.caption(FONTE + " Malha das UFs: IBGE.")
