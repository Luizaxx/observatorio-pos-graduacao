-- O total de programas por ano nas tabelas agregadas tem que ser igual ao da prata.
-- Retorna os anos em que alguma das tabelas diverge.
with prata as (
    select ano_base, count(*) as total
    from {{ ref('stg_capes__programas') }}
    group by 1
),

por_uf as (
    select ano_base, sum(total_programas) as total
    from {{ ref('fct_programas_por_uf_ano') }}
    group by 1
),

por_area as (
    select ano_base, sum(total_programas) as total
    from {{ ref('fct_programas_por_area_ano') }}
    group by 1
)

select
    p.ano_base,
    p.total     as total_prata,
    u.total     as total_por_uf,
    a.total     as total_por_area
from prata p
left join por_uf u using (ano_base)
left join por_area a using (ano_base)
where u.total is distinct from p.total
   or a.total is distinct from p.total
