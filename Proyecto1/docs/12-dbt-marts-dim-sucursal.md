# Dimensión de sucursales — `marts.dim_sucursal`

## Definición y grano

[`dim_sucursal`](../dbt/models/marts/dim_sucursal.sql) expone **una fila por `id_sucursal`** desde `stg_oltp_sucursal`, materializada como vista en `marts`. Conserva la identidad, el nombre y la localización de cada sucursal: `id_sucursal`, `nombre`, `ciudad`, `departamento`, más `_etl_load_id`, `_etl_loaded_at`, `_etl_source_table` y `_etl_extracted_at`.

## Relación con el hecho

La dimensión se relaciona de manera lógica por `dim_sucursal.id_sucursal = fct_ventas_detalle.id_sucursal`. No constituye una FK física sobre la vista. Se valida que las referencias de ventas estén cubiertas y que el join mantenga el grano y las medidas del hecho.

## Controles de calidad

En el conjunto académico se preservaron **6 sucursales**, **6 claves únicas**, 8 columnas y cero diferencias frente al origen staging. No se encontraron ventas sin sucursal ni fanout; los **3,209 detalles**, **19,174 unidades** y **838,452.07** de subtotal permanecieron estables.

Evidencias: [run 25](../resultados/25-dbt-marts-dim-sucursal-run.txt), [tests 26](../resultados/26-dbt-marts-dim-sucursal-tests.txt), [validación 27](../resultados/27-validacion-marts-dim-sucursal-independiente.txt).

## Límite histórico

La dimensión refleja los atributos disponibles en el origen y conserva metadatos de carga. No se implementó un historial tipo SCD2 de cambios de nombre, ciudad o departamento, porque las fuentes no proporcionan un contrato histórico suficiente.
