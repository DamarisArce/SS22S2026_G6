with recalculado as (
    select
        fecha_corte,
        id_sucursal,
        id_producto,
        lote,
        fecha_vencimiento,
        case
            when fecha_vencimiento is null then null
            when fecha_vencimiento = fecha_corte then false
            else fecha_vencimiento < fecha_corte
        end as es_vencido_en_corte_esperado,
        case
            when fecha_vencimiento is null then null
            when fecha_vencimiento = fecha_corte then 0
            else fecha_vencimiento - fecha_corte
        end as dias_para_vencer_esperado
    from {{ ref('stg_csv_inventario_bodega') }}
), snapshot as (
    select
        fecha_corte,
        id_sucursal,
        id_producto,
        lote,
        fecha_vencimiento,
        es_vencido_en_corte,
        dias_para_vencer
    from {{ ref('int_inventario_snapshot') }}
)
select
    recalculado.fecha_corte,
    recalculado.id_sucursal,
    recalculado.id_producto,
    recalculado.lote,
    recalculado.fecha_vencimiento,
    snapshot.es_vencido_en_corte,
    recalculado.es_vencido_en_corte_esperado,
    snapshot.dias_para_vencer,
    recalculado.dias_para_vencer_esperado
from recalculado
join snapshot
    on recalculado.fecha_corte = snapshot.fecha_corte
   and recalculado.id_sucursal = snapshot.id_sucursal
   and recalculado.id_producto = snapshot.id_producto
   and recalculado.lote = snapshot.lote
where snapshot.es_vencido_en_corte is distinct from recalculado.es_vencido_en_corte_esperado
   or snapshot.dias_para_vencer is distinct from recalculado.dias_para_vencer_esperado
