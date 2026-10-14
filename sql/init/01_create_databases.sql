-- Executado só na primeira subida do container (volume vazio).
-- "observatorio" já é criado pelo POSTGRES_DB; aqui criamos o banco de metadados do Airflow
-- e os schemas da arquitetura medalhão.

CREATE DATABASE airflow;

\connect observatorio
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS prata;
CREATE SCHEMA IF NOT EXISTS ouro;
