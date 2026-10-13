# Catálogo inicial de fuentes SG-Food

Estado: **revisión estática verificada; carga aún PENDIENTE**. Los conteos se obtuvieron leyendo directamente `sgfood_oltp.sql` y los CSV dentro de `insumos/Data-20260930.zip`; no se ejecutó el SQL ni se cargó una base de datos.

## Mapa de procedencia

| Fuente | Procedencia | Papel propuesto | Filas verificadas |
|---|---|---|---:|
| `catalogo_insumos_sgfood.xlsx` | Catálogo de apoyo incluido en el ZIP | Diccionario/resumen de fuentes; no es una fuente operativa adicional | 2 hojas (`Resumen`, `Diccionario`); no aplica |
| `sgfood_oltp.sql` | Sistema OLTP sintético PostgreSQL, schema `oltp_sgfood` | Fuente transaccional para dimensiones de sucursal, categoría, marca, producto, cliente y hechos de venta | 4,763 en 7 tablas |
| `inventario_bodega.csv` | Archivo delimitado | Hecho/snapshot de inventario | 3,840 |
| `devoluciones.csv` | Archivo delimitado | Hecho de devoluciones, sujeto a decisión de negocio | 80 |
| `metas_ventas.csv` | Archivo delimitado | Hecho o presupuesto mensual | 48 |
| `promociones.csv` | Archivo delimitado | Dimensión/evento de promoción, sujeto a decisión de relación con ventas | 30 |
| `proveedores_precios.csv` | Archivo delimitado | Histórico de precios/proveedores | 103 |
| `casos_calidad_opcionales.csv` | Archivo delimitado de casos sintéticos | Fixtures de pruebas de calidad; no son operación | 10 |

El total OLTP es la suma de filas de sus tablas, no una entidad única. Los CSV no se deben sumar como si fueran una sola tabla.

## Tablas OLTP

El SQL declara `DROP SCHEMA IF EXISTS oltp_sgfood CASCADE`; por seguridad, esa sentencia no se ejecutó y no forma parte de la carga autorizada de esta fase.

| Tabla | Columnas | Clave | Granularidad | Filas |
|---|---|---|---|---:|
| `sucursal` | `id_sucursal`, `nombre`, `ciudad`, `departamento` | `id_sucursal` | Una sucursal | 6 |
| `categoria` | `id_categoria`, `nombre` | `id_categoria` | Una categoría | 8 |
| `marca` | `id_marca`, `nombre` | `id_marca` | Una marca | 10 |
| `producto` | `id_producto`, `sku`, `nombre`, `id_categoria`, `id_marca`, `unidad_medida`, `costo_base`, `precio_lista`, `activo` | `id_producto`; `sku` único | Un producto | 80 |
| `cliente` | `id_cliente`, `nit`, `nombre`, `tipo_cliente`, `municipio`, `departamento`, `fecha_alta` | `id_cliente` | Un cliente | 250 |
| `venta` | `id_venta`, `fecha`, `id_cliente`, `id_sucursal`, `canal`, `metodo_pago`, `estado` | `id_venta` | Una cabecera de venta | 1,200 |
| `venta_detalle` | `id_detalle`, `id_venta`, `id_producto`, `cantidad`, `precio_unitario`, `descuento`, `subtotal` | `id_detalle`; FK a venta/producto | Un producto dentro de una venta | 3,209 |

Las FKs declaradas son producto→categoría/marca, venta→cliente/sucursal y detalle→venta/producto. El SQL declara controles de no negatividad para costos, precios, cantidades, descuentos y subtotales. Las fechas de venta verificadas abarcan `2026-01-01` a `2026-08-31`.

## Archivos delimitados

| Archivo | Columnas | Clave/granularidad propuesta | Observaciones verificadas |
|---|---|---|---|
| `inventario_bodega.csv` | `fecha_corte`, `id_sucursal`, `id_producto`, `stock_disponible`, `stock_minimo`, `stock_maximo`, `lote`, `fecha_vencimiento` | (`fecha_corte`, `id_sucursal`, `id_producto`, `lote`); una existencia por lote/producto/sucursal/corte | 8 cortes mensuales, 480 filas por corte; 0 duplicados en la clave compuesta; todas las FKs de producto/sucursal coinciden |
| `devoluciones.csv` | `id_devolucion`, `fecha`, `id_venta`, `id_producto`, `cantidad`, `motivo` | `id_devolucion`; una devolución de producto asociada a venta | 0 duplicados de clave; `id_venta` e `id_producto` coinciden con OLTP |
| `metas_ventas.csv` | `periodo`, `id_sucursal`, `meta_ventas`, `meta_unidades` | (`periodo`, `id_sucursal`); una meta mensual por sucursal | 8 periodos × 6 sucursales; sin duplicados de clave |
| `promociones.csv` | `id_promocion`, `nombre`, `fecha_inicio`, `fecha_fin`, `id_categoria`, `porcentaje_descuento` | `id_promocion`; una promoción por categoría y vigencia | 0 duplicados de clave; categorías coinciden con OLTP |
| `proveedores_precios.csv` | `id_proveedor`, `proveedor`, `id_producto`, `costo_proveedor`, `plazo_dias`, `fecha_vigencia` | (`id_proveedor`, `id_producto`, `fecha_vigencia`); un precio vigente reportado | 0 duplicados en la clave propuesta; productos coinciden con OLTP; no existe dimensión de proveedor en el SQL |
| `casos_calidad_opcionales.csv` | `entidad`, `campo`, `valor_prueba`, `tipo_incidencia` | Caso de prueba, no clave operativa | 10 casos, incluidos 2 valores vacíos; contiene `cliente.id_cliente` nulo y `producto.precio_lista` negativo como fixtures |

## Hallazgo de vencimientos

Se corrigió expresamente la interpretación del inventario: **658 filas históricas tienen `fecha_vencimiento` anterior al 2026-08-31**. Eso no significa que estén vencidas en su corte. La verificación directa mostró:

- 8 cortes: del 2026-01-31 al 2026-08-31.
- 480 filas en el corte 2026-08-31.
- 0 filas con `fecha_vencimiento < fecha_corte` en todos los cortes, incluido su propio corte.
- Por tanto, hay **0 registros vencidos en el corte del 2026-08-31** y **0 vencidos en su propio corte**.

La regla futura debe comparar vencimiento contra `fecha_corte`, no contra la fecha máxima del archivo ni contra la fecha de ejecución. Los 658 casos deben conservarse como historia válida, sujetos a una prueba explícita que evite etiquetarlos erróneamente como vencidos.

## Otros hallazgos estáticos

Los siguientes resultados son observaciones de consistencia obtenidas sobre las fuentes. Son anomalías observadas, no errores de negocio confirmados; su tratamiento requiere reglas comerciales o validaciones de calidad aprobadas.

- **Inventario:** 265 registros tienen `stock_disponible > stock_maximo`. El hallazgo no determina por sí solo si el dato es inválido, si existe una excepción operativa o si el límite requiere interpretación.
- **Ventas:** 48 de 3,209 líneas presentan diferencia entre `subtotal` y la fórmula calculada usando `ROUND_HALF_EVEN` a dos decimales; 59 de 3,209 presentan diferencia usando `ROUND_HALF_UP` a dos decimales. Son discrepancias observadas bajo dos reglas de redondeo; no se debe sobrescribir el subtotal de origen ni declarar el cálculo como error confirmado sin definir la regla comercial.
- **Promociones:** existen 7 pares de promociones de una misma categoría cuyas vigencias se solapan. El solapamiento observado no confirma que las promociones sean incompatibles, porque el enunciado no define exclusividad ni prioridad comercial.

## Anomalías, riesgos y controles pendientes

- Los CSV no declaran tipos ni claves; el contrato de carga debe fijar fechas, numéricos, dominios y codificación UTF-8.
- `proveedores_precios.csv` introduce proveedor fuera del OLTP; falta decidir si se crea una dimensión de proveedor o si queda como atributo de la fuente.
- No hay vínculo explícito entre promociones y líneas de venta; no atribuir descuentos a ventas sin una regla de negocio aprobada.
- No hay vínculo explícito entre devoluciones y detalle de venta más allá de (`id_venta`, `id_producto`); validar multiplicidad antes de unirlas a hechos.
- `casos_calidad_opcionales.csv` debe cargarse como fixture de pruebas o mantenerse fuera de los hechos; no presentar sus 10 filas como operación normal.
- Verificaciones de rangos, signos, fechas solapadas, duplicados semánticos y reconciliación monetaria siguen PENDIENTES de ejecución en PostgreSQL/dbt.
