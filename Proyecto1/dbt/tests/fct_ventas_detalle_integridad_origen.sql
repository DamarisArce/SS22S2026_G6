with origen as (
    select
        id_detalle,
        id_venta,
        id_producto,
        id_cliente,
        id_sucursal,
        fecha,
        cantidad,
        precio_unitario,
        descuento,
        subtotal,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from {{ ref('int_venta_detalle_enriquecida') }}
), mart as (
    select
        id_detalle,
        id_venta,
        id_producto,
        id_cliente,
        id_sucursal,
        fecha,
        cantidad,
        precio_unitario,
        descuento,
        subtotal,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from {{ ref('fct_ventas_detalle') }}
), origen_minus_mart as (
    select
        id_detalle,
        id_venta,
        id_producto,
        id_cliente,
        id_sucursal,
        fecha,
        cantidad,
        precio_unitario,
        descuento,
        subtotal,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from origen
    except all
    select
        id_detalle,
        id_venta,
        id_producto,
        id_cliente,
        id_sucursal,
        fecha,
        cantidad,
        precio_unitario,
        descuento,
        subtotal,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from mart
), mart_minus_origen as (
    select
        id_detalle,
        id_venta,
        id_producto,
        id_cliente,
        id_sucursal,
        fecha,
        cantidad,
        precio_unitario,
        descuento,
        subtotal,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from mart
    except all
    select
        id_detalle,
        id_venta,
        id_producto,
        id_cliente,
        id_sucursal,
        fecha,
        cantidad,
        precio_unitario,
        descuento,
        subtotal,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from origen
)
select 'origen_minus_mart' as violation_direction, difference.*
from origen_minus_mart as difference
union all
select 'mart_minus_origen' as violation_direction, difference.*
from mart_minus_origen as difference
