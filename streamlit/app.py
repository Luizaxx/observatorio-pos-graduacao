import streamlit as st

st.set_page_config(
    page_title="Observatório da Pós-Graduação",
    page_icon="🎓",
    layout="wide",
)

paginas = [
    st.Page("paginas/visao_geral.py", title="Visão geral", default=True),
]

st.navigation(paginas).run()
