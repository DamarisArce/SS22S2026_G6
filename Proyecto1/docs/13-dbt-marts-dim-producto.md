# Bloque 2C4 — dimensión de productos

Estado: **IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (14 de octubre de 2026).

## Objetivo dimensional

`dim_producto` conserva en `marts` la información de productos disponible en
staging, sin historización artificial, enriquecimientos ni cambios de
semántica. Se materializa como una `VIEW` y no modifica los marts anteriores.

## Fuente, clave y grano

La única fuente es `{{ ref('stg_oltp_producto') }}`. El grano contractual es
una fila por `id_producto`, que es la clave natural y la clave primaria del
origen. `dbt/models/sources.yml` describe igualmente una fila por producto.
La unicidad está respaldada por el `PRIMARY KEY (id_producto)` del DDL y por
el contrato de staging.

## Columnas y tipos confirmados

La auditoría estática revisó `stg_oltp_producto.sql`,
`dbt/models/staging/schema.yml`, `sql/03-create-raw.sql` y
`etl/raw_loader.py`. El modelo conserva explícitamente estas columnas, todas
declaradas `NOT NULL` en el contrato OLTP:

| Columna | Tipo de origen | Significado |
|---|---|---|
| `id_producto` | `INTEGER` | Clave primaria natural |
| `sku` | `VARCHAR(20)` | SKU único |
| `nombre` | `VARCHAR(150)` | Nombre comercial de origen |
| `id_categoria` | `INTEGER` | Referencia a categoría |
| `id_marca` | `INTEGER` | Referencia a marca |
| `unidad_medida` | `VARCHAR(30)` | Unidad de medida |
| `costo_base` | `NUMERIC(12,2)` | Costo base reportado |
| `precio_lista` | `NUMERIC(12,2)` | Precio de lista reportado |
| `activo` | `BOOLEAN` | Estado de actividad de origen |
| `_etl_load_id` | `UUID` | Identificador técnico de carga |
| `_etl_loaded_at` | `TIMESTAMPTZ` | Instante técnico de carga |
| `_etl_source_table` | `TEXT` | Tabla OLTP de procedencia |
| `_etl_extracted_at` | `TIMESTAMPTZ` | Instante técnico de extracción |

No se observan columnas de producto opcionales o nulas en el DDL auditado.
El contrato de columnas, tipos, nulidad y unicidad también se contrastó
con PostgreSQL mediante consultas de solo lectura y pruebas dbt.

## Relaciones y ventas

`id_categoria` e `id_marca` son referencias `NOT NULL` confirmadas hacia
`stg_oltp_categoria.id_categoria` y `stg_oltp_marca.id_marca`, respectivamente.
El contrato de marts usa esas relaciones hacia staging y no depende de
dimensiones de categoría o marca aún inexistentes.

`fct_ventas_detalle.id_producto` referencia el producto staging. La relación
analítica validada es 1:N: un producto puede aparecer en muchas líneas de
venta. El test de integridad de ventas detecta claves de ventas sin producto
en la dimensión sin deduplicar ni multiplicar el hecho. Los productos sin
ventas permanecen en `dim_producto` porque el modelo no aplica filtros.

## Precios, estado e historia

`costo_base` y `precio_lista` son valores comerciales actuales disponibles en
el origen y se preservan sin cálculos. No representan necesariamente el costo
o el precio válido en la fecha de una venta, no se usan como costo vendido ni
para derivar rentabilidad.

`activo` es el estado registrado en el origen. El contrato no contiene fechas
de vigencia, versiones, indicador histórico ni reglas confiables para
reconstruir cambios. Por ello este bloque no implementa SCD2, no inventa
claves sustitutas y no presenta los valores actuales como atributos
históricos de las ventas.

## Tests creados

- `dim_producto_clave_unica.sql`: detecta duplicados de `id_producto`.
- `dim_producto_reconciliacion.sql`: compara dinámicamente filas y claves
  distintas entre staging y la dimensión.
- `dim_producto_integridad_origen.sql`: compara las 13 columnas seleccionadas
  con `EXCEPT ALL` en ambas direcciones, preservando multiplicidad y NULL.
- `dim_producto_integridad_ventas.sql`: detecta productos referenciados por el
  hecho que no existen en la dimensión.
- `tests/test_dbt_marts_product_contract.py`: valida estáticamente fuente,
  grano, materialización, columnas, relaciones, tests y preservación de los
  dos marts anteriores.

## Ejecución y validación real

Validación completada el **14 de octubre de 2026**.

### Entorno y materialización

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Rol ejecutor: `sgfood_dbt_runner`.
- Modelo: `marts.dim_producto`.
- Materialización: `VIEW`.
- Fuente única: `stg_oltp_producto`.
- Grano: una fila por `id_producto`.

### Pruebas ejecutadas

- `dbt parse`: aprobado.
- Modelos dbt declarados: 19.
- Tests dbt declarados: 167.
- `dbt run --select dim_producto`: PASS=1, ERROR=0.
- `dbt test --select dim_producto`: PASS=21, ERROR=0.
- Tests del producto: 17 genéricos y cuatro singulares.
- Suite Python: 82 pruebas aprobadas.
- Compilación Python y revisión estática: aprobadas.

Los 167 tests corresponden al proyecto completo.
Los 21 ejecutados en este bloque corresponden a
`dim_producto`; no se afirma que los 167 hayan
sido ejecutados juntos.

### Reconciliación independiente PostgreSQL

Ejecutada mediante una transacción
`REPEATABLE READ, READ ONLY`.

| Comprobación | Resultado |
|---|---:|
| Productos conservados | 80 |
| Identificadores `id_producto` únicos | 80 |
| SKU únicos | 80 |
| Columnas preservadas | 13 |
| Campos obligatorios con valores NULL | 0 |
| Diferencias `EXCEPT ALL` bidireccionales | 0 |
| Productos sin categoría o marca | 0 |
| Ventas sin producto correspondiente | 0 |
| Detalles de venta tras relacionar con productos | 3,209 |
| Cantidad registrada preservada | 19,174 |
| Subtotal registrado preservado | 838,452.07 |

También se verificó:

- Igualdad de tipos y orden de las 13 columnas.
- Conservación de `costo_base`, `precio_lista` y `activo`.
- Integridad referencial con categoría y marca.
- Ausencia de fanout al relacionar productos con catálogos.
- Relación 1:N entre productos y ventas sin multiplicación.
- Preservación de `fct_ventas_detalle` y `dim_sucursal`.
- Preservación de las cuatro vistas `intermediate`.
- Conservación de ventas mensuales, inventario y devoluciones.

Las cantidades corresponden al lote académico
validado; no son restricciones permanentes de dbt.

### Evidencias

- `resultados/28-dbt-marts-dim-producto-run.txt`.
- `resultados/29-dbt-marts-dim-producto-tests.txt`.
- `resultados/30-validacion-marts-dim-producto-independiente.txt`.

## Limitaciones y próximos pasos

`costo_base`, `precio_lista` y `activo` conservan
los valores disponibles en origen. No representan
necesariamente los valores vigentes en la fecha
histórica de cada venta.

No se implementa SCD2 sin evidencia confiable
de cambios históricos y fechas de vigencia.

Quedan pendientes otras dimensiones, hechos
analíticos, la orquestación y la validación integral
del pipeline ELT.
