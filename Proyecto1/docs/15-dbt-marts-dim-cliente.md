# `marts.dim_cliente`

## Estado

**IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (14 de octubre de 2026).

La vista `marts.dim_cliente` fue construida mediante dbt, superó los
13 tests propios y se reconcilió independientemente contra staging
mediante una transacción PostgreSQL `REPEATABLE READ, READ ONLY`.

## Objetivo, grano y fuente

`dim_cliente` representa el estado de cliente disponible en el lote de origen,
con una fila por `id_cliente`. La clave natural es `id_cliente`; no se añade
una clave sustituta. La única fuente autorizada es
`ref('stg_oltp_cliente')`, proyectada sin joins, filtros, deduplicación ni
transformaciones. La materialización es `VIEW` en el esquema `marts`.

## Columnas y tipos

| Columna | Tipo | Nulabilidad y semántica |
| --- | --- | --- |
| `id_cliente` | `INTEGER` | No nulo; clave natural. |
| `nit` | `VARCHAR(20)` | No nulo; identificador tributario de origen. |
| `nombre` | `VARCHAR(150)` | No nulo; nombre de origen. |
| `tipo_cliente` | `VARCHAR(40)` | No nulo; clasificación de origen. |
| `municipio` | `VARCHAR(100)` | Puede ser `NULL`. |
| `departamento` | `VARCHAR(100)` | Puede ser `NULL`. |
| `fecha_alta` | `DATE` | No nulo; exclusivamente fecha de alta del cliente. |
| `_etl_load_id` | `UUID` | No nulo; metadato técnico de carga. |
| `_etl_loaded_at` | `TIMESTAMPTZ` | No nulo; instante técnico de carga. |
| `_etl_source_table` | `TEXT` | No nulo; tabla técnica de procedencia. |
| `_etl_extracted_at` | `TIMESTAMPTZ` | No nulo; instante técnico de extracción. |

El staging existente conserva estas columnas mediante una proyección directa
desde `raw.oltp_cliente`; los tipos proceden del DDL raw autorizado y no se
redeclaran ni alteran en el mart.

## Relaciones y límites históricos

La dimensión se relaciona 1:N con `fct_ventas_detalle` mediante
`id_cliente`. Todos los clientes permanecen incluidos aunque no tengan
cabeceras de venta. Esto no debe confundirse con clientes que tengan cabecera
pero carezcan de detalles en el hecho analítico.

`fecha_alta` no es fecha de compra, primera compra, última compra ni fecha de
vigencia. El contrato describe el estado disponible, no un historial de
cambios de atributos. No se usa SCD2 porque no existen en este contrato
fechas de vigencia, versiones, cierres ni una fuente histórica confiable; crear
esas columnas produciría historia inventada.

No se impone `unique` sobre `nit`: el contrato solo garantiza la clave natural
`id_cliente`, no la unicidad de ese identificador tributario.

## Datos sintéticos y privacidad

El lote académico contiene datos sintéticos. La inspección inicial del SQL
académico y la validación posterior en PostgreSQL confirmaron 250 clientes,
249 clientes referenciados por cabeceras de venta, un cliente sin ventas
y cero referencias a clientes inexistentes.

Aunque el lote sea sintético, `nit`, `nombre`, `municipio` y `departamento`
representan categorías de datos cuya exposición debe limitarse. Una evolución
posterior debe evaluar controles de acceso y vistas anonimizadas antes de
publicar estos atributos a consumidores amplios.

## Pruebas y validaciones ejecutadas

**Fecha de validación:** 14 de octubre de 2026.

### Entorno y manifiesto dbt

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Esquema: `marts`.
- Modelo: `dim_cliente`.
- Materialización: `VIEW`.
- Rol de ejecución: `sgfood_dbt_runner`.
- Fuente única: `stg_oltp_cliente`.
- Modelos declarados en el proyecto: 21.
- Fuentes declaradas: 12.
- Tests declarados en el proyecto: 201.

### Construcción y tests

- `dbt parse --no-partial-parse`: aprobado.
- `dbt run --select dim_cliente`: PASS=1, ERROR=0.
- `dbt test --select dim_cliente`: PASS=13, ERROR=0.
- Tests genéricos: nueve `not_null` y un `unique`.
- Tests singulares: tres.

Los tests singulares comprueban:

1. Integridad de las once columnas mediante `EXCEPT ALL` bidireccional.
2. Integridad con ventas y ausencia de fanout.
3. Conservación dinámica de clientes sin cabeceras de venta.

La suite Python estática completa aprobó 100 pruebas.

Los 201 tests corresponden al inventario declarado del proyecto.
No se afirma que todos hayan sido ejecutados juntos.

### Reconciliación PostgreSQL independiente

Se utilizó una transacción `REPEATABLE READ, READ ONLY`
con el rol `sgfood_dbt_runner`.

| Control | Resultado |
| --- | ---: |
| Clientes en `dim_cliente` | 250 |
| Claves `id_cliente` únicas | 250 |
| Columnas con tipos correctos | 11 |
| Columnas obligatorias sin valores NULL | 9 |
| Diferencias bidireccionales con staging | 0 |
| Cabeceras de venta | 1,200 |
| Clientes referenciados en ventas | 249 |
| Clientes sin cabeceras de venta | 1 |
| Referencias a clientes inexistentes | 0 |
| Detalles de venta preservados | 3,209 |
| Cantidad registrada preservada | 19,174 |
| Subtotal registrado preservado | 838,452.07 |
| Fanout de la relación cliente-ventas | 0 |

La comparación bidireccional verificó las once columnas,
incluidos los valores NULL permitidos de `municipio` y
`departamento` y los cuatro metadatos ETL.

Se preservaron las dimensiones `dim_sucursal`, `dim_producto`
y `dim_fecha`, el hecho `fct_ventas_detalle` y las cuatro
vistas `intermediate` anteriores.

Los conteos pertenecen al lote académico validado.
No son reglas permanentes de cardinalidad.

El subtotal registrado no se interpreta como ingreso neto
oficial, margen ni utilidad.

### Evidencias

- `resultados/34-dbt-marts-dim-cliente-run.txt`.
- `resultados/35-dbt-marts-dim-cliente-tests.txt`.
- `resultados/36-validacion-marts-dim-cliente-independiente.txt`.

Las evidencias registran métricas y estados de validación,
sin publicar NIT ni nombres de clientes.

## Limitaciones y próximos pasos

`dim_cliente` conserva el estado disponible del cliente.
No reconstruye versiones históricas ni implementa SCD2.

No se declara unicidad de `nit` porque el contrato OLTP
no establece dicha restricción.

La presencia de atributos personales en la dimensión no
equivale a una autorización de acceso para consumidores
analíticos generales. Deben evaluarse controles de acceso,
minimización y posibles vistas anonimizadas antes de
utilizar datos reales.

Continúan pendientes los demás componentes analíticos,
la orquestación y la validación integral del pipeline ELT.
