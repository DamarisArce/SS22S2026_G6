select
    inventario.fecha_corte,
    inventario.id_sucursal,
    inventario.id_producto,
    inventario.lote,
    inventario.stock_disponible,
    inventario.stock_minimo,
    inventario.stock_maximo,
    inventario.fecha_vencimiento,
    inventario._etl_load_id,
    inventario._etl_loaded_at,
    inventario._etl_source_name,
    inventario._etl_source_sha256,
    inventario._etl_row_number,
    producto.sku,
    producto.nombre as nombre_producto,
    sucursal.nombre as nombre_sucursal,
    case
        when inventario.fecha_vencimiento is null then null
        else inventario.fecha_vencimiento < inventario.fecha_corte
    end as es_vencido_en_corte,
    case
        when inventario.fecha_vencimiento is null then null
        else inventario.fecha_vencimiento - inventario.fecha_corte
    end as dias_para_vencer
from {{ ref('stg_csv_inventario_bodega') }} as inventario
left join {{ ref('stg_oltp_producto') }} as producto
    on inventario.id_producto = producto.id_producto
left join {{ ref('stg_oltp_sucursal') }} as sucursal
    on inventario.id_sucursal = sucursal.id_sucursal
