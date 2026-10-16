select
    ano_base,
    regiao,
    uf,
{{ metricas_programas() }}
from {{ ref('stg_capes__programas') }}
group by 1, 2, 3
