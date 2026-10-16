-- Métricas comuns às tabelas agregadas da camada ouro.
-- O conceito médio considera só programas avaliados (exclui conceito "A").
{% macro metricas_programas() %}
        count(*)                                                  as total_programas,
        count(*) filter (where situacao = 'EM FUNCIONAMENTO')     as programas_em_funcionamento,
        count(*) filter (where modalidade = 'ACADÊMICO')          as programas_academicos,
        count(*) filter (where modalidade = 'PROFISSIONAL')       as programas_profissionais,
        count(*) filter (where grau like '%DOUTORADO%')           as programas_com_doutorado,
        count(conceito)                                           as programas_avaliados,
        round(avg(conceito), 2)                                   as conceito_medio,
        count(*) filter (where conceito >= 6)                     as programas_nota_6_7,
        round(
            100.0 * count(*) filter (where conceito >= 6) / nullif(count(conceito), 0),
            1
        )                                                         as pct_nota_6_7
{% endmacro %}
