with origen as (
    select distinct
        date_trunc('month', fecha)::date as periodo,
        id_sucursal
    from {{ ref('int_venta_detalle_enriquecida') }}
), modelo as (
    select distinct
        periodo,
        id_sucursal
    from {{ ref('int_ventas_mensuales_sucursal') }}
), distribucion as (
    select
        origen.periodo as origen_periodo,
        modelo.periodo as modelo_periodo,
        origen.id_sucursal as origen_id_sucursal,
        modelo.id_sucursal as modelo_id_sucursal
    from origen
    full outer join modelo
        on origen.periodo = modelo.periodo
       and origen.id_sucursal = modelo.id_sucursal
    where origen.periodo is null
       or modelo.periodo is null
       or origen.id_sucursal is null
       or modelo.id_sucursal is null
)
select
    periodo,
    id_sucursal,
    'periodo_no_es_primer_dia' as violation
from {{ ref('int_ventas_mensuales_sucursal') }}
where periodo <> date_trunc('month', periodo)::date
union all
select
    coalesce(origen_periodo, modelo_periodo) as periodo,
    coalesce(origen_id_sucursal, modelo_id_sucursal) as id_sucursal,
    'combinacion_periodo_sucursal_no_coincide' as violation
from distribucion
