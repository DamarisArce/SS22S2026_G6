# Bloque 2C3 — dimensión de sucursales

Estado: **IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (13 de octubre de 2026).

## Propósito analítico

`dim_sucursal` es la primera dimensión analítica implementada en `marts`.
Describe las sucursales disponibles en el origen para dar contexto geográfico
y operativo al hecho `fct_ventas_detalle`, sin alterar sus registros ni sus
medidas.

La revisión se realizó sobre los modelos dbt, el DDL de `raw`, el contrato del
cargador y la documentación académica existente. La matriz documentada en
`docs/00-matriz-requisitos.md` mantiene R-03, R-04, R-05 y R-06 como requisitos
generales del proyecto; este bloque implementa y valida una dimensión
analítica, sin afirmar la validación integral del pipeline ELT.

## Fuente, grano y clave

La fuente única es `{{ ref('stg_oltp_sucursal') }}`. El modelo se materializa
como `VIEW` en el schema `marts` y conserva exactamente una fila por
`id_sucursal`. La clave natural es `id_sucursal`; no se genera una clave
sustituta.

El contrato origen revisado en `sql/03-create-raw.sql` declara
`id_sucursal INTEGER NOT NULL` como clave primaria. `etl/raw_loader.py` confirma
los tipos y la nulidad de las ocho columnas. La entrada de `sources.yml`
describe una fila por sucursal. Estos contratos se contrastaron con PostgreSQL mediante pruebas dbt
y una validación independiente de solo lectura.

## Columnas y atributos confirmados

Se seleccionan explícitamente, sin joins, filtros, deduplicación ni cambios de
semántica:

- `id_sucursal`: clave natural.
- `nombre`: nombre de la sucursal.
- `ciudad`: ciudad de la sucursal.
- `departamento`: departamento de la sucursal.
- `_etl_load_id`, `_etl_loaded_at`, `_etl_source_table` y `_etl_extracted_at`:
  metadatos técnicos conservados desde staging.

El DDL de origen declara todas estas columnas `NOT NULL`. La nulidad del
contrato se refleja en el YAML de marts para los atributos seleccionados.

## Relación con ventas

`fct_ventas_detalle.id_sucursal` conserva la misma clave natural y su contrato
staging declara la relación con `stg_oltp_sucursal`. Por tanto, la relación
analítica esperada es 1:N: una sucursal puede contextualizar muchas líneas del
hecho. Esta relación se controla con
`dim_sucursal_integridad_ventas.sql`, que reporta únicamente claves de ventas
sin sucursal correspondiente y no usa `DISTINCT` para ocultar multiplicidad.

## Limitaciones históricas

La dimensión describe el estado disponible en el origen al momento de la
carga. No demuestra historia de sucursales: el contrato auditado no aporta
versiones, fechas de vigencia, indicador de registro actual ni una estrategia
de captura histórica confiable. Por ello no se infiere SCD1 ni SCD2 como regla
de negocio y no se crean filas históricas artificiales.

La decisión de no implementar SCD2 es deliberada: no existen en el contrato
revisado los atributos temporales necesarios para identificar cambios,
cerrar versiones y relacionar ventas históricas con la versión correcta.
Queda pendiente acordar una estrategia histórica y su evidencia antes de
incorporarla.

## Tests definidos

- `dim_sucursal_clave_unica.sql` detecta duplicaciones de `id_sucursal`.
- `dim_sucursal_reconciliacion.sql` compara dinámicamente filas y claves
  únicas entre staging y la dimensión.
- `dim_sucursal_integridad_origen.sql` compara las ocho columnas seleccionadas
  con `EXCEPT ALL` en ambas direcciones, incluyendo diferencias `NULL` y
  multiplicidad.
- `dim_sucursal_integridad_ventas.sql` detecta sucursales referenciadas por
  ventas que no existen en la dimensión mediante una relación explícita.
- `tests/test_dbt_marts_branch_contract.py` verifica estáticamente fuente,
  grano, materialización, selección explícita, tests, YAML y preservación del
  primer mart.

## Ejecución y validación real

Validación completada el **13 de octubre de 2026**.

### Entorno y materialización

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Rol de ejecución: `sgfood_dbt_runner`.
- Objeto: `marts.dim_sucursal`.
- Materialización: `VIEW`.
- Fuente única: `stg_oltp_sucursal`.

### Pruebas ejecutadas

- `dbt parse`: aprobado.
- Modelos dbt declarados: 18.
- Tests dbt declarados: 146.
- `dbt run --select dim_sucursal`: PASS=1, ERROR=0.
- `dbt test --select dim_sucursal`: PASS=13, ERROR=0.
- Tests de la dimensión: nueve genéricos y cuatro singulares.
- Suite Python: 74 pruebas aprobadas.
- `py_compile`: aprobado.
- Verificación Git y whitespace: aprobada.

Los 146 tests corresponden al proyecto completo; los 13 tests
ejecutados en esta fase corresponden únicamente a `dim_sucursal`.

### Validación independiente de PostgreSQL

Ejecutada con el rol `sgfood_dbt_runner`, utilizando una transacción
`REPEATABLE READ, READ ONLY`.

| Comprobación | Resultado |
|---|---:|
| Sucursales originales conservadas | 6 |
| Identificadores únicos | 6 |
| Columnas preservadas | 8 |
| Campos obligatorios con valores nulos | 0 |
| Diferencias `EXCEPT ALL` bidireccionales | 0 |
| Ventas sin sucursal correspondiente | 0 |
| Detalles conservados tras relacionar dimensión y hecho | 3,209 |
| Cantidad registrada conservada | 19,174 |
| Subtotal registrado conservado | 838,452.07 |

Se verificaron además los tipos PostgreSQL de las ocho columnas,
la ausencia de multiplicación de detalles de venta mediante `JOIN`,
los propietarios de las vistas y la preservación de los cuatro modelos
`intermediate` y del primer mart de ventas.

También se comprobaron las métricas previamente validadas de ventas
mensuales, inventario histórico y devoluciones.

Estos valores describen el lote académico utilizado y no son
restricciones permanentes de la dimensión.

### Evidencias

- `resultados/25-dbt-marts-dim-sucursal-run.txt`.
- `resultados/26-dbt-marts-dim-sucursal-tests.txt`.
- `resultados/27-validacion-marts-dim-sucursal-independiente.txt`.

### Limitaciones pendientes

La dimensión representa el estado disponible en el origen.
No existe evidencia suficiente para implementar historización SCD2.

La validación integral del pipeline ELT y la orquestación continúan
pendientes; completar esta dimensión no equivale a cerrar el proyecto.

## Próximas dimensiones recomendadas

Como siguientes candidatos quedan `dim_producto`, `dim_cliente` y
`dim_fecha`, cada uno con su propio contrato de fuente, grano, relaciones y
decisión histórica. También debe definirse explícitamente si cliente y
producto requieren historial antes de implementar SCD.
