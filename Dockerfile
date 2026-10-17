FROM apache/airflow:2.10.5-python3.11

# dbt fica num venv separado para não brigar com as dependências do Airflow
COPY dbt/requirements.txt /tmp/dbt-requirements.txt
RUN python -m venv /home/airflow/dbt-venv \
    && /home/airflow/dbt-venv/bin/pip install --no-cache-dir -r /tmp/dbt-requirements.txt
