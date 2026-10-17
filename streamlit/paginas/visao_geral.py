import plotly.graph_objects as go
import streamlit as st

from db import consultar
from graficos import AZUL, FONTE, estilo, numero

# O conceito médio nacional é a média dos conceitos ponderada pelos programas
# avaliados de cada UF, o que equivale à média sobre todos os programas.
por_ano = consultar(
    """
    select
        ano_base,
        sum(total_programas)                                       as total,
        sum(programas_com_doutorado)                               as com_doutorado,
        sum(programas_nota_6_7)                                    as nota_6_7,
        sum(programas_avaliados)                                   as avaliados,
        sum(conceito_medio * programas_avaliados) / sum(programas_avaliados) as conceito_medio
    from ouro.fct_programas_por_uf_ano
    group by ano_base
    order by ano_base
    """
)
por_ano["pct_doutorado"] = 100 * por_ano["com_doutorado"] / por_ano["total"]
por_ano["pct_nota_6_7"] = 100 * por_ano["nota_6_7"] / por_ano["avaliados"]

atual = por_ano.iloc[-1]
anterior = por_ano.iloc[-2] if len(por_ano) > 1 else None
ano = int(atual["ano_base"])


def variacao(coluna: str, casas: int = 0, sufixo: str = "") -> str | None:
    if anterior is None:
        return None
    return numero(atual[coluna] - anterior[coluna], casas, sinal=True) + sufixo


st.title("Observatório da Pós-Graduação")
st.caption(
    f"Programas de mestrado e doutorado no Brasil. Ano-base {ano}, "
    f"comparado com {ano - 1}."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Programas", numero(atual["total"]), variacao("total"))
c2.metric("Conceito médio", numero(atual["conceito_medio"], 2),
          variacao("conceito_medio", 2),
          help="Média da nota CAPES (1 a 7) entre os programas avaliados.")
c3.metric("Com doutorado", numero(atual["pct_doutorado"], 1) + "%",
          variacao("pct_doutorado", 1, " p.p."))
c4.metric("Nota 6 ou 7", numero(atual["pct_nota_6_7"], 1) + "%",
          variacao("pct_nota_6_7", 1, " p.p."),
          help="Percentual de programas avaliados com nível de excelência internacional.")

st.divider()

esq, dir_ = st.columns(2, gap="large")

with esq:
    st.subheader("Programas por ano-base")
    fig = go.Figure(
        go.Scatter(
            x=por_ano["ano_base"],
            y=por_ano["total"],
            mode="lines+markers",
            line=dict(color=AZUL, width=2),
            marker=dict(size=9),
            hovertemplate="%{x}: %{y:,.0f} programas<extra></extra>",
        )
    )
    fig.update_xaxes(tickmode="array", tickvals=por_ano["ano_base"])
    fig.update_yaxes(tickformat=",.0f", rangemode="tozero")
    st.plotly_chart(estilo(fig), use_container_width=True)

with dir_:
    st.subheader(f"Programas por região em {ano}")
    por_regiao = consultar(
        """
        select regiao, sum(total_programas) as total
        from ouro.fct_programas_por_uf_ano
        where ano_base = :ano
        group by regiao
        order by total
        """,
        ano=ano,
    )
    fig = go.Figure(
        go.Bar(
            x=por_regiao["total"],
            y=por_regiao["regiao"].str.title(),
            orientation="h",
            marker=dict(color=AZUL, cornerradius=4),
            text=por_regiao["total"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,.0f} programas<extra></extra>",
        )
    )
    # folga à direita para o rótulo da maior barra não ser cortado
    fig.update_xaxes(visible=False, range=[0, por_regiao["total"].max() * 1.15])
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(estilo(fig), use_container_width=True)

with st.expander("Ver dados por ano"):
    tabela = por_ano[["ano_base", "total", "conceito_medio", "pct_doutorado", "pct_nota_6_7"]]
    st.dataframe(
        tabela,
        hide_index=True,
        use_container_width=True,
        column_config={
            "ano_base": st.column_config.NumberColumn("Ano-base", format="%d"),
            "total": st.column_config.NumberColumn("Programas"),
            "conceito_medio": st.column_config.NumberColumn("Conceito médio", format="%.2f"),
            "pct_doutorado": st.column_config.NumberColumn("% com doutorado", format="%.1f"),
            "pct_nota_6_7": st.column_config.NumberColumn("% nota 6 ou 7", format="%.1f"),
        },
    )

st.caption(FONTE)
