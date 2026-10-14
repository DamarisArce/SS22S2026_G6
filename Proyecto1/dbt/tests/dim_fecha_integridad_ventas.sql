select ventas.fecha, 'fecha_de_venta_ausente_en_dim_fecha' as violation
from {{ ref('fct_ventas_detalle') }} as ventas
left join {{ ref('dim_fecha') }} as calendario
    on calendario.fecha = ventas.fecha
where ventas.fecha is not null
  and calendario.fecha is null
