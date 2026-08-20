/*
===============================================================================
Universidad de San Carlos de Guatemala
Facultad de Ingeniería
Escuela de Ciencias y Sistemas
Seminario de Sistemas 2

Práctica 1 - ETL con Python
Script: 05_reconciliation.sql

Descripción:
    Validación posterior al ETL para comprobar completitud, consistencia,
    trazabilidad e integridad de la carga.
===============================================================================
*/

USE SS2_Practica1_VuelosDW;
GO

SET NOCOUNT ON;
GO


DECLARE @ultima_ejecucion BIGINT;

SELECT
    @ultima_ejecucion = MAX(id_ejecucion)
FROM audit.EjecucionETL
WHERE estado = 'EXITOSO';


/* ============================================================================
   01. AUDITORÍA DE LA ÚLTIMA EJECUCIÓN
   ============================================================================ */

PRINT '===== 01. AUDITORIA ETL =====';

SELECT
    id_ejecucion,
    archivo_fuente,
    estado,
    filas_extraidas,
    filas_transformadas,
    filas_cargadas,
    filas_rechazadas,
    fecha_inicio,
    fecha_fin
FROM audit.EjecucionETL
WHERE id_ejecucion = @ultima_ejecucion;
GO


/* ============================================================================
   Como GO inicia un nuevo batch, recuperar nuevamente la ejecución.
   ============================================================================ */

DECLARE @ultima_ejecucion BIGINT;

SELECT
    @ultima_ejecucion = MAX(id_ejecucion)
FROM audit.EjecucionETL
WHERE estado = 'EXITOSO';


/* ============================================================================
   02. RECONCILIACIÓN DE CANTIDADES
   ============================================================================ */

PRINT '===== 02. RECONCILIACION DE CANTIDADES =====';

SELECT
    (
        SELECT COUNT(*)
        FROM stg.VueloRaw
        WHERE id_ejecucion = @ultima_ejecucion
    ) AS filas_staging,

    (
        SELECT COUNT(*)
        FROM dw.FactVueloPasajero
    ) AS filas_fact,

    (
        SELECT COUNT(DISTINCT record_id_fuente)
        FROM dw.FactVueloPasajero
    ) AS record_id_unicos;
GO


/* ============================================================================
   03. CORRESPONDENCIA STAGING -> FACT
   ============================================================================ */

DECLARE @ultima_ejecucion BIGINT;

SELECT
    @ultima_ejecucion = MAX(id_ejecucion)
FROM audit.EjecucionETL
WHERE estado = 'EXITOSO';

PRINT '===== 03. STAGING SIN HECHO =====';

SELECT
    COUNT(*) AS staging_sin_hecho
FROM stg.VueloRaw AS s
LEFT JOIN dw.FactVueloPasajero AS f
    ON f.record_id_fuente =
       TRY_CONVERT(INT, s.record_id)
WHERE
    s.id_ejecucion = @ultima_ejecucion
    AND f.id_fact_vuelo_pasajero IS NULL;
GO


/* ============================================================================
   04. CORRESPONDENCIA FACT -> STAGING
   ============================================================================ */

PRINT '===== 04. HECHOS SIN STAGING =====';

SELECT
    COUNT(*) AS hechos_sin_staging
FROM dw.FactVueloPasajero AS f
LEFT JOIN stg.VueloRaw AS s
    ON s.id_ejecucion = f.id_ejecucion
    AND TRY_CONVERT(INT, s.record_id) =
        f.record_id_fuente
WHERE s.id_staging IS NULL;
GO


/* ============================================================================
   05. CARDINALIDAD DE DIMENSIONES
   ============================================================================ */

PRINT '===== 05. CARDINALIDAD DE DIMENSIONES =====';

SELECT 'DimAerolinea' AS dimension, COUNT(*) AS registros
FROM dw.DimAerolinea

UNION ALL
SELECT 'DimAeronave', COUNT(*) FROM dw.DimAeronave

UNION ALL
SELECT 'DimAeropuerto', COUNT(*) FROM dw.DimAeropuerto

UNION ALL
SELECT 'DimCanalVenta', COUNT(*) FROM dw.DimCanalVenta

UNION ALL
SELECT 'DimClaseCabina', COUNT(*) FROM dw.DimClaseCabina

UNION ALL
SELECT 'DimEstadoVuelo', COUNT(*) FROM dw.DimEstadoVuelo

UNION ALL
SELECT 'DimFecha', COUNT(*) FROM dw.DimFecha

UNION ALL
SELECT 'DimMetodoPago', COUNT(*) FROM dw.DimMetodoPago

UNION ALL
SELECT 'DimMoneda', COUNT(*) FROM dw.DimMoneda

UNION ALL
SELECT 'DimPasajero', COUNT(*) FROM dw.DimPasajero

ORDER BY dimension;
GO


/* ============================================================================
   06. NULOS ESPERADOS
   ============================================================================ */

PRINT '===== 06. NULOS ESPERADOS =====';

SELECT
    SUM(
        CASE WHEN asiento IS NULL
        THEN 1 ELSE 0 END
    ) AS asientos_null,

    SUM(
        CASE WHEN fecha_hora_llegada IS NULL
        THEN 1 ELSE 0 END
    ) AS llegadas_null,

    SUM(
        CASE WHEN duracion_min IS NULL
        THEN 1 ELSE 0 END
    ) AS duraciones_null,

    SUM(
        CASE WHEN retraso_min IS NULL
        THEN 1 ELSE 0 END
    ) AS retrasos_null
FROM dw.FactVueloPasajero;

SELECT
    SUM(
        CASE WHEN edad IS NULL
        THEN 1 ELSE 0 END
    ) AS edades_null,

    SUM(
        CASE WHEN nacionalidad IS NULL
        THEN 1 ELSE 0 END
    ) AS nacionalidades_null
FROM dw.DimPasajero;
GO


/* ============================================================================
   07. CONSISTENCIA DE CANCELACIONES
   ============================================================================ */

PRINT '===== 07. CONSISTENCIA DE CANCELACIONES =====';

SELECT
    SUM(
        CASE
            WHEN e.estado_vuelo = 'CANCELLED'
            THEN 1 ELSE 0
        END
    ) AS cancelados,

    SUM(
        CASE
            WHEN e.estado_vuelo = 'CANCELLED'
             AND f.id_fecha_llegada IS NULL
             AND f.fecha_hora_llegada IS NULL
             AND f.duracion_min IS NULL
             AND f.retraso_min IS NULL
             AND f.asiento IS NULL
            THEN 1 ELSE 0
        END
    ) AS cancelados_correctos,

    SUM(
        CASE
            WHEN e.estado_vuelo <> 'CANCELLED'
             AND (
                    f.id_fecha_llegada IS NULL
                 OR f.fecha_hora_llegada IS NULL
                 OR f.duracion_min IS NULL
                 OR f.retraso_min IS NULL
                 OR f.asiento IS NULL
             )
            THEN 1 ELSE 0
        END
    ) AS activos_con_nulos_indebidos

FROM dw.FactVueloPasajero AS f
INNER JOIN dw.DimEstadoVuelo AS e
    ON e.id_estado_vuelo =
       f.id_estado_vuelo;
GO


/* ============================================================================
   08. CONSISTENCIA TEMPORAL
   ============================================================================ */

PRINT '===== 08. CONSISTENCIA TEMPORAL =====';

SELECT
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
    ) AS reservas_despues_salida
FROM dw.FactVueloPasajero;
GO


/* ============================================================================
   09. CONSISTENCIA DE NEGOCIO
   ============================================================================ */

PRINT '===== 09. CONSISTENCIA DE NEGOCIO =====';

SELECT
    SUM(
        CASE
            WHEN id_aeropuerto_origen =
                 id_aeropuerto_destino
            THEN 1 ELSE 0
        END
    ) AS origen_igual_destino,

    SUM(
        CASE
            WHEN maletas_facturadas > maletas_total
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


/* ============================================================================
   10. DUPLICADOS
   ============================================================================ */

PRINT '===== 10. DUPLICADOS =====';

SELECT
    COUNT(*) AS grupos_record_id_duplicados
FROM (
    SELECT
        record_id_fuente
    FROM dw.FactVueloPasajero
    GROUP BY
        record_id_fuente
    HAVING COUNT(*) > 1
) AS duplicados;
GO


/* ============================================================================
   11. FOREIGN KEYS
   ============================================================================ */

PRINT '===== 11. FOREIGN KEYS =====';

SELECT
    COUNT(*) AS foreign_keys_problematicas
FROM sys.foreign_keys
WHERE
    OBJECT_SCHEMA_NAME(parent_object_id)
        IN ('audit', 'stg', 'dw')
    AND (
        is_disabled = 1
        OR is_not_trusted = 1
    );
GO


/* ============================================================================
   12. ERRORES ETL
   ============================================================================ */

PRINT '===== 12. ERRORES ETL =====';

SELECT
    COUNT(*) AS errores_etl
FROM audit.ErrorETL;
GO


/* ============================================================================
   13. RANGO DE FECHAS
   ============================================================================ */

PRINT '===== 13. RANGO DE FECHAS =====';

SELECT
    MIN(fecha) AS fecha_minima,
    MAX(fecha) AS fecha_maxima,
    COUNT(*) AS fechas_distintas
FROM dw.DimFecha;
GO


PRINT '===== RECONCILIACION FINALIZADA =====';
GO
