# Extracción y carga de datos en `raw`

## Propósito y componentes

[`etl/raw_loader.py`](../etl/raw_loader.py) ejecuta la etapa **Extract–Load** del pipeline: obtiene siete tablas de `oltp_sgfood`, lee cinco archivos CSV y escribe doce tablas físicas del esquema `sgfood_dw.raw`. Usa el usuario de lectura OLTP para extraer y el rol de carga raw para persistir los datos. La estructura de destino se establece en [`sql/03-create-raw.sql`](../sql/03-create-raw.sql).

## Mapa de fuentes y destinos

| Origen | Destino | Clave o grano |
|---|---|---|
| `oltp_sgfood.sucursal` | `raw.oltp_sucursal` | `id_sucursal` |
| `oltp_sgfood.categoria` | `raw.oltp_categoria` | `id_categoria` |
| `oltp_sgfood.marca` | `raw.oltp_marca` | `id_marca` |
| `oltp_sgfood.producto` | `raw.oltp_producto` | `id_producto` |
| `oltp_sgfood.cliente` | `raw.oltp_cliente` | `id_cliente` |
| `oltp_sgfood.venta` | `raw.oltp_venta` | `id_venta` |
| `oltp_sgfood.venta_detalle` | `raw.oltp_venta_detalle` | `id_detalle` |
| `inventario_bodega.csv` | `raw.csv_inventario_bodega` | Corte, sucursal, producto y lote |
| `devoluciones.csv` | `raw.csv_devoluciones` | `id_devolucion` |
| `metas_ventas.csv` | `raw.csv_metas_ventas` | Periodo y sucursal |
| `promociones.csv` | `raw.csv_promociones` | `id_promocion` |
| `proveedores_precios.csv` | `raw.csv_proveedores_precios` | Proveedor, producto y vigencia |

Los datos OLTP conservan sus tipos de origen y los CSV ingresan como texto para normalización posterior. La capa raw contiene además metadatos técnicos de carga y procedencia, incluidos identificadores, instantes y hashes o nombres de archivo según la fuente. La definición de claves, columnas y tipos se encuentra en el DDL y en [`dbt/models/sources.yml`](../dbt/models/sources.yml).

## Controles de integridad

El loader valida condiciones de conexión, existencia de las doce estructuras esperadas, formato UTF-8, cabeceras y campos CSV y unicidad de las claves de origen. La escritura raw se realiza mediante transacciones: ante un error posterior a inserciones parciales, se aplica **rollback** para no dejar una carga incompleta. El procedimiento conserva trazabilidad de lote y recuentos para posteriores reconciliaciones.

La idempotencia se comprueba mediante reejecuciones y comparación de fotografías del conjunto de datos; no implica que cualquier modificación futura de las fuentes sea ignorada. Los conteos de referencia de la muestra fueron **4,763 registros OLTP y 4,101 CSV**, distribuidos en doce tablas. Véanse [catálogo](01-catalogo-fuentes.md) y [evidencia de idempotencia](../resultados/39-airflow-3c3-idempotencia.txt).

## Ejecución

El DAG invoca el cargador como segunda tarea, después de `precheck_config`. También puede ejecutarse directamente con roles aprovisionados y servicios activos:

```bash
python etl/raw_loader.py --source-dir data --env-file .env
```

Este comando es una **alternativa de mantenimiento**; la validación integral está respaldada por ejecuciones del DAG, no por una repetición reciente de cada comando individual del manual.

## Evidencias

- [Primera carga raw](../resultados/04-primera-carga-raw.txt).
- [Segunda carga](../resultados/05-segunda-carga-raw.txt).
- [Prueba de rollback](../resultados/06-prueba-rollback-raw.txt).
- [Ejecuciones integrales Airflow 37 y 38](../resultados/37-airflow-3c3-primera-ejecucion.txt).
- [Pruebas unitarias del loader](../tests/test_raw_loader.py).

La carga raw no aplica atribuciones de promoción, ajustes comerciales a subtotales ni cambios de grano; esas transformaciones deben justificarse explícitamente antes de incorporarse.
