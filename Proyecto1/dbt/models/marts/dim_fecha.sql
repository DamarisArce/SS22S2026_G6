{{ config(materialized='view', schema='marts') }}

with fechas_fuente as (
    select fecha::date as fecha
    from {{ ref('stg_oltp_venta') }}
    where fecha is not null

    union all

    select periodo::date as fecha
    from {{ ref('int_ventas_mensuales_sucursal') }}
    where periodo is not null
),
limites as (
    select
        min(fecha)::date as fecha_minima,
        max(fecha)::date as fecha_maxima
    from fechas_fuente
),
calendario as (
    select serie.fecha_generada::date as fecha
    from limites
    cross join lateral generate_series(
        limites.fecha_minima::timestamp without time zone,
        limites.fecha_maxima::timestamp without time zone,
        interval '1 day'
    ) as serie(fecha_generada)
)
select
    calendario.fecha::date as fecha,
    extract(year from calendario.fecha)::integer as anio,
    extract(isoyear from calendario.fecha)::integer as anio_iso,
    extract(quarter from calendario.fecha)::smallint as trimestre,
    extract(month from calendario.fecha)::smallint as mes,
    extract(day from calendario.fecha)::smallint as dia_mes,
    extract(isodow from calendario.fecha)::smallint as dia_semana,
    extract(week from calendario.fecha)::smallint as numero_semana,
    date_trunc('month', calendario.fecha)::date as inicio_mes,
    (date_trunc('month', calendario.fecha) + interval '1 month - 1 day')::date as fin_mes,
    date_trunc('quarter', calendario.fecha)::date as inicio_trimestre,
    date_trunc('year', calendario.fecha)::date as inicio_anio,
    (extract(isodow from calendario.fecha) in (6, 7))::boolean as es_fin_semana
from calendario
