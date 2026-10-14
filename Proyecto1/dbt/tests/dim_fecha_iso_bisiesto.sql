with fixtures as (
    select date '2021-01-01' as fecha,
           2020::integer as anio_iso_esperado,
           53::smallint as semana_esperada,
           false::boolean as es_fin_semana_esperado
    union all
    select date '2024-02-29' as fecha,
           2024::integer as anio_iso_esperado,
           9::smallint as semana_esperada,
           false::boolean as es_fin_semana_esperado
),
calculadas as (
    select fecha,
           extract(isoyear from fecha)::integer as anio_iso,
           extract(week from fecha)::smallint as numero_semana,
           extract(month from fecha)::smallint as mes,
           extract(day from fecha)::smallint as dia_mes,
           (extract(isodow from fecha) in (6, 7))::boolean as es_fin_semana
    from fixtures
)
select calculadas.fecha, 'fixture_iso_o_bisiesto_invalida' as violation
from calculadas
join fixtures using (fecha)
where calculadas.anio_iso is distinct from fixtures.anio_iso_esperado
   or calculadas.numero_semana is distinct from fixtures.semana_esperada
   or calculadas.es_fin_semana is distinct from fixtures.es_fin_semana_esperado
   or (calculadas.fecha = date '2024-02-29'
       and (calculadas.mes, calculadas.dia_mes) is distinct from (2::smallint, 29::smallint))
