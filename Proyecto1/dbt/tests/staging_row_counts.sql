with counts as (
    select 'stg_oltp_sucursal' as model_name, (select count(*) from {{ ref('stg_oltp_sucursal') }}) as staging_count, (select count(*) from {{ source('raw', 'oltp_sucursal') }}) as source_count union all
    select 'stg_oltp_categoria', (select count(*) from {{ ref('stg_oltp_categoria') }}), (select count(*) from {{ source('raw', 'oltp_categoria') }}) union all
    select 'stg_oltp_marca', (select count(*) from {{ ref('stg_oltp_marca') }}), (select count(*) from {{ source('raw', 'oltp_marca') }}) union all
    select 'stg_oltp_producto', (select count(*) from {{ ref('stg_oltp_producto') }}), (select count(*) from {{ source('raw', 'oltp_producto') }}) union all
    select 'stg_oltp_cliente', (select count(*) from {{ ref('stg_oltp_cliente') }}), (select count(*) from {{ source('raw', 'oltp_cliente') }}) union all
    select 'stg_oltp_venta', (select count(*) from {{ ref('stg_oltp_venta') }}), (select count(*) from {{ source('raw', 'oltp_venta') }}) union all
    select 'stg_oltp_venta_detalle', (select count(*) from {{ ref('stg_oltp_venta_detalle') }}), (select count(*) from {{ source('raw', 'oltp_venta_detalle') }}) union all
    select 'stg_csv_inventario_bodega', (select count(*) from {{ ref('stg_csv_inventario_bodega') }}), (select count(*) from {{ source('raw', 'csv_inventario_bodega') }}) union all
    select 'stg_csv_devoluciones', (select count(*) from {{ ref('stg_csv_devoluciones') }}), (select count(*) from {{ source('raw', 'csv_devoluciones') }}) union all
    select 'stg_csv_metas_ventas', (select count(*) from {{ ref('stg_csv_metas_ventas') }}), (select count(*) from {{ source('raw', 'csv_metas_ventas') }}) union all
    select 'stg_csv_promociones', (select count(*) from {{ ref('stg_csv_promociones') }}), (select count(*) from {{ source('raw', 'csv_promociones') }}) union all
    select 'stg_csv_proveedores_precios', (select count(*) from {{ ref('stg_csv_proveedores_precios') }}), (select count(*) from {{ source('raw', 'csv_proveedores_precios') }})
)
select * from counts where staging_count <> source_count
