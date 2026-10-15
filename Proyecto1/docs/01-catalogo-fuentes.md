# Catálogo y perfil de fuentes de datos

## Procedencia

La solución utiliza la base transaccional `sgfood_oltp`, inicializada a partir de [`data/sgfood_oltp.sql`](../data/sgfood_oltp.sql), y cinco archivos CSV contenidos en [`data/`](../data/). El catálogo Excel y los fixtures opcionales presentes en el material académico son recursos de análisis, **no fuentes cargadas como tablas operativas** por el pipeline.

## Fuente PostgreSQL OLTP

| Tabla `oltp_sgfood` | Clave de negocio | Grano | Filas del conjunto validado | Tabla de destino |
|---|---|---|---:|---|
| `sucursal` | `id_sucursal` | Una sucursal | 6 | `raw.oltp_sucursal` |
| `categoria` | `id_categoria` | Una categoría | 8 | `raw.oltp_categoria` |
| `marca` | `id_marca` | Una marca | 10 | `raw.oltp_marca` |
| `producto` | `id_producto` (`sku` alterna) | Un producto | 80 | `raw.oltp_producto` |
| `cliente` | `id_cliente` | Un cliente | 250 | `raw.oltp_cliente` |
| `venta` | `id_venta` | Una cabecera | 1,200 | `raw.oltp_venta` |
| `venta_detalle` | `id_detalle` | Una línea de venta | 3,209 | `raw.oltp_venta_detalle` |
| **Total** | | | **4,763** | |

El modelo OLTP relaciona producto con categoría/marca, venta con cliente/sucursal y detalle con venta/producto. Las fechas de venta observadas van de `2026-01-01` a `2026-08-31`. Los conteos son una fotografía académica, no restricciones invariables del cargador.

## Fuentes CSV

| Archivo | Grano y clave natural | Filas validadas | Destino raw |
|---|---|---:|---|
| `inventario_bodega.csv` | Corte, sucursal, producto y lote | 3,840 | `csv_inventario_bodega` |
| `devoluciones.csv` | `id_devolucion` | 80 | `csv_devoluciones` |
| `metas_ventas.csv` | Periodo mensual y sucursal | 48 | `csv_metas_ventas` |
| `promociones.csv` | `id_promocion` | 30 | `csv_promociones` |
| `proveedores_precios.csv` | Proveedor, producto y vigencia | 103 | `csv_proveedores_precios` |
| **Total** | | **4,101** | |

En conjunto, las fuentes operativas contienen **8,864 registros de referencia** distribuidos en doce entidades; no constituyen una única tabla ni comparten un solo grano. El cargador preserva el contenido CSV como texto en raw y el tipado se aplica en staging. Las columnas completas se especifican en [el contrato de carga](05-carga-raw.md) y los [sources dbt](../dbt/models/sources.yml).

## Perfil y observaciones del conjunto académico

- **Inventario:** ocho cortes mensuales de enero a agosto de 2026, 480 registros por corte. Los 3,840 registros tenían vencimiento posterior a **su propia fecha de corte**. Un total de 658 fechas de vencimiento son anteriores a `2026-08-31`, pero ello no significa que esos lotes estuvieran vencidos en cortes anteriores.
- **Stock:** 265 registros presentan `stock_disponible > stock_maximo`. Es una observación, no un error comercial demostrado sin una regla adicional.
- **Ventas:** 48 líneas difieren de una fórmula de subtotal calculada con redondeo `ROUND_HALF_EVEN`; 59 con `ROUND_HALF_UP`. Se conserva el subtotal original como fuente de verdad registrada, sin forzar una política comercial de recálculo.
- **Promociones:** siete pares de vigencias se solapan dentro de una categoría. No se definió prioridad ni exclusividad entre promociones.
- **Proveedores:** el OLTP no incorpora una dimensión de proveedor; sus registros se conservan en `raw` y `staging`, sin dimensión, mart ni modelo `intermediate` específico de proveedores.
- **Devoluciones:** los vínculos a venta/producto no justifican mezclar devoluciones directamente con el hecho de ventas si ello cambia el grano.

## Controles implementados

El proceso de carga verifica formato y cabeceras CSV, codificación, claves naturales, contratos de destino y condiciones para evitar duplicados. Las tablas `raw` preservan metadatos como identificadores de carga, instantes y hashes de procedencia. Los tests dbt validan relaciones y claves; la reconciliación [`etl/integrity_reconciliation.py`](../etl/integrity_reconciliation.py) contrasta fuentes y resultados. Véanse [resultados de carga](../resultados/04-primera-carga-raw.txt), [pruebas de staging](../resultados/09-validacion-staging-independiente.txt) y [ejecuciones integrales](../resultados/37-airflow-3c3-primera-ejecucion.txt).

Los casos sintéticos de calidad, cuando estén presentes en material de apoyo, no forman parte de los doce conjuntos de datos operativos cargados por el pipeline.
