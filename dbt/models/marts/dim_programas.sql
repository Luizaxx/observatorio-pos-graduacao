with programas as (

    select * from {{ ref('stg_capes__programas') }}

),

historico as (

    select
        codigo_programa,
        min(ano_base)   as primeiro_ano_base,
        max(ano_base)   as ultimo_ano_base,
        count(*)        as anos_na_base
    from programas
    group by 1

),

mais_recente as (

    select distinct on (codigo_programa) *
    from programas
    order by codigo_programa, ano_base desc

)

select
    r.codigo_programa,
    r.nome_programa,
    r.nome_programa_ingles,
    r.modalidade,
    r.grau,
    r.conceito,
    r.sem_avaliacao,
    r.situacao,
    r.data_situacao,
    r.ano_inicio_programa,
    r.em_rede,
    r.grande_area,
    r.area_conhecimento,
    r.codigo_area_avaliacao,
    r.area_avaliacao,
    r.codigo_ies_capes,
    r.sigla_ies,
    r.nome_ies,
    r.status_juridico,
    r.dependencia_administrativa,
    r.regiao,
    r.uf,
    r.municipio,
    h.primeiro_ano_base,
    h.ultimo_ano_base,
    h.anos_na_base,
    h.ultimo_ano_base = (select max(ano_base) from programas) as presente_na_ultima_coleta
from mais_recente r
join historico h using (codigo_programa)
