import streamlit as st

st.set_page_config(
    page_title="Observatório da Pós-Graduação",
    page_icon="🎓",
    layout="wide",
)

paginas = [
    st.Page("paginas/visao_geral.py", title="Visão geral", default=True),
    st.Page("paginas/por_uf.py", title="Por UF"),
    st.Page("paginas/por_area.py", title="Por área"),
    st.Page("paginas/busca.py", title="Busca de programas"),
]

st.navigation(paginas).run()
