# Bloque 2C2 — primer mart de ventas por detalle

Estado: **IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (13 de octubre de 2026).

## Objetivo

`fct_ventas_detalle` es el primer modelo de hechos de `marts`. Preserva el
detalle de ventas registrado y deja las reglas comerciales para fases
posteriores. El modelo se implementa como una vista en el schema `marts`.

## Requisitos académicos verificados

La lectura directa de `insumos/798_Proyecto_1_2S2026.pdf` confirmó:

- sección 3.2: Data Warehouse dimensional y modelos dbt en `staging`,
  `intermediate` y `marts`;
- sección 3.3: esquema dimensional con dimensiones, hechos, relaciones y
  materializaciones consistentes;
- sección 3.4: scripts de validación, consultas analíticas y documentación;
- metodología 4 y 5: construcción de modelos dbt y pruebas de calidad;
- rúbrica 9.4, criterio 2.1: sources, refs, materializaciones, dimensiones,
  hechos, relaciones y pruebas coherentes.

La matriz del proyecto refleja estos requisitos en R-03, R-04, R-05, R-06,
Q-04 y Q-05. El modelo específico `fct_ventas_detalle` es una decisión de
diseño compatible con ese requisito; el PDF no impone este nombre concreto.

## Fuente y grano

La única fuente conductora es:

```text
{{ ref('int_venta_detalle_enriquecida') }}
```

El grano es exactamente una fila por `id_detalle`. No se realizan joins,
agrupaciones, filtros ni deduplicaciones. El modelo no modifica los cuatro
modelos intermediate previamente validados.

## Columnas conservadas

Se conservan explícitamente:

- `id_detalle`
- `id_venta`
- `id_producto`
- `id_cliente`
- `id_sucursal`
- `fecha`
- `cantidad`
- `precio_unitario`
- `descuento`
- `subtotal`
- `_etl_load_id`
- `_etl_loaded_at`
- `_etl_source_table`
- `_etl_extracted_at`

Las claves de venta, producto, cliente y sucursal son claves naturales de
origen. Podrán relacionarse posteriormente con dimensiones marts separadas;
este bloque no crea claves sustitutas ni pretende constituir por sí solo un
esquema estrella completo.

## Semántica de medidas

- `cantidad`: medida original potencialmente aditiva según el contexto.
- `subtotal`: medida original potencialmente aditiva según reglas posteriores;
  no se recalcula ni se reemplaza.
- `precio_unitario`: medida no aditiva; no debe sumarse.
- `descuento`: valor original cuyo importe o proporción no se vuelve a
  interpretar en este modelo.

El hecho representa detalles de venta registrados. No representa
automáticamente ventas oficiales, ventas netas, ingresos contables,
recaudación, ganancias, márgenes ni descuentos atribuidos a promociones.

## Razón para no introducir joins

`int_venta_detalle_enriquecida` ya contiene las claves naturales necesarias y
las relaciones con venta y producto fueron verificadas en el contrato
intermediate. Agregar dimensiones en este modelo podría introducir cambios
de cardinalidad y mezclar responsabilidades. Las dimensiones marts se
incorporarán en bloques separados, con sus propios contratos.

## Tests incorporados

- `fct_ventas_detalle_clave_unica.sql`: detecta duplicaciones de `id_detalle`.
- `fct_ventas_detalle_reconciliacion.sql`: compara dinámicamente conteo,
  detalles distintos, cantidad y subtotal contra intermediate, usando
  comparaciones NULL-safe.
- `fct_ventas_detalle_integridad_origen.sql`: ejecuta `EXCEPT ALL` en ambas
  direcciones sobre todas las columnas seleccionadas, incluyendo medidas y
  metadatos técnicos.
- `tests/test_dbt_marts_sales_contract.py`: verifica estáticamente el modelo,
  el schema, las refs autorizadas y los tests singulares.

El contrato documenta relaciones naturales hacia los modelos staging de venta,
producto, cliente y sucursal. Esto no afirma todavía la existencia de un
esquema estrella completo en marts.

## Ejecución y validación real

Validación completada el **13 de octubre de 2026**.

### Entorno

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Rol de ejecución: `sgfood_dbt_runner`.
- Vista: `marts.fct_ventas_detalle`.
- Materialización: `VIEW`.

### Resultados de dbt

- `dbt parse`: aprobado.
- Modelos declarados: 17.
- Tests declarados: 133.
- `dbt run --select fct_ventas_detalle`: PASS=1, ERROR=0.
- `dbt test --select fct_ventas_detalle`: PASS=22, ERROR=0.
- Tests del mart: 19 genéricos y tres singulares.
- Pruebas Python: 66 aprobadas.

Los 133 tests corresponden al proyecto completo.
Los 22 tests ejecutados corresponden al primer mart;
la validación integral del proyecto continúa pendiente.

### Validación independiente PostgreSQL

Ejecutada mediante una transacción `REPEATABLE READ, READ ONLY`.

| Métrica | Resultado |
|---|---:|
| Registros de detalle | 3,209 |
| Identificadores únicos | 3,209 |
| Cantidad registrada | 19,174 |
| Subtotal original | 838,452.07 |
| Columnas preservadas | 14 |
| Diferencias bidireccionales | 0 |

También se verificó:

- Igualdad de tipos PostgreSQL entre origen y mart.
- Preservación exacta de claves, medidas y metadatos.
- `EXCEPT ALL` en ambas direcciones sin diferencias.
- Existencia de un único objeto en el schema `marts`.
- Cuatro vistas `intermediate` anteriores preservadas.
- Ventas mensuales, inventario y devoluciones sin alteraciones.

Los conteos y sumas anteriores describen el lote académico
validado; no constituyen restricciones permanentes del modelo.

### Evidencias

- `resultados/22-dbt-marts-ventas-detalle-run.txt`.
- `resultados/23-dbt-marts-ventas-detalle-tests.txt`.
- `resultados/24-validacion-marts-ventas-detalle-independiente.txt`.

El modelo conserva las medidas originales sin establecer reglas
de ventas oficiales, ventas netas, márgenes o ganancias.

## Limitaciones y siguiente paso

No se aplican reglas sobre estados, canales, devoluciones, promociones,
metas, costos ni rentabilidad. Tampoco se introducen surrogate keys ni SCD.
La construcción mediante dbt y la validación independiente en PostgreSQL
fueron completadas satisfactoriamente.

El siguiente bloque puede implementar dimensiones separadas, comenzando por
fecha, sucursal y producto, y definir entonces las relaciones dimensionales
sin alterar este hecho base.
