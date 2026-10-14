select
    date_trunc('month', fecha)::date as periodo,
    id_sucursal,
    count(*) as lineas_registradas,
    count(distinct id_venta) as ventas_distintas_registradas,
    sum(cantidad) as cantidad_registrada,
    sum(subtotal) as subtotal_registrado
from {{ ref('int_venta_detalle_enriquecida') }} as venta_detalle
group by periodo, id_sucursal
