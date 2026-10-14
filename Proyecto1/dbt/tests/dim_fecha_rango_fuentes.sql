with fuentes as (
    select fecha::date as fecha
    from {{ ref('stg_oltp_venta') }}
    where fecha is not null
    union all
    select periodo::date as fecha
    from {{ ref('int_ventas_mensuales_sucursal') }}
    where periodo is not null
),
limites_fuentes as (
    select min(fecha)::date as fecha_minima, max(fecha)::date as fecha_maxima
    from fuentes
),
limites_modelo as (
    select min(fecha)::date as fecha_minima, max(fecha)::date as fecha_maxima
    from {{ ref('dim_fecha') }}
),
anomalias as (
    select 'modelo_con_fechas_sin_fuentes' as violation,
           modelo.fecha_minima,
           modelo.fecha_maxima
    from limites_fuentes as fuentes
    cross join limites_modelo as modelo
    where fuentes.fecha_minima is null
      and (modelo.fecha_minima is not null or modelo.fecha_maxima is not null)
    union all
    select 'limites_modelo_no_coinciden_con_fuentes' as violation,
           modelo.fecha_minima,
           modelo.fecha_maxima
    from limites_fuentes as fuentes
    cross join limites_modelo as modelo
    where fuentes.fecha_minima is not null
      and (modelo.fecha_minima is distinct from fuentes.fecha_minima
           or modelo.fecha_maxima is distinct from fuentes.fecha_maxima)
)
select *
from anomalias
