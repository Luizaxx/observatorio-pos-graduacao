with origem as (

    select * from {{ source('bronze', 'capes_programas') }}

),

-- Se o mesmo arquivo for carregado mais de uma vez, fica a carga mais recente.
deduplicado as (

    select
        *,
        row_number() over (
            partition by cd_programa_ies, an_base
            order by _carregado_em desc
        ) as _ordem
    from origem

),

final as (

    select
        -- chaves
        cd_programa_ies                                        as codigo_programa,
        an_base::int                                           as ano_base,

        -- programa
        nm_programa_ies                                        as nome_programa,
        nullif(trim(nm_programa_idioma), '')                   as nome_programa_ingles,
        nm_modalidade_programa                                 as modalidade,
        nm_grau_programa                                       as grau,
        -- "A" indica curso novo aprovado que ainda não passou por avaliação
        case
            when cd_conceito_programa ~ '^[1-7]$' then cd_conceito_programa::int
        end                                                    as conceito,
        cd_conceito_programa = 'A'                             as sem_avaliacao,
        ds_situacao_programa                                   as situacao,
        to_date(left(dt_situacao_programa, 9), 'DDMONYYYY')    as data_situacao,
        an_inicio_programa::int                                as ano_inicio_programa,
        -- formato "mestrado/doutorado", mas a ordem não é confiável em todos os anos
        an_inicio_curso                                        as anos_inicio_cursos,
        in_rede = 'SIM'                                        as em_rede,
        nullif(trim(sg_entidade_ensino_rede), '')              as sigla_ies_rede,

        -- área do conhecimento
        nm_grande_area_conhecimento                            as grande_area,
        nm_area_conhecimento                                   as area_conhecimento,
        nm_area_basica                                         as area_basica,
        nm_subarea_conhecimento                                as subarea_conhecimento,
        nm_especialidade                                       as especialidade,
        cd_area_avaliacao::int                                 as codigo_area_avaliacao,
        nm_area_avaliacao                                      as area_avaliacao,

        -- instituição
        cd_entidade_capes                                      as codigo_ies_capes,
        cd_entidade_emec                                       as codigo_ies_emec,
        sg_entidade_ensino                                     as sigla_ies,
        nm_entidade_ensino                                     as nome_ies,
        cs_status_juridico                                     as status_juridico,
        ds_dependencia_administrativa                          as dependencia_administrativa,
        ds_organizacao_academica                               as organizacao_academica,

        -- localização
        upper(trim(nm_regiao))                                 as regiao,
        upper(trim(sg_uf_programa))                            as uf,
        nm_municipio_programa_ies                              as municipio,

        -- linhagem
        _arquivo_origem                                        as arquivo_origem,
        _carregado_em                                          as carregado_em

    from deduplicado
    where _ordem = 1

)

select * from final
