/*
===============================================================================
Universidad de San Carlos de Guatemala
Facultad de Ingeniería
Escuela de Ciencias y Sistemas
Seminario de Sistemas 2

Práctica 1 - ETL con Python
Script: 03_analytic_queries.sql

Descripción:
    Consultas analíticas sobre el modelo estrella de vuelos.

Grano de la tabla de hechos:
    Una fila de dw.FactVueloPasajero representa un registro fuente de un
    pasajero asociado con una reserva y una ocurrencia de vuelo.

Consideración:
    COUNT(*) sobre la tabla de hechos representa registros pasajero-vuelo.
    Cuando se calculan ocurrencias distintas de vuelo se indica expresamente.

Objetivos:
    - Validar las cantidades cargadas.
    - Obtener indicadores generales.
    - Generar rankings Top 5.
    - Analizar estados, retrasos y cancelaciones.
    - Analizar montos de boletos, ventas y precios.
    - Analizar pasajeros y equipaje.
    - Analizar comportamiento temporal.
===============================================================================
*/

USE SS2_Practica1_VuelosDW;
GO

SET NOCOUNT ON;
GO


/* ============================================================================
   CONSULTA 01
   RESUMEN GENERAL DEL DATA WAREHOUSE
   ============================================================================ */

PRINT '===== 01. RESUMEN GENERAL =====';

SELECT
    COUNT(*) AS total_registros_pasajero_vuelo,

    COUNT(DISTINCT record_id_fuente)
        AS record_id_unicos,

    COUNT(DISTINCT id_pasajero)
        AS pasajeros_distintos,

    CAST(
        SUM(precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_total_usd_estimado,

    CAST(
        AVG(precio_usd_estimado)
        AS DECIMAL(12,2)
    ) AS precio_promedio_usd_estimado,

    CAST(
        AVG(
            CAST(
                duracion_min AS DECIMAL(12,2)
            )
        )
        AS DECIMAL(12,2)
    ) AS duracion_promedio_min,

    CAST(
        AVG(
            CAST(
                retraso_min AS DECIMAL(12,2)
            )
        )
        AS DECIMAL(12,2)
    ) AS retraso_promedio_min
FROM dw.FactVueloPasajero;
GO


/* ============================================================================
   CONSULTA 02
   OCURRENCIAS DISTINTAS DE VUELO

   Se considera una ocurrencia distinta mediante:
       aerolínea + número de vuelo + origen + destino + fecha/hora de salida.
   ============================================================================ */

PRINT '===== 02. OCURRENCIAS DISTINTAS DE VUELO =====';

SELECT
    COUNT(*) AS ocurrencias_vuelo_distintas
FROM (
    SELECT
        id_aerolinea,
        numero_vuelo,
        id_aeropuerto_origen,
        id_aeropuerto_destino,
        fecha_hora_salida
    FROM dw.FactVueloPasajero
    GROUP BY
        id_aerolinea,
        numero_vuelo,
        id_aeropuerto_origen,
        id_aeropuerto_destino,
        fecha_hora_salida
) AS vuelos;
GO


/* ============================================================================
   CONSULTA 03
   DISTRIBUCIÓN GENERAL POR ESTADO
   ============================================================================ */

PRINT '===== 03. DISTRIBUCION POR ESTADO =====';

SELECT
    e.estado_vuelo,
    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje
FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimEstadoVuelo AS e
    ON e.id_estado_vuelo =
       f.id_estado_vuelo
GROUP BY
    e.estado_vuelo
ORDER BY
    cantidad_registros DESC;
GO


/* ============================================================================
   CONSULTA 04
   TOP 5 AEROPUERTOS DE DESTINO
   ============================================================================ */

PRINT '===== 04. TOP 5 DESTINOS =====';

SELECT TOP (5)
    a.codigo_aeropuerto AS destino,
    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje_total,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_usd_estimado
FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAeropuerto AS a
    ON a.id_aeropuerto =
       f.id_aeropuerto_destino
GROUP BY
    a.codigo_aeropuerto
ORDER BY
    cantidad_registros DESC,
    destino ASC;
GO


/* ============================================================================
   CONSULTA 05
   TOP 5 AEROPUERTOS DE ORIGEN
   ============================================================================ */

PRINT '===== 05. TOP 5 ORIGENES =====';

SELECT TOP (5)
    a.codigo_aeropuerto AS origen,
    COUNT(*) AS cantidad_registros,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_usd_estimado
FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAeropuerto AS a
    ON a.id_aeropuerto =
       f.id_aeropuerto_origen
GROUP BY
    a.codigo_aeropuerto
ORDER BY
    cantidad_registros DESC,
    origen ASC;
GO


/* ============================================================================
   CONSULTA 06
   TOP 5 RUTAS
   ============================================================================ */

PRINT '===== 06. TOP 5 RUTAS =====';

SELECT TOP (5)
    origen.codigo_aeropuerto AS origen,
    destino.codigo_aeropuerto AS destino,

    CONCAT(
        origen.codigo_aeropuerto,
        ' -> ',
        destino.codigo_aeropuerto
    ) AS ruta,

    COUNT(*) AS cantidad_registros,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_usd_estimado,

    CAST(
        AVG(
            CAST(
                f.duracion_min AS DECIMAL(12,2)
            )
        )
        AS DECIMAL(12,2)
    ) AS duracion_promedio_min
FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAeropuerto AS origen
    ON origen.id_aeropuerto =
       f.id_aeropuerto_origen
INNER JOIN dw.DimAeropuerto AS destino
    ON destino.id_aeropuerto =
       f.id_aeropuerto_destino
GROUP BY
    origen.codigo_aeropuerto,
    destino.codigo_aeropuerto
ORDER BY
    cantidad_registros DESC,
    origen.codigo_aeropuerto,
    destino.codigo_aeropuerto;
GO


/* ============================================================================
   CONSULTA 07
   VOLUMEN POR AEROLÍNEA
   ============================================================================ */

PRINT '===== 07. VOLUMEN POR AEROLINEA =====';

SELECT
    a.codigo_aerolinea,
    a.nombre_aerolinea,
    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje_total
FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAerolinea AS a
    ON a.id_aerolinea =
       f.id_aerolinea
GROUP BY
    a.codigo_aerolinea,
    a.nombre_aerolinea
ORDER BY
    cantidad_registros DESC,
    a.codigo_aerolinea;
GO


/* ============================================================================
   CONSULTA 08
   PUNTUALIDAD E IRREGULARIDADES POR AEROLÍNEA
   ============================================================================ */

PRINT '===== 08. PUNTUALIDAD POR AEROLINEA =====';

SELECT
    a.codigo_aerolinea,
    a.nombre_aerolinea,

    COUNT(*) AS total_registros,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'ON_TIME'
            THEN 1
            ELSE 0
        END
    ) AS on_time,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'DELAYED'
            THEN 1
            ELSE 0
        END
    ) AS delayed,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'CANCELLED'
            THEN 1
            ELSE 0
        END
    ) AS cancelled,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'DIVERTED'
            THEN 1
            ELSE 0
        END
    ) AS diverted,

    CAST(
        100.0 *
        SUM(
            CASE
                WHEN e.estado_vuelo = 'ON_TIME'
                THEN 1
                ELSE 0
            END
        )
        /
        NULLIF(COUNT(*), 0)
        AS DECIMAL(6,2)
    ) AS porcentaje_puntualidad

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAerolinea AS a
    ON a.id_aerolinea =
       f.id_aerolinea
INNER JOIN dw.DimEstadoVuelo AS e
    ON e.id_estado_vuelo =
       f.id_estado_vuelo
GROUP BY
    a.codigo_aerolinea,
    a.nombre_aerolinea
ORDER BY
    porcentaje_puntualidad DESC,
    total_registros DESC;
GO


/* ============================================================================
   CONSULTA 09
   RETRASOS POR AEROLÍNEA

   Solamente se incluyen registros DELAYED.
   ============================================================================ */

PRINT '===== 09. RETRASOS POR AEROLINEA =====';

SELECT
    a.codigo_aerolinea,
    a.nombre_aerolinea,

    COUNT(*) AS registros_retrasados,

    CAST(
        AVG(
            CAST(
                f.retraso_min AS DECIMAL(12,2)
            )
        )
        AS DECIMAL(12,2)
    ) AS retraso_promedio_min,

    MIN(f.retraso_min)
        AS retraso_minimo_min,

    MAX(f.retraso_min)
        AS retraso_maximo_min

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAerolinea AS a
    ON a.id_aerolinea =
       f.id_aerolinea
INNER JOIN dw.DimEstadoVuelo AS e
    ON e.id_estado_vuelo =
       f.id_estado_vuelo
WHERE
    e.estado_vuelo = 'DELAYED'
GROUP BY
    a.codigo_aerolinea,
    a.nombre_aerolinea
ORDER BY
    retraso_promedio_min DESC,
    registros_retrasados DESC;
GO


/* ============================================================================
   CONSULTA 10
   CANCELACIONES POR AEROLÍNEA
   ============================================================================ */

PRINT '===== 10. CANCELACIONES POR AEROLINEA =====';

SELECT
    a.codigo_aerolinea,
    a.nombre_aerolinea,

    COUNT(*) AS total_registros,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'CANCELLED'
            THEN 1
            ELSE 0
        END
    ) AS cancelaciones,

    CAST(
        100.0 *
        SUM(
            CASE
                WHEN e.estado_vuelo = 'CANCELLED'
                THEN 1
                ELSE 0
            END
        )
        /
        NULLIF(COUNT(*), 0)
        AS DECIMAL(6,2)
    ) AS porcentaje_cancelacion

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAerolinea AS a
    ON a.id_aerolinea =
       f.id_aerolinea
INNER JOIN dw.DimEstadoVuelo AS e
    ON e.id_estado_vuelo =
       f.id_estado_vuelo
GROUP BY
    a.codigo_aerolinea,
    a.nombre_aerolinea
ORDER BY
    porcentaje_cancelacion DESC,
    cancelaciones DESC;
GO


/* ============================================================================
   CONSULTA 11
   MONTO DE BOLETOS POR AEROLÍNEA
   ============================================================================ */

PRINT '===== 11. MONTO DE BOLETOS POR AEROLINEA =====';

SELECT
    a.codigo_aerolinea,
    a.nombre_aerolinea,

    COUNT(*) AS registros,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_total_usd_estimado,

    CAST(
        AVG(f.precio_usd_estimado)
        AS DECIMAL(12,2)
    ) AS precio_promedio_usd_estimado

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAerolinea AS a
    ON a.id_aerolinea =
       f.id_aerolinea
GROUP BY
    a.codigo_aerolinea,
    a.nombre_aerolinea
ORDER BY
    monto_total_usd_estimado DESC;
GO


/* ============================================================================
   CONSULTA 12
   MONTOS POR MONEDA
   ============================================================================ */

PRINT '===== 12. MONTOS POR MONEDA =====';

SELECT
    m.codigo_moneda,

    COUNT(*) AS cantidad_registros,

    CAST(
        SUM(f.precio_boleto)
        AS DECIMAL(18,2)
    ) AS total_moneda_original,

    CAST(
        AVG(f.precio_boleto)
        AS DECIMAL(12,2)
    ) AS precio_promedio_moneda_original,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS total_usd_estimado

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimMoneda AS m
    ON m.id_moneda =
       f.id_moneda
GROUP BY
    m.codigo_moneda
ORDER BY
    total_usd_estimado DESC;
GO


/* ============================================================================
   CONSULTA 13
   ANÁLISIS POR CLASE DE CABINA
   ============================================================================ */

PRINT '===== 13. CLASES DE CABINA =====';

SELECT
    c.clase_cabina,

    COUNT(*) AS cantidad_registros,

    CAST(
        AVG(f.precio_usd_estimado)
        AS DECIMAL(12,2)
    ) AS precio_promedio_usd,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_total_usd,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'CANCELLED'
            THEN 1
            ELSE 0
        END
    ) AS cancelaciones

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimClaseCabina AS c
    ON c.id_clase_cabina =
       f.id_clase_cabina
INNER JOIN dw.DimEstadoVuelo AS e
    ON e.id_estado_vuelo =
       f.id_estado_vuelo
GROUP BY
    c.clase_cabina
ORDER BY
    cantidad_registros DESC;
GO


/* ============================================================================
   CONSULTA 14
   CANALES DE VENTA
   ============================================================================ */

PRINT '===== 14. CANALES DE VENTA =====';

SELECT
    c.canal_venta,

    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_usd_estimado

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimCanalVenta AS c
    ON c.id_canal_venta =
       f.id_canal_venta
GROUP BY
    c.canal_venta
ORDER BY
    cantidad_registros DESC;
GO


/* ============================================================================
   CONSULTA 15
   MÉTODOS DE PAGO
   ============================================================================ */

PRINT '===== 15. METODOS DE PAGO =====';

SELECT
    m.metodo_pago,

    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_usd_estimado

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimMetodoPago AS m
    ON m.id_metodo_pago =
       f.id_metodo_pago
GROUP BY
    m.metodo_pago
ORDER BY
    cantidad_registros DESC;
GO


/* ============================================================================
   CONSULTA 16
   TENDENCIA MENSUAL SEGÚN FECHA DE SALIDA
   ============================================================================ */

PRINT '===== 16. TENDENCIA MENSUAL DE SALIDAS =====';

SELECT
    d.anio,
    d.mes,
    MAX(d.nombre_mes) AS nombre_mes,

    COUNT(*) AS cantidad_registros,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'ON_TIME'
            THEN 1 ELSE 0
        END
    ) AS on_time,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'DELAYED'
            THEN 1 ELSE 0
        END
    ) AS delayed,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'CANCELLED'
            THEN 1 ELSE 0
        END
    ) AS cancelled,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'DIVERTED'
            THEN 1 ELSE 0
        END
    ) AS diverted,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_usd_estimado

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimFecha AS d
    ON d.id_fecha =
       f.id_fecha_salida
INNER JOIN dw.DimEstadoVuelo AS e
    ON e.id_estado_vuelo =
       f.id_estado_vuelo
GROUP BY
    d.anio,
    d.mes
ORDER BY
    d.anio,
    d.mes;
GO


/* ============================================================================
   CONSULTA 17
   ANTICIPACIÓN DE RESERVA
   ============================================================================ */

PRINT '===== 17. ANTICIPACION DE RESERVA =====';

SELECT
    CASE
        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 0 AND 7
            THEN '01. 0-7 días'

        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 8 AND 30
            THEN '02. 8-30 días'

        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 31 AND 60
            THEN '03. 31-60 días'

        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 61 AND 90
            THEN '04. 61-90 días'

        ELSE '05. Más de 90 días'
    END AS rango_anticipacion,

    COUNT(*) AS cantidad_registros,

    CAST(
        AVG(
            CAST(
                DATEDIFF(
                    MINUTE,
                    fecha_hora_reserva,
                    fecha_hora_salida
                )
                AS DECIMAL(18,2)
            )
        )
        / 1440.0
        AS DECIMAL(10,2)
    ) AS anticipacion_promedio_dias

FROM dw.FactVueloPasajero
GROUP BY
    CASE
        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 0 AND 7
            THEN '01. 0-7 días'

        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 8 AND 30
            THEN '02. 8-30 días'

        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 31 AND 60
            THEN '03. 31-60 días'

        WHEN DATEDIFF(
            DAY,
            fecha_hora_reserva,
            fecha_hora_salida
        ) BETWEEN 61 AND 90
            THEN '04. 61-90 días'

        ELSE '05. Más de 90 días'
    END
ORDER BY
    rango_anticipacion;
GO


/* ============================================================================
   CONSULTA 18
   EQUIPAJE
   ============================================================================ */

PRINT '===== 18. EQUIPAJE =====';

SELECT
    maletas_total,

    COUNT(*) AS cantidad_registros,

    CAST(
        AVG(
            CAST(
                maletas_facturadas
                AS DECIMAL(10,2)
            )
        )
        AS DECIMAL(10,2)
    ) AS promedio_maletas_facturadas

FROM dw.FactVueloPasajero
GROUP BY
    maletas_total
ORDER BY
    maletas_total;
GO


/* ============================================================================
   CONSULTA 19
   DISTRIBUCIÓN POR GÉNERO
   ============================================================================ */

PRINT '===== 19. DISTRIBUCION POR GENERO =====';

SELECT
    p.genero,

    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimPasajero AS p
    ON p.id_pasajero =
       f.id_pasajero
GROUP BY
    p.genero
ORDER BY
    cantidad_registros DESC;
GO


/* ============================================================================
   CONSULTA 20
   DISTRIBUCIÓN POR NACIONALIDAD
   ============================================================================ */

PRINT '===== 20. NACIONALIDADES =====';

SELECT
    COALESCE(
        p.nacionalidad,
        'DESCONOCIDA'
    ) AS nacionalidad,

    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimPasajero AS p
    ON p.id_pasajero =
       f.id_pasajero
GROUP BY
    p.nacionalidad
ORDER BY
    cantidad_registros DESC;
GO


/* ============================================================================
   CONSULTA 21
   DISTRIBUCIÓN POR RANGO ETARIO
   ============================================================================ */

PRINT '===== 21. RANGOS DE EDAD =====';

SELECT
    CASE
        WHEN p.edad IS NULL
            THEN '00. DESCONOCIDA'
        WHEN p.edad < 18
            THEN '01. MENOR DE 18'
        WHEN p.edad BETWEEN 18 AND 25
            THEN '02. 18-25'
        WHEN p.edad BETWEEN 26 AND 35
            THEN '03. 26-35'
        WHEN p.edad BETWEEN 36 AND 45
            THEN '04. 36-45'
        WHEN p.edad BETWEEN 46 AND 60
            THEN '05. 46-60'
        ELSE '06. MAYOR DE 60'
    END AS rango_edad,

    COUNT(*) AS cantidad_registros,

    CAST(
        100.0 * COUNT(*)
        /
        NULLIF(
            (
                SELECT COUNT(*)
                FROM dw.FactVueloPasajero
            ),
            0
        )
        AS DECIMAL(6,2)
    ) AS porcentaje

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimPasajero AS p
    ON p.id_pasajero =
       f.id_pasajero
GROUP BY
    CASE
        WHEN p.edad IS NULL
            THEN '00. DESCONOCIDA'
        WHEN p.edad < 18
            THEN '01. MENOR DE 18'
        WHEN p.edad BETWEEN 18 AND 25
            THEN '02. 18-25'
        WHEN p.edad BETWEEN 26 AND 35
            THEN '03. 26-35'
        WHEN p.edad BETWEEN 36 AND 45
            THEN '04. 36-45'
        WHEN p.edad BETWEEN 46 AND 60
            THEN '05. 46-60'
        ELSE '06. MAYOR DE 60'
    END
ORDER BY
    rango_edad;
GO


/* ============================================================================
   CONSULTA 22
   TIPOS DE AERONAVE
   ============================================================================ */

PRINT '===== 22. TIPOS DE AERONAVE =====';

SELECT
    a.tipo_aeronave,

    COUNT(*) AS cantidad_registros,

    CAST(
        AVG(
            CAST(
                f.duracion_min AS DECIMAL(12,2)
            )
        )
        AS DECIMAL(12,2)
    ) AS duracion_promedio_min,

    CAST(
        AVG(f.precio_usd_estimado)
        AS DECIMAL(12,2)
    ) AS precio_promedio_usd

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAeronave AS a
    ON a.id_aeronave =
       f.id_aeronave
GROUP BY
    a.tipo_aeronave
ORDER BY
    cantidad_registros DESC;
GO


/* ============================================================================
   CONSULTA 23
   TOP 5 DESTINOS POR MONTO DE BOLETOS
   ============================================================================ */

PRINT '===== 23. TOP 5 DESTINOS POR MONTO DE BOLETOS =====';

SELECT TOP (5)
    a.codigo_aeropuerto AS destino,

    COUNT(*) AS cantidad_registros,

    CAST(
        SUM(f.precio_usd_estimado)
        AS DECIMAL(18,2)
    ) AS monto_total_usd_estimado,

    CAST(
        AVG(f.precio_usd_estimado)
        AS DECIMAL(12,2)
    ) AS precio_promedio_usd_estimado

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimAeropuerto AS a
    ON a.id_aeropuerto =
       f.id_aeropuerto_destino
GROUP BY
    a.codigo_aeropuerto
ORDER BY
    monto_total_usd_estimado DESC;
GO


/* ============================================================================
   CONSULTA 24
   CONTROL FINAL DE CALIDAD DE LA CARGA
   ============================================================================ */

PRINT '===== 24. CONTROL FINAL DE CALIDAD =====';

SELECT
    COUNT(*) AS total_hechos,

    COUNT(DISTINCT record_id_fuente)
        AS record_id_unicos,

    SUM(
        CASE
            WHEN fecha_hora_llegada IS NOT NULL
             AND fecha_hora_llegada < fecha_hora_salida
            THEN 1 ELSE 0
        END
    ) AS llegadas_antes_salida,

    SUM(
        CASE
            WHEN fecha_hora_reserva > fecha_hora_salida
            THEN 1 ELSE 0
        END
    ) AS reservas_despues_salida,

    SUM(
        CASE
            WHEN id_aeropuerto_origen =
                 id_aeropuerto_destino
            THEN 1 ELSE 0
        END
    ) AS origen_igual_destino,

    SUM(
        CASE
            WHEN maletas_facturadas >
                 maletas_total
            THEN 1 ELSE 0
        END
    ) AS equipaje_inconsistente,

    SUM(
        CASE
            WHEN precio_boleto < 0
              OR precio_usd_estimado < 0
            THEN 1 ELSE 0
        END
    ) AS precios_negativos

FROM dw.FactVueloPasajero;
GO


PRINT '===== CONSULTAS ANALITICAS FINALIZADAS =====';
GO
