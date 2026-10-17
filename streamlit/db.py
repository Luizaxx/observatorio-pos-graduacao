"""Acesso ao banco. As consultas ficam em cache por 10 minutos para o painel não
bater no Postgres a cada interação."""

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# Fora do Docker, conecta no Postgres exposto no host
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://obs:obs@localhost:5434/observatorio"
)


@st.cache_resource
def _engine():
    return create_engine(DATABASE_URL)


@st.cache_data(ttl=600, show_spinner=False)
def consultar(sql: str, **params) -> pd.DataFrame:
    with _engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)
