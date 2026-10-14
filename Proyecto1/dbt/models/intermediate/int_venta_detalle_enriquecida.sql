select
    detalle.id_detalle,
    detalle.id_venta,
    detalle.id_producto,
    detalle.cantidad,
    detalle.precio_unitario,
    detalle.descuento,
    detalle.subtotal,
    venta.fecha,
    venta.id_cliente,
    venta.id_sucursal,
    venta.canal,
    venta.metodo_pago,
    venta.estado,
    producto.sku,
    producto.nombre as nombre_producto,
    producto.id_categoria,
    producto.id_marca,
    producto.unidad_medida,
    detalle._etl_load_id,
    detalle._etl_loaded_at,
    detalle._etl_source_table,
    detalle._etl_extracted_at
from {{ ref('stg_oltp_venta_detalle') }} as detalle
left join {{ ref('stg_oltp_venta') }} as venta
    on detalle.id_venta = venta.id_venta
left join {{ ref('stg_oltp_producto') }} as producto
    on detalle.id_producto = producto.id_producto
