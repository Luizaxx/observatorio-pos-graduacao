-- Sem essa macro o dbt concatena o schema do profile com o +schema do modelo
-- (ex.: public_prata). Aqui usamos o +schema direto quando ele existe.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
