/*
  Bloque 3C6B - consultas analíticas de solo lectura.
  Contrato consultado: vistas dbt en schemas marts e intermediate.
  No se recalculan ventas netas, márgenes, rotación, metas, descuentos,
  promociones ni devoluciones netas. "registrado/a" conserva el significado
  de las columnas documentadas por dbt.
*/

-- 1. Conteos generales: una fila por relación analítica y su grano.
SELECT 'marts.dim_sucursal' AS relacion, 'id_sucursal' AS grano, count(*) AS filas FROM marts.dim_sucursal
UNION ALL SELECT 'marts.dim_cliente', 'id_cliente', count(*) FROM marts.dim_cliente
UNION ALL SELECT 'marts.dim_producto', 'id_producto', count(*) FROM marts.dim_producto
UNION ALL SELECT 'marts.dim_fecha', 'fecha', count(*) FROM marts.dim_fecha
UNION ALL SELECT 'marts.fct_ventas_detalle', 'id_detalle', count(*) FROM marts.fct_ventas_detalle
UNION ALL SELECT 'intermediate.int_inventario_snapshot', '(fecha_corte,id_sucursal,id_producto,lote)', count(*) FROM intermediate.int_inventario_snapshot
UNION ALL SELECT 'intermediate.int_devoluciones_enriquecida', 'id_devolucion', count(*) FROM intermediate.int_devoluciones_enriquecida;

-- 2. Ventas registradas por sucursal: grano sucursal; no suma importes.
SELECT s.id_sucursal, s.nombre AS nombre_sucursal,
       count(DISTINCT f.id_venta) AS ventas_distintas_registradas,
       count(*) AS lineas_registradas,
       sum(f.cantidad) AS cantidad_registrada,
       sum(f.subtotal) AS subtotal_registrado
FROM marts.fct_ventas_detalle AS f
JOIN marts.dim_sucursal AS s ON s.id_sucursal = f.id_sucursal
GROUP BY s.id_sucursal, s.nombre
ORDER BY s.id_sucursal;

-- 3. Ventas registradas por período: usa la agregación mensual dbt ya definida.
SELECT periodo, id_sucursal, lineas_registradas,
       ventas_distintas_registradas, cantidad_registrada,
       subtotal_registrado
FROM intermediate.int_ventas_mensuales_sucursal
ORDER BY periodo, id_sucursal;

-- 4. Productos y cantidades registradas: grano producto; no une otros hechos.
SELECT p.id_producto, p.sku, p.nombre,
       sum(f.cantidad) AS cantidad_registrada,
       count(*) AS lineas_registradas
FROM marts.fct_ventas_detalle AS f
JOIN marts.dim_producto AS p ON p.id_producto = f.id_producto
GROUP BY p.id_producto, p.sku, p.nombre
ORDER BY p.id_producto;

-- 5. Dimensiones principales: una consulta por dimensión, sin multiplicar filas.
SELECT id_sucursal, nombre, ciudad, departamento FROM marts.dim_sucursal ORDER BY id_sucursal;
SELECT id_cliente, nit, nombre, tipo_cliente, municipio, departamento, fecha_alta FROM marts.dim_cliente ORDER BY id_cliente;
SELECT id_producto, sku, nombre, id_categoria, id_marca, unidad_medida, costo_base, precio_lista, activo
FROM marts.dim_producto ORDER BY id_producto;
SELECT fecha, anio, trimestre, mes, dia_mes, dia_semana, numero_semana, es_fin_semana
FROM marts.dim_fecha ORDER BY fecha;

-- 6. Inventario por fecha de corte y sucursal: grano de salida corte-sucursal.
SELECT i.fecha_corte, i.id_sucursal, i.nombre_sucursal,
       sum(i.stock_disponible) AS stock_disponible_registrado,
       count(*) AS lotes_registrados
FROM intermediate.int_inventario_snapshot AS i
GROUP BY i.fecha_corte, i.id_sucursal, i.nombre_sucursal
ORDER BY i.fecha_corte, i.id_sucursal;

-- 7. Inventario por producto y lote: conserva el grano original del snapshot.
SELECT fecha_corte, id_sucursal, id_producto, sku, nombre_producto, lote,
       stock_disponible, stock_minimo, stock_maximo, fecha_vencimiento
FROM intermediate.int_inventario_snapshot
ORDER BY fecha_corte, id_sucursal, id_producto, lote;

-- 8. Inventario según vencimiento registrado: usa la derivación dbt aprobada.
SELECT fecha_corte, id_sucursal, id_producto, lote, fecha_vencimiento,
       es_vencido_en_corte, dias_para_vencer, stock_disponible
FROM intermediate.int_inventario_snapshot
WHERE fecha_vencimiento IS NOT NULL
ORDER BY fecha_corte, es_vencido_en_corte DESC, fecha_vencimiento;

-- 9. Devoluciones registradas: una fila por devolución; no descuenta ventas.
SELECT id_devolucion, fecha, id_venta, id_producto, cantidad, motivo,
       fecha_venta, id_cliente, id_sucursal, sku, nombre_producto
FROM intermediate.int_devoluciones_enriquecida
ORDER BY fecha, id_devolucion;

-- 10. Integridad de claves: filas de hechos sin dimensión correspondiente.
SELECT 'sucursal' AS relacion, f.id_sucursal::text AS clave, count(*) AS filas_sin_dim
FROM marts.fct_ventas_detalle AS f
LEFT JOIN marts.dim_sucursal AS d ON d.id_sucursal = f.id_sucursal
WHERE d.id_sucursal IS NULL GROUP BY f.id_sucursal
UNION ALL
SELECT 'producto', f.id_producto::text, count(*)
FROM marts.fct_ventas_detalle AS f
LEFT JOIN marts.dim_producto AS d ON d.id_producto = f.id_producto
WHERE d.id_producto IS NULL GROUP BY f.id_producto
UNION ALL
SELECT 'cliente', f.id_cliente::text, count(*)
FROM marts.fct_ventas_detalle AS f
LEFT JOIN marts.dim_cliente AS d ON d.id_cliente = f.id_cliente
WHERE d.id_cliente IS NULL GROUP BY f.id_cliente
UNION ALL
SELECT 'fecha', f.fecha::text, count(*)
FROM marts.fct_ventas_detalle AS f
LEFT JOIN marts.dim_fecha AS d ON d.fecha = f.fecha
WHERE d.fecha IS NULL GROUP BY f.fecha;

-- 11. Cobertura del hecho: conteo y correspondencia real con dimensiones.
SELECT count(*) AS lineas_hecho,
       count(DISTINCT f.id_detalle) AS detalles_distintos,
       count(*) FILTER (WHERE s.id_sucursal IS NOT NULL) AS lineas_con_sucursal,
       count(*) FILTER (WHERE p.id_producto IS NOT NULL) AS lineas_con_producto,
       count(*) FILTER (WHERE c.id_cliente IS NOT NULL) AS lineas_con_cliente,
       count(*) FILTER (WHERE d.fecha IS NOT NULL) AS lineas_con_fecha
FROM marts.fct_ventas_detalle AS f
LEFT JOIN marts.dim_sucursal AS s ON s.id_sucursal = f.id_sucursal
LEFT JOIN marts.dim_producto AS p ON p.id_producto = f.id_producto
LEFT JOIN marts.dim_cliente AS c ON c.id_cliente = f.id_cliente
LEFT JOIN marts.dim_fecha AS d ON d.fecha = f.fecha;

-- 12. Reconciliación de conteos: marts contra sus modelos dbt de procedencia.
SELECT 'fct_ventas_detalle_vs_intermediate' AS comparacion,
       (SELECT count(*) FROM marts.fct_ventas_detalle) AS mart_count,
       (SELECT count(*) FROM intermediate.int_venta_detalle_enriquecida) AS origen_count,
       (SELECT count(DISTINCT id_detalle) FROM marts.fct_ventas_detalle) AS mart_distinct_key_count,
       (SELECT count(DISTINCT id_detalle) FROM intermediate.int_venta_detalle_enriquecida) AS origen_distinct_key_count
UNION ALL
SELECT 'dim_sucursal_vs_staging',
       (SELECT count(*) FROM marts.dim_sucursal),
       (SELECT count(*) FROM staging.stg_oltp_sucursal),
       (SELECT count(DISTINCT id_sucursal) FROM marts.dim_sucursal),
       (SELECT count(DISTINCT id_sucursal) FROM staging.stg_oltp_sucursal)
UNION ALL
SELECT 'dim_producto_vs_staging',
       (SELECT count(*) FROM marts.dim_producto),
       (SELECT count(*) FROM staging.stg_oltp_producto),
       (SELECT count(DISTINCT id_producto) FROM marts.dim_producto),
       (SELECT count(DISTINCT id_producto) FROM staging.stg_oltp_producto)
UNION ALL
SELECT 'dim_cliente_vs_staging',
       (SELECT count(*) FROM marts.dim_cliente),
       (SELECT count(*) FROM staging.stg_oltp_cliente),
       (SELECT count(DISTINCT id_cliente) FROM marts.dim_cliente),
       (SELECT count(DISTINCT id_cliente) FROM staging.stg_oltp_cliente);
