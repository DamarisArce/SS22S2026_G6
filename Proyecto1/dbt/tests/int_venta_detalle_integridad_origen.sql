with staging as (
    select
        id_detalle,
        id_venta,
        id_producto,
        cantidad,
        precio_unitario,
        descuento,
        subtotal
    from {{ ref('stg_oltp_venta_detalle') }}
), intermediate as (
    select
        id_detalle,
        id_venta,
        id_producto,
        cantidad,
        precio_unitario,
        descuento,
        subtotal
    from {{ ref('int_venta_detalle_enriquecida') }}
)
select
    'staging_vs_intermediate' as violation_direction,
    staging.id_detalle,
    staging.id_venta,
    intermediate.id_venta as intermediate_id_venta,
    staging.id_producto,
    intermediate.id_producto as intermediate_id_producto,
    staging.cantidad,
    intermediate.cantidad as intermediate_cantidad,
    staging.precio_unitario,
    intermediate.precio_unitario as intermediate_precio_unitario,
    staging.descuento,
    intermediate.descuento as intermediate_descuento,
    staging.subtotal,
    intermediate.subtotal as intermediate_subtotal
from staging
full outer join intermediate using (id_detalle)
where staging.id_detalle is null
   or intermediate.id_detalle is null
   or staging.id_venta is distinct from intermediate.id_venta
   or staging.id_producto is distinct from intermediate.id_producto
   or staging.cantidad is distinct from intermediate.cantidad
   or staging.precio_unitario is distinct from intermediate.precio_unitario
   or staging.descuento is distinct from intermediate.descuento
   or staging.subtotal is distinct from intermediate.subtotal
