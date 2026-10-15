# Agregación de ventas mensuales por sucursal

## Modelo analítico

[`int_ventas_mensuales_sucursal`](../dbt/models/intermediate/int_ventas_mensuales_sucursal.sql) agrupa la información de `int_venta_detalle_enriquecida` por **primer día del mes (`periodo`) y `id_sucursal`**. Resume actividad registrada por el origen; no presupone reglas de ventas netas, campañas o reconocimiento contable.

| Medida | Cálculo dbt | Interpretación |
|---|---|---|
| `lineas_registradas` | `COUNT(*)` | Líneas de detalle del periodo y sucursal |
| `ventas_distintas_registradas` | `COUNT(DISTINCT id_venta)` | Cabeceras de venta distintas observadas en el grupo |
| `cantidad_registrada` | `SUM(cantidad)` | Cantidad original |
| `subtotal_registrado` | `SUM(subtotal)` | Subtotal original, sin recalcular |

## Integridad y resultados

En la muestra validada se observaron **48 grupos mes–sucursal**, correspondientes a ocho meses y seis sucursales; las sumas agregadas conservaron **3,209 líneas**, **1,200 ventas distintas**, **19,174 unidades** y **838,452.07** de subtotal registrado. No se detectaron duplicados de la clave compuesta ni diferencias en las comparaciones bidireccionales.

El contrato dbt verifica unicidad de `(periodo, id_sucursal)`, formato del periodo, relaciones y reconciliación de los agregados contra el detalle. Evidencias: [construcción 19](../resultados/19-dbt-ventas-mensuales-run.txt), [tests 20](../resultados/20-dbt-ventas-mensuales-tests.txt) y [reconciliación 21](../resultados/21-validacion-ventas-mensuales-independiente.txt).

## Límites de interpretación

La agrupación no excluye ventas en función de `estado` o `canal` porque no existe una política comercial aprobada en el enunciado. Tampoco resta devoluciones ni atribuye descuentos promocionales; se limita a agregar los valores originalmente registrados.
