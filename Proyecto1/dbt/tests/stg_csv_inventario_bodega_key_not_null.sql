select fecha_corte, id_sucursal, id_producto, lote
from {{ ref('stg_csv_inventario_bodega') }}
where fecha_corte is null
   or id_sucursal is null
   or id_producto is null
   or lote is null
