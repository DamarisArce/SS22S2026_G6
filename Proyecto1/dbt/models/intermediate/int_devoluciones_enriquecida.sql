select
    devolucion.id_devolucion,
    devolucion.fecha,
    devolucion.id_venta,
    devolucion.id_producto,
    devolucion.cantidad,
    devolucion.motivo,
    devolucion._etl_load_id,
    devolucion._etl_loaded_at,
    devolucion._etl_source_name,
    devolucion._etl_source_sha256,
    devolucion._etl_row_number,
    venta.fecha as fecha_venta,
    venta.id_cliente,
    venta.id_sucursal,
    venta.canal,
    venta.metodo_pago,
    venta.estado,
    producto.sku,
    producto.nombre as nombre_producto,
    producto.id_categoria,
    producto.id_marca,
    producto.unidad_medida
from {{ ref('stg_csv_devoluciones') }} as devolucion
left join {{ ref('stg_oltp_venta') }} as venta
    on devolucion.id_venta = venta.id_venta
left join {{ ref('stg_oltp_producto') }} as producto
    on devolucion.id_producto = producto.id_producto
