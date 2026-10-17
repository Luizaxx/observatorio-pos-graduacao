"""Padrões visuais compartilhados pelos gráficos do painel."""

import plotly.graph_objects as go

AZUL = "#2a78d6"
FONTE = "Fonte: CAPES, Coleta Sucupira."


def numero(valor: float, casas: int = 0, sinal: bool = False) -> str:
    """Formata no padrão brasileiro: 4.635 / 4,38 / +3,6."""
    texto = f"{valor:{'+' if sinal else ''},.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def estilo(fig: go.Figure, altura: int = 360) -> go.Figure:
    """Fundo transparente, grade discreta e números no padrão brasileiro."""
    fig.update_layout(
        height=altura,
        separators=",.",
        bargap=0.45,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig
