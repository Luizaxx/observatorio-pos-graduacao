with programas as (

    select * from {{ ref('stg_capes__programas') }}

),

-- Algumas áreas mudaram de nome entre os anos; usamos o nome mais recente
-- para a série histórica ficar contínua.
nome_atual_area as (

    select distinct on (codigo_area_avaliacao)
        codigo_area_avaliacao,
        area_avaliacao
    from programas
    order by codigo_area_avaliacao, ano_base desc

)

select
    p.ano_base,
    p.grande_area,
    p.codigo_area_avaliacao,
    n.area_avaliacao,
{{ metricas_programas() }}
from programas p
join nome_atual_area n using (codigo_area_avaliacao)
group by 1, 2, 3, 4
