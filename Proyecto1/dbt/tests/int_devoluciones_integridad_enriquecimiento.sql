with expected as (
    select
        devolucion.id_devolucion,
        devolucion.id_venta,
        devolucion.id_producto,
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
), actual as (
    select
        id_devolucion,
        id_venta,
        id_producto,
        fecha_venta,
        id_cliente,
        id_sucursal,
        canal,
        metodo_pago,
        estado,
        sku,
        nombre_producto,
        id_categoria,
        id_marca,
        unidad_medida
    from {{ ref('int_devoluciones_enriquecida') }}
)
select
    coalesce(expected.id_devolucion, actual.id_devolucion) as id_devolucion,
    expected.id_venta as expected_id_venta,
    actual.id_venta as actual_id_venta,
    expected.id_producto as expected_id_producto,
    actual.id_producto as actual_id_producto,
    expected.fecha_venta as expected_fecha_venta,
    actual.fecha_venta as actual_fecha_venta,
    expected.id_cliente as expected_id_cliente,
    actual.id_cliente as actual_id_cliente,
    expected.id_sucursal as expected_id_sucursal,
    actual.id_sucursal as actual_id_sucursal,
    expected.canal as expected_canal,
    actual.canal as actual_canal,
    expected.metodo_pago as expected_metodo_pago,
    actual.metodo_pago as actual_metodo_pago,
    expected.estado as expected_estado,
    actual.estado as actual_estado,
    expected.sku as expected_sku,
    actual.sku as actual_sku,
    expected.nombre_producto as expected_nombre_producto,
    actual.nombre_producto as actual_nombre_producto,
    expected.id_categoria as expected_id_categoria,
    actual.id_categoria as actual_id_categoria,
    expected.id_marca as expected_id_marca,
    actual.id_marca as actual_id_marca,
    expected.unidad_medida as expected_unidad_medida,
    actual.unidad_medida as actual_unidad_medida
from expected
full outer join actual using (id_devolucion)
where expected.id_devolucion is null
   or actual.id_devolucion is null
   or expected.id_venta is distinct from actual.id_venta
   or expected.id_producto is distinct from actual.id_producto
   or expected.fecha_venta is distinct from actual.fecha_venta
   or expected.id_cliente is distinct from actual.id_cliente
   or expected.id_sucursal is distinct from actual.id_sucursal
   or expected.canal is distinct from actual.canal
   or expected.metodo_pago is distinct from actual.metodo_pago
   or expected.estado is distinct from actual.estado
   or expected.sku is distinct from actual.sku
   or expected.nombre_producto is distinct from actual.nombre_producto
   or expected.id_categoria is distinct from actual.id_categoria
   or expected.id_marca is distinct from actual.id_marca
   or expected.unidad_medida is distinct from actual.unidad_medida
   or (select count(*) from expected) is distinct from
      (select count(*) from {{ ref('stg_csv_devoluciones') }})
   or (select count(*) from actual) is distinct from
      (select count(*) from {{ ref('stg_csv_devoluciones') }})
