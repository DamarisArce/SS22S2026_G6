with modelo as (
    select fecha, anio, anio_iso, trimestre, mes, dia_mes, dia_semana,
           numero_semana, inicio_mes, fin_mes, inicio_trimestre, inicio_anio,
           es_fin_semana
    from {{ ref('dim_fecha') }}
),
esperado as (
    select fecha,
           extract(year from fecha)::integer as anio,
           extract(isoyear from fecha)::integer as anio_iso,
           extract(quarter from fecha)::smallint as trimestre,
           extract(month from fecha)::smallint as mes,
           extract(day from fecha)::smallint as dia_mes,
           extract(isodow from fecha)::smallint as dia_semana,
           extract(week from fecha)::smallint as numero_semana,
           date_trunc('month', fecha)::date as inicio_mes,
           (date_trunc('month', fecha) + interval '1 month - 1 day')::date as fin_mes,
           date_trunc('quarter', fecha)::date as inicio_trimestre,
           date_trunc('year', fecha)::date as inicio_anio,
           (extract(isodow from fecha) in (6, 7))::boolean as es_fin_semana
    from modelo
),
violaciones as (
    select modelo.fecha, 'anio' as violation from modelo join esperado using (fecha)
    where modelo.anio is distinct from esperado.anio
    union all
    select modelo.fecha, 'anio_iso' from modelo join esperado using (fecha)
    where modelo.anio_iso is distinct from esperado.anio_iso
    union all
    select modelo.fecha, 'trimestre' from modelo join esperado using (fecha)
    where modelo.trimestre is distinct from esperado.trimestre
    union all
    select modelo.fecha, 'mes' from modelo join esperado using (fecha)
    where modelo.mes is distinct from esperado.mes
    union all
    select modelo.fecha, 'dia_mes' from modelo join esperado using (fecha)
    where modelo.dia_mes is distinct from esperado.dia_mes
    union all
    select modelo.fecha, 'dia_semana_iso' from modelo join esperado using (fecha)
    where modelo.dia_semana is distinct from esperado.dia_semana
    union all
    select modelo.fecha, 'numero_semana_iso' from modelo join esperado using (fecha)
    where modelo.numero_semana is distinct from esperado.numero_semana
    union all
    select modelo.fecha, 'inicio_mes' from modelo join esperado using (fecha)
    where modelo.inicio_mes is distinct from esperado.inicio_mes
    union all
    select modelo.fecha, 'fin_mes' from modelo join esperado using (fecha)
    where modelo.fin_mes is distinct from esperado.fin_mes
    union all
    select modelo.fecha, 'inicio_trimestre' from modelo join esperado using (fecha)
    where modelo.inicio_trimestre is distinct from esperado.inicio_trimestre
    union all
    select modelo.fecha, 'inicio_anio' from modelo join esperado using (fecha)
    where modelo.inicio_anio is distinct from esperado.inicio_anio
    union all
    select modelo.fecha, 'es_fin_semana' from modelo join esperado using (fecha)
    where modelo.es_fin_semana is distinct from esperado.es_fin_semana
)
select fecha, violation
from violaciones
