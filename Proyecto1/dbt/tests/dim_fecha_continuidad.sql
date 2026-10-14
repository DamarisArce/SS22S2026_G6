with ordenadas as (
    select fecha, lead(fecha) over (order by fecha) as siguiente_fecha
    from {{ ref('dim_fecha') }}
),
violaciones as (
    select fecha, 'fecha_nula' as violation
    from ordenadas
    where fecha is null
    union all
    select fecha, 'hueco_en_calendario' as violation
    from ordenadas
    where siguiente_fecha is not null
      and siguiente_fecha <> fecha + 1
    union all
    select min(fecha), 'cantidad_no_coherente_con_rango' as violation
    from ordenadas
    having count(*) <> (max(fecha) - min(fecha) + 1)
)
select fecha, violation
from violaciones
