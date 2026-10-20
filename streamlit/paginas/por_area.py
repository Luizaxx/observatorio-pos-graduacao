import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import consultar
from graficos import AZUL, CINZA, FONTE, estilo, nome, numero
from indicadores import INDICADORES, agregar, com_percentuais

# Grandes áreas que não estão em foco no comparativo
AZUL_CLARO = "#9ec5f4"

# Biodiversidade aparece em duas grandes áreas (a maior parte em Ciências
# Biológicas). Por isso o ranking e a evolução ficam sempre dentro da grande
# área escolhida.
dados = com_percentuais(
    consultar("select * from ouro.fct_programas_por_area_ano order by ano_base")
)
dados["grande_area"] = dados["grande_area"].map(nome)
dados["area_avaliacao"] = dados["area_avaliacao"].map(nome)

por_grande_area = agregar(dados, ["ano_base", "grande_area"]).reset_index()


def barras(df, coluna, rotulos, cores, formato, sufixo="", altura=360):
    fig = go.Figure(
        go.Bar(
            x=df[coluna],
            y=df[rotulos],
            orientation="h",
            marker=dict(color=cores, cornerradius=4),
            text=df[coluna],
            texttemplate=f"%{{text:{formato}}}{sufixo}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"%{{y}}: %{{x:{formato}}}{sufixo}<extra></extra>",
        )
    )
    # folga à direita para o rótulo da maior barra não ser cortado
    fig.update_xaxes(visible=False, range=[0, df[coluna].max() * 1.18])
    fig.update_yaxes(showgrid=False)
    fig.update_layout(bargap=0.3)
    return estilo(fig, altura=altura)


st.title("Indicadores por área")
st.caption(
    "Compare as grandes áreas do conhecimento e as áreas de avaliação da CAPES "
    "dentro de cada uma."
)

anos = sorted(dados["ano_base"].unique(), reverse=True)
grandes_areas = sorted(dados["grande_area"].unique(), key=str.lower)
f1, f2, _ = st.columns([1, 2, 3])
ano = f1.selectbox("Ano-base", anos)
grande_area = f2.selectbox("Grande área", grandes_areas)

st.divider()

st.subheader(f"Grandes áreas em {ano}")
st.caption(f"{grande_area} em destaque.")
do_ano = por_grande_area[por_grande_area["ano_base"] == ano]

esq, dir_ = st.columns(2, gap="large")
for coluna, col, formato in [
    ("total_programas", esq, ",.0f"),
    ("conceito_medio", dir_, ",.2f"),
]:
    ordenado = do_ano.sort_values(coluna)
    cores = [AZUL if g == grande_area else AZUL_CLARO for g in ordenado["grande_area"]]
    with col:
        st.markdown(f"**{INDICADORES[coluna][0]}**")
        st.plotly_chart(
            barras(ordenado, coluna, "grande_area", cores, formato),
            use_container_width=True,
        )

st.divider()

st.subheader(f"Áreas de avaliação em {grande_area}")
indicador = st.columns([2, 4])[0].selectbox(
    "Indicador", list(INDICADORES), format_func=lambda c: INDICADORES[c][0]
)
rotulo, casas, sufixo = INDICADORES[indicador]
formato = f",.{casas}f"

areas = dados[(dados["ano_base"] == ano) & (dados["grande_area"] == grande_area)]
referencia = do_ano.set_index("grande_area").loc[grande_area, indicador]

ranking = areas[["area_avaliacao", indicador]]
# Para o total, a soma da grande área não serve de referência ao lado de uma área
if indicador != "total_programas":
    ranking = pd.concat(
        [ranking, pd.DataFrame({"area_avaliacao": [grande_area], indicador: [referencia]})]
    )
    st.caption(f"Barra cinza: {grande_area} como um todo.")
ranking = ranking.sort_values(indicador)
cores = [CINZA if a == grande_area else AZUL for a in ranking["area_avaliacao"]]
st.plotly_chart(
    barras(ranking, indicador, "area_avaliacao", cores, formato, sufixo,
           altura=60 + 32 * len(ranking)),
    use_container_width=True,
)

with st.expander(f"Ver todos os indicadores das áreas em {ano}"):
    colunas = ["area_avaliacao", "programas_avaliados", *INDICADORES]
    st.dataframe(
        areas.sort_values("total_programas", ascending=False)[colunas],
        hide_index=True,
        use_container_width=True,
        column_config={
            "area_avaliacao": "Área de avaliação",
            "programas_avaliados": st.column_config.NumberColumn("Avaliados"),
            "total_programas": st.column_config.NumberColumn("Programas"),
            "conceito_medio": st.column_config.NumberColumn("Conceito médio", format="%.2f"),
            "pct_doutorado": st.column_config.NumberColumn("% com doutorado", format="%.1f"),
            "pct_nota_6_7": st.column_config.NumberColumn("% nota 6 ou 7", format="%.1f"),
            "pct_profissionais": st.column_config.NumberColumn("% profissionais", format="%.1f"),
        },
    )

st.divider()

st.subheader("Evolução de uma área")
nomes_areas = sorted(areas["area_avaliacao"], key=str.lower)
area = st.columns([2, 4])[0].selectbox("Área de avaliação", nomes_areas)
serie = dados[(dados["grande_area"] == grande_area) & (dados["area_avaliacao"] == area)]
serie_grande_area = por_grande_area[por_grande_area["grande_area"] == grande_area]

fig = go.Figure(
    go.Scatter(
        x=serie["ano_base"],
        y=serie[indicador],
        name=area,
        mode="lines+markers",
        line=dict(color=AZUL, width=2),
        marker=dict(size=9),
        hovertemplate=f"{area}<br>%{{x}}: %{{y:{formato}}}{sufixo}<extra></extra>",
    )
)
# Como no ranking, a referência da grande área só aparece para médias e percentuais
if indicador != "total_programas":
    fig.add_trace(
        go.Scatter(
            x=serie_grande_area["ano_base"],
            y=serie_grande_area[indicador],
            name=grande_area,
            mode="lines+markers",
            line=dict(color=CINZA, width=2, dash="dash"),
            marker=dict(size=8),
            hovertemplate=f"{grande_area}<br>%{{x}}: %{{y:{formato}}}{sufixo}<extra></extra>",
        )
    )
fig.update_xaxes(tickmode="array", tickvals=sorted(dados["ano_base"].unique()))
fig.update_yaxes(tickformat=formato, ticksuffix=sufixo)
if indicador == "total_programas":
    fig.update_yaxes(rangemode="tozero")
estilo(fig)
fig.update_layout(
    showlegend=True,
    legend=dict(orientation="h", y=1.08, x=0),
    margin=dict(t=40),
)
st.caption(f"{rotulo} ao longo dos anos.")
st.plotly_chart(fig, use_container_width=True)

st.caption(FONTE)
