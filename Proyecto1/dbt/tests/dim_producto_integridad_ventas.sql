select
    ventas.id_producto,
    count(*) as ventas_sin_producto
from {{ ref('fct_ventas_detalle') }} as ventas
left join {{ ref('dim_producto') }} as producto
    on ventas.id_producto = producto.id_producto
where producto.id_producto is null
group by ventas.id_producto
