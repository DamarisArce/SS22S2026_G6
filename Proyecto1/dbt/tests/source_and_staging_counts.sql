{{ config(enabled=var('enable_academic_snapshot', false)) }}

with expected as (
    select 'raw.oltp_sucursal' as relation_name, 6 as expected_count union all
    select 'raw.oltp_categoria', 8 union all
    select 'raw.oltp_marca', 10 union all
    select 'raw.oltp_producto', 80 union all
    select 'raw.oltp_cliente', 250 union all
    select 'raw.oltp_venta', 1200 union all
    select 'raw.oltp_venta_detalle', 3209 union all
    select 'raw.csv_inventario_bodega', 3840 union all
    select 'raw.csv_devoluciones', 80 union all
    select 'raw.csv_metas_ventas', 48 union all
    select 'raw.csv_promociones', 30 union all
    select 'raw.csv_proveedores_precios', 103
), actual as (
    select 'raw.oltp_sucursal' as relation_name, count(*) as actual_count from {{ source('raw', 'oltp_sucursal') }} union all
    select 'raw.oltp_categoria', count(*) from {{ source('raw', 'oltp_categoria') }} union all
    select 'raw.oltp_marca', count(*) from {{ source('raw', 'oltp_marca') }} union all
    select 'raw.oltp_producto', count(*) from {{ source('raw', 'oltp_producto') }} union all
    select 'raw.oltp_cliente', count(*) from {{ source('raw', 'oltp_cliente') }} union all
    select 'raw.oltp_venta', count(*) from {{ source('raw', 'oltp_venta') }} union all
    select 'raw.oltp_venta_detalle', count(*) from {{ source('raw', 'oltp_venta_detalle') }} union all
    select 'raw.csv_inventario_bodega', count(*) from {{ source('raw', 'csv_inventario_bodega') }} union all
    select 'raw.csv_devoluciones', count(*) from {{ source('raw', 'csv_devoluciones') }} union all
    select 'raw.csv_metas_ventas', count(*) from {{ source('raw', 'csv_metas_ventas') }} union all
    select 'raw.csv_promociones', count(*) from {{ source('raw', 'csv_promociones') }} union all
    select 'raw.csv_proveedores_precios', count(*) from {{ source('raw', 'csv_proveedores_precios') }}
)
select expected.relation_name, expected.expected_count, actual.actual_count
from expected
join actual using (relation_name)
where expected.expected_count <> actual.actual_count
