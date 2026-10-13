# Arquitectura propuesta y decisiones iniciales

Estado: **propuesta para la siguiente fase; no implementada**. Las decisiones de tecnología y modelado de este documento no constituyen evidencia de cumplimiento ni requisitos adicionales al enunciado.

## Arquitectura lógica

```text
OLTP PostgreSQL (oltp_sgfood) ─┐
                               ├─ Python extract/load ─> PostgreSQL DW.raw
CSV delimitados ───────────────┘                              │
                                      Airflow orquesta         v
                                              dbt: staging -> intermediate -> marts
                                                              │
                                                   pruebas y consultas analíticas
```

Propuesta tecnológica: Python para extracción/carga, Apache Airflow para orquestación, PostgreSQL como Data Warehouse y dbt Core con adapter PostgreSQL para transformación, pruebas y documentación. Las versiones se definirán solo después de comprobar compatibilidad en el entorno objetivo; no se fijan versiones en esta etapa.

## Separación de responsabilidades

- **OLTP**: fuente transaccional `oltp_sgfood`; no debe recibir tablas analíticas ni transformaciones del proyecto.
- **DW `raw`**: copia técnica de cada fuente, con metadatos de lote, archivo, extracción y carga. No corregir silenciosamente valores originales.
- **DW `staging`**: tipado, normalización técnica, nombres consistentes y validaciones de estructura; conservar columnas de origen relevantes.
- **DW `intermediate`**: relaciones y reglas reutilizables, por ejemplo ventas con sus dimensiones y snapshots de inventario; controlar cardinalidades antes de materializar hechos.
- **DW `marts`**: dimensiones y hechos consumibles para análisis, con claves sustitutas si se justifican y claves naturales de origen trazables.

Los schemas exactos de PostgreSQL quedan por confirmar según la convención final del proyecto, pero deben mantener la separación `raw`, `staging` y `marts`; `intermediate` puede ser schema o convención dbt explícita.

## Grano propuesto

| Modelo | Grano propuesto | Clave natural / control |
|---|---|---|
| `dim_sucursal` | Una sucursal | `id_sucursal` |
| `dim_categoria` | Una categoría | `id_categoria` |
| `dim_marca` | Una marca | `id_marca` |
| `dim_producto` | Un producto | `id_producto`; conservar categoría, marca, unidad y atributos de precio |
| `dim_cliente` | Un cliente | `id_cliente`; estrategia histórica SCD pendiente |
| `dim_fecha` | Un día del calendario analítico | Fecha calendario; rango a decidir |
| `dim_proveedor` | Un proveedor | Propuesta necesaria solo si se integra el archivo de precios como entidad analítica |
| `fct_ventas` | Exactamente una fila por `id_detalle` de `venta_detalle` | `id_detalle`; no asumir que (`id_venta`, `id_producto`) es único |
| `fct_inventario_snapshot` | Una existencia por fecha de corte, sucursal, producto y lote | Clave compuesta del catálogo |
| `fct_devoluciones` | Una devolución por `id_devolucion` | Evitar replicarla al unirla directamente a líneas si hay más de una devolución por venta/producto |
| `fct_metas_ventas` | Una meta por periodo y sucursal | (`periodo`, `id_sucursal`) |
| `fct_proveedores_precios` | Un precio reportado por proveedor, producto y vigencia | Clave compuesta propuesta |
| `casos_calidad_opcionales` | Un caso sintético de prueba | Fixture aislado; no es mart operativo |

`subtotal` del OLTP se conservará como medida de origen. Puede existir una medida derivada para reconciliación, pero nunca se reemplazará el subtotal original silenciosamente. Cualquier diferencia entre subtotal y una fórmula derivada debe quedar en una prueba/alerta y en documentación.

## Carga e idempotencia

1. **Extracción**: registrar fuente, lote, fecha/hora, archivo y hash o identificador de entrada sin exponer secretos.
2. **Raw**: cargar de forma repetible; usar una clave de lote y una estrategia explícita de reemplazo o deduplicación. La política exacta queda PENDIENTE de prueba en PostgreSQL.
3. **Staging/dbt**: usar `sources` para raw y `ref` entre modelos; evitar referencias directas cruzadas que oculten linaje.
4. **Hechos/dimensiones**: aplicar `unique`, `not_null`, `relationships` y reglas de dominio donde correspondan. Para dimensiones, decidir entre snapshot/SCD o sobrescritura antes de implementar.
5. **Reejecución**: un mismo lote no debe duplicar filas. La aceptación debe probar una primera carga, una segunda carga idéntica y una carga incremental nueva.
6. **Airflow**: tareas idempotentes, dependencias explícitas, retries controlados, logs y validación posterior. El schedule es opcional/recomendado por el enunciado.

## Reglas contra errores de modelado

- No unir `venta` directamente con varias fuentes de múltiples filas sin agregar primero al grano objetivo.
- Antes de unir devoluciones, proveedores, promociones o inventario a ventas, medir la cardinalidad y documentar la regla de asignación.
- No multiplicar `fct_ventas`: debe conservar exactamente una fila por `id_detalle` de `venta_detalle`; una promoción o devolución no puede convertir una línea en varias sin un hecho puente o una agregación aprobada.
- Para comparar ventas con metas, agregar primero las ventas a un grano temporal y geográfico compatible con las metas —como periodo mensual y sucursal— y comparar después de alinear calendario, sucursal y reglas de inclusión.
- Mantener los subtotales originales y reconciliar cantidades/importe con consultas independientes.
- Comparar vencimiento con el `fecha_corte` de cada snapshot. Los 658 vencimientos anteriores al 2026-08-31 no son, por sí solos, vencidos.

## Decisiones de negocio abiertas

- ¿Qué estados de `venta` y canales participan en los indicadores oficiales?
- ¿El análisis monetario usa `subtotal` del OLTP, una fórmula derivada o ambos con conciliación?
- ¿Las devoluciones reducen ventas, se reportan como hecho separado o ambas cosas?
- ¿Cómo se asignan promociones a ventas si no existe una relación explícita?
- ¿Se modelará proveedor como dimensión y cuál es la regla de selección cuando hay varios precios?
- ¿Inventario se analiza por lote, por producto agregado o en ambos niveles?
- ¿`dim_cliente` y `dim_producto` requieren historial tipo SCD o solo estado actual?
- ¿Las metas pertenecen a un hecho de presupuesto y cómo se comparan contra ventas por periodo?
- ¿Los casos opcionales se mantienen únicamente como fixtures de calidad?
- ¿Cuál es el calendario operativo, zona horaria y fecha de ejecución de los lotes?

Estas preguntas requieren aprobación del equipo; no deben resolverse inventando requisitos.

## Criterios de aceptación para la siguiente fase

La implementación podrá considerarse lista para revisión cuando, como mínimo:

1. Existan componentes Python, Airflow, PostgreSQL y dbt ejecutables mediante instrucciones reproducibles y sin secretos.
2. Una carga inicial y su reejecución produzcan conteos y claves sin duplicación no explicada en raw, staging e intermediate/marts.
3. Se reconcilien los conteos estáticos del catálogo: OLTP 6/8/10/80/250/1,200/3,209 y CSV 10/80/3,840/48/30/103, con cualquier diferencia documentada.
4. `fct_ventas` conserve el grano de `venta_detalle`, los FKs sean válidos y los joins de fuentes múltiples no multipliquen filas.
5. El subtotal original quede disponible y las diferencias con cálculos derivados sean visibles en pruebas o consultas de control.
6. Las pruebas cubran unicidad, no nulidad, relaciones, dominios y la regla de vencimiento por `fecha_corte`; el resultado real quede archivado.
7. Airflow ejecute carga, dbt y validaciones con dependencias, logs y manejo básico de errores.
8. La documentación final incluya arquitectura, DAG, modelos, configuración, integrantes, manual y consultas/evidencias de ejecución.

Todos estos criterios permanecen **PENDIENTES** hasta su ejecución real.
