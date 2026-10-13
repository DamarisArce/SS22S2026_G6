# Bloque 2A — Carga Python al schema `raw`

Estado al 13 de octubre de 2026: **COMPROBADO mediante ejecuciones reales**.
La carga Python al schema `raw`, su idempotencia y su política transaccional
fueron validadas con PostgreSQL el 13/10/2026. Esta comprobación corresponde
exclusivamente al ETL Python raw; dbt/modelos analíticos, Apache Airflow y las
pruebas del flujo ELT completo permanecen **PENDIENTES**.

## Arquitectura

`etl/raw_loader.py` lee los cinco CSV desde `data/`, extrae las siete tablas
del schema `oltp_sgfood` con `sgfood_oltp_reader` y escribe exclusivamente las
doce tablas administradas bajo `raw` usando `sgfood_raw_loader`. El script
`sql/03-create-raw.sql` se ejecuta por el mismo loader dentro de la transacción
de escritura; no se requiere una conexión administrativa.

La extracción OLTP usa una transacción `REPEATABLE READ, READ ONLY`, valida
`current_database()`/`current_user` y usa proyecciones explícitas. La carga DW
valida la misma identidad antes de escribir, ejecuta DDL `CREATE TABLE IF NOT
EXISTS`, comprueba catálogo, tipos, nulabilidad, propiedad, relkind y columnas
adicionales antes de `TRUNCATE`, y usa listas explícitas de columnas. El DDL,
el truncado, los `executemany()` y la reconciliación de las doce tablas se
confirman juntos o se revierten juntos.

## Contrato exacto de fuentes y destinos

Las columnas originales mantienen nombre y orden. Las columnas `_etl_*` son
metadatos técnicos adicionales y no reemplazan ningún valor de origen.

| Fuente | Destino | Columnas originales | Tipos raw | Clave natural |
|---|---|---|---|---|
| `oltp_sgfood.sucursal` | `raw.oltp_sucursal` | `id_sucursal`, `nombre`, `ciudad`, `departamento` | `INTEGER`, `VARCHAR(100)`, `VARCHAR(100)`, `VARCHAR(100)` | `id_sucursal` |
| `oltp_sgfood.categoria` | `raw.oltp_categoria` | `id_categoria`, `nombre` | `INTEGER`, `VARCHAR(100)` | `id_categoria` |
| `oltp_sgfood.marca` | `raw.oltp_marca` | `id_marca`, `nombre` | `INTEGER`, `VARCHAR(100)` | `id_marca` |
| `oltp_sgfood.producto` | `raw.oltp_producto` | `id_producto`, `sku`, `nombre`, `id_categoria`, `id_marca`, `unidad_medida`, `costo_base`, `precio_lista`, `activo` | Tipos PostgreSQL originales | `id_producto`; `sku` alterna |
| `oltp_sgfood.cliente` | `raw.oltp_cliente` | `id_cliente`, `nit`, `nombre`, `tipo_cliente`, `municipio`, `departamento`, `fecha_alta` | Tipos PostgreSQL originales | `id_cliente` |
| `oltp_sgfood.venta` | `raw.oltp_venta` | `id_venta`, `fecha`, `id_cliente`, `id_sucursal`, `canal`, `metodo_pago`, `estado` | Tipos PostgreSQL originales | `id_venta` |
| `oltp_sgfood.venta_detalle` | `raw.oltp_venta_detalle` | `id_detalle`, `id_venta`, `id_producto`, `cantidad`, `precio_unitario`, `descuento`, `subtotal` | Tipos PostgreSQL originales | `id_detalle` |
| `inventario_bodega.csv` | `raw.csv_inventario_bodega` | `fecha_corte`, `id_sucursal`, `id_producto`, `stock_disponible`, `stock_minimo`, `stock_maximo`, `lote`, `fecha_vencimiento` | `TEXT` | `fecha_corte`, `id_sucursal`, `id_producto`, `lote` |
| `devoluciones.csv` | `raw.csv_devoluciones` | `id_devolucion`, `fecha`, `id_venta`, `id_producto`, `cantidad`, `motivo` | `TEXT` | `id_devolucion` |
| `metas_ventas.csv` | `raw.csv_metas_ventas` | `periodo`, `id_sucursal`, `meta_ventas`, `meta_unidades` | `TEXT` | `periodo`, `id_sucursal` |
| `promociones.csv` | `raw.csv_promociones` | `id_promocion`, `nombre`, `fecha_inicio`, `fecha_fin`, `id_categoria`, `porcentaje_descuento` | `TEXT` | `id_promocion` |
| `proveedores_precios.csv` | `raw.csv_proveedores_precios` | `id_proveedor`, `proveedor`, `id_producto`, `costo_proveedor`, `plazo_dias`, `fecha_vigencia` | `TEXT` | `id_proveedor`, `id_producto`, `fecha_vigencia` |

En CSV, una celda vacía se conserva como `''`; no se convierte a `NULL`, fecha,
número ni regla de negocio. Se valida estrictamente el encabezado, el número
de campos, las claves naturales y el formato; se lee con `io.StringIO(...,
newline='')`, `csv.reader(strict=True)` y `utf-8-sig`, preservando CRLF dentro
de campos entrecomillados. Toda anomalía produce `RawLoadError` sin detalles
sensibles. Se calcula SHA-256 sobre los bytes originales. Los archivos fuera de
las cinco fuentes declaradas quedan fuera de la carga operativa.

## Idempotencia, atomicidad y trazabilidad

Cada ejecución genera un UUID `_etl_load_id` y registra fecha/hora UTC. OLTP
registra tabla fuente y momento de extracción; CSV registra nombre, SHA-256 y
número de fila original (iniciando en 2 por el encabezado). La estrategia de
reemplazo es `TRUNCATE` acotado a las doce tablas y reinserción completa dentro
de una sola transacción DW. Por ello una segunda carga idéntica no duplica filas
y un fallo hace rollback de DDL/datos de la carga en curso. No se usa `DROP`,
`CASCADE` ni se borran objetos ajenos.

Los duplicados de claves naturales CSV se rechazan antes de abrir la
transacción de escritura. Las restricciones `PRIMARY KEY`/`UNIQUE` del DDL
también protegen las claves declaradas. Después de insertar, el cargador
consulta `COUNT(*)` por destino y compara cada resultado con las filas
extraídas; una diferencia provoca rollback antes del commit. Registra por
fuente el conteo real y el UUID de carga, sin secretos. Los conteos del dataset
académico, si se proporcionan como expectativa, solo generan advertencias y no
bloquean futuras cargas.

## Configuración y comando propuesto

La CLI lee `Proyecto1/.env` sin sobrescribir variables ya exportadas y exige
los hosts/puertos/bases `POSTGRES_OLTP_*` y `POSTGRES_DW_*`, además de
`SGFOOD_OLTP_READER_PASSWORD` y `SGFOOD_RAW_LOADER_PASSWORD`. Los nombres de
usuario están fijados en código a `sgfood_oltp_reader` y `sgfood_raw_loader`;
esto impide que la carga use administradores por configuración accidental.
Nunca recibe contraseñas por argumento ni las imprime. La carga se ejecuta
desde la raíz así:

```bash
python3 -m etl.raw_loader --source-dir data --env-file .env
```

Se debe ejecutar con los roles separados ya documentados. No debe ejecutarse
con usuarios administradores.

## Evidencia de ejecuciones reales

La primera carga real del 13/10/2026 insertó y reconcilió las doce fuentes:

- Las siete tablas PostgreSQL OLTP aportaron 4763 registros.
- Los cinco CSV aportaron 4101 registros.
- El total fue de 12 tablas raw y 8864 registros.
- La reconciliación se realizó mediante `sgfood_dbt_runner`.
- Load ID: `3c3c5e10-3f55-4511-be32-8404ddd34b09`.

Evidencia: [resultados/04-primera-carga-raw.txt](../resultados/04-primera-carga-raw.txt).

La segunda carga real, también del 13/10/2026, confirmó que los conteos de
las doce tablas no cambiaron y que las huellas de los datos de negocio
coincidieron. Se generó un nuevo identificador de carga, por lo que quedó
comprobada la idempotencia para fuentes sin cambios; los metadatos de carga
se renovaron normalmente.

- Load ID: `dac2fed3-7a33-42e1-a7a6-f5de7b66ff6c`.
- Total posterior: 8864 registros.

Evidencia: [resultados/05-segunda-carga-raw.txt](../resultados/05-segunda-carga-raw.txt).

La prueba de rollback real insertó las doce fuentes dentro de una transacción
DW, provocó un fallo después de las inserciones y antes del `COMMIT`, y capturó
el error. Una conexión independiente verificó que datos y metadatos
permanecieron idénticos al estado previo; se conservaron 8864 registros. El
resultado fue **VALIDACIÓN DE ROLLBACK REAL APROBADA**.

Evidencia: [resultados/06-prueba-rollback-raw.txt](../resultados/06-prueba-rollback-raw.txt).

## Pruebas y plan posterior

**Pruebas unitarias simuladas:** con mocks/fakes se cubren BOM, CRLF, vacíos,
campos multilínea preservados exactamente, CSV mal formado, encabezado inválido,
claves duplicadas, columnas explícitas, contrato raw incompatible, propietario
incorrecto, aislamiento de las doce tablas, reconciliación antes del commit,
rollback DW y cierre de la primera conexión si falla la segunda. No usan
conexiones reales.

**Validación de datos locales:** el loader calcula SHA-256 de los bytes fuente,
mantiene los valores de negocio como texto en CSV y conserva los conteos reales
extraídos.

**Pruebas unitarias:** las 15 pruebas de `tests/test_raw_loader.py` pasaron
usando Psycopg 3.3.6.

**Estado del alcance:** el ETL Python raw está validado con las ejecuciones
reales y evidencias enlazadas arriba. **PENDIENTE:** dbt y los modelos
analíticos; Apache Airflow; y las pruebas del flujo ELT completo.

## Riesgos y limitaciones

- La atomicidad es completa para la escritura DW, pero la lectura OLTP y la
  escritura DW pertenecen a bases PostgreSQL distintas; no existe una
  transacción distribuida entre ambas.
- Los CSV se mantienen como texto en raw. Tipado, normalización y reglas de
  vencimiento, montos, devoluciones o promociones pertenecen a staging y
  requieren decisiones de negocio posteriores.
- El cargador presupone que las tablas existentes, si las hubiera, coinciden
  con el contrato. Una incompatibilidad debe fallar y hacer rollback; no se
  corrige silenciosamente.
- La atomicidad validada corresponde a la escritura DW del ETL Python; no
  constituye una transacción distribuida entre la lectura OLTP y la escritura
  DW.
- La validación de este documento no implica que dbt, los modelos analíticos,
  Airflow o el flujo ELT completo estén terminados.
