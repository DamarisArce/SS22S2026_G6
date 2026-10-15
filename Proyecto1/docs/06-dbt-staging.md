# Capa `staging` — tipado y normalización dbt

## Función arquitectónica

La capa de staging expone **doce vistas** —una por cada tabla raw— que transforman la representación técnica de las fuentes en entidades consistentes para las capas posteriores. Son materializadas como `VIEW` por dbt y consultadas por modelos `intermediate` y `marts` a través de `ref()`.

## Inventario de modelos

| Origen | Vista staging |
|---|---|
| `raw.oltp_sucursal` | `stg_oltp_sucursal` |
| `raw.oltp_categoria` | `stg_oltp_categoria` |
| `raw.oltp_marca` | `stg_oltp_marca` |
| `raw.oltp_producto` | `stg_oltp_producto` |
| `raw.oltp_cliente` | `stg_oltp_cliente` |
| `raw.oltp_venta` | `stg_oltp_venta` |
| `raw.oltp_venta_detalle` | `stg_oltp_venta_detalle` |
| `raw.csv_inventario_bodega` | `stg_csv_inventario_bodega` |
| `raw.csv_devoluciones` | `stg_csv_devoluciones` |
| `raw.csv_metas_ventas` | `stg_csv_metas_ventas` |
| `raw.csv_promociones` | `stg_csv_promociones` |
| `raw.csv_proveedores_precios` | `stg_csv_proveedores_precios` |

Las definiciones viven en [`dbt/models/staging/`](../dbt/models/staging/), con contrato y pruebas en [`schema.yml`](../dbt/models/staging/schema.yml). Las doce fuentes están registradas en [`sources.yml`](../dbt/models/sources.yml). Las columnas técnicas preservan rastreabilidad del lote y archivo.

## Reglas de transformación

La normalización convierte fechas y valores numéricos de los CSV y mantiene los tipos adecuados en modelos OLTP. No debe confundirse el valor de `fecha_vencimiento` con una evaluación contra la fecha actual; los cálculos históricos se realizan en intermediate usando `fecha_corte`. Se preserva el `subtotal` de venta original. No se atribuyen promociones a líneas de venta ni se combinan devoluciones con el detalle de ventas.

El macro [`generate_schema_name.sql`](../dbt/macros/generate_schema_name.sql) garantiza la separación de `staging`, `intermediate` y `marts` sin prefijos redundantes. La conexión de dbt usa el rol `sgfood_dbt_runner` y el perfil configurable [`profiles.example.yml`](../dbt/profiles.example.yml).

## Calidad y resultados

Se verificaron conteos de raw y staging con igualdad para la muestra de **8,864 registros** y se aprobaron los tests declarados para la capa. La validación integral posterior confirmó la construcción simultánea de las tres capas: **21 modelos** y **201 pruebas** con resultado `PASS=222`, `WARN=0`, `ERROR=0`.

Evidencias: [construcción staging](../resultados/07-dbt-staging-run.txt), [pruebas](../resultados/08-dbt-staging-tests.txt), [reconciliación independiente](../resultados/09-validacion-staging-independiente.txt) y [DAG integral](../resultados/37-airflow-3c3-primera-ejecucion.txt).

## Alcance de los tests

Las verificaciones dbt cubren claves, nulabilidad, relaciones y reglas tipadas, además de pruebas singulares SQL ubicadas en [`dbt/tests/`](../dbt/tests/). Algunas fotografías de conteos exactos son opcionales y no se imponen como invariantes universales ante cambios legítimos de datos de entrada.
