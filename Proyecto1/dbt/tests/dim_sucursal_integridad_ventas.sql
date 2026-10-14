select
    ventas.id_sucursal,
    count(*) as ventas_sin_sucursal
from {{ ref('fct_ventas_detalle') }} as ventas
left join {{ ref('dim_sucursal') }} as sucursal
    on ventas.id_sucursal = sucursal.id_sucursal
where sucursal.id_sucursal is null
group by ventas.id_sucursal
