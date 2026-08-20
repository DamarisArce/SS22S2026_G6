/*
===============================================================================
Práctica 1 - ETL con Python
Script auxiliar: 99_reset_data.sql

ADVERTENCIA:
    Elimina únicamente los DATOS de la práctica para permitir repetir una
    carga desde cero durante desarrollo.

    No elimina tablas.
    No elimina relaciones.
    No elimina restricciones.
    No elimina la base de datos.
    Conserva el miembro DESCONOCIDO de DimCanalVenta.
===============================================================================
*/

USE SS2_Practica1_VuelosDW;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

IF DB_NAME() <> N'SS2_Practica1_VuelosDW'
BEGIN
    THROW 50001, 'El script solamente puede ejecutarse en SS2_Practica1_VuelosDW.', 1;
END;
GO

BEGIN TRY

    BEGIN TRANSACTION;

    /* La tabla de hechos referencia dimensiones y auditoría. */
    DELETE FROM dw.FactVueloPasajero;

    /* Staging también referencia auditoría. */
    DELETE FROM stg.VueloRaw;

    /* Errores antes de eliminar la ejecución asociada. */
    DELETE FROM audit.ErrorETL;
    DELETE FROM audit.EjecucionETL;

    /* Dimensiones. */
    DELETE FROM dw.DimPasajero;
    DELETE FROM dw.DimAerolinea;
    DELETE FROM dw.DimAeropuerto;
    DELETE FROM dw.DimAeronave;
    DELETE FROM dw.DimClaseCabina;
    DELETE FROM dw.DimEstadoVuelo;
    DELETE FROM dw.DimMetodoPago;
    DELETE FROM dw.DimMoneda;
    DELETE FROM dw.DimFecha;

    /* Se conserva únicamente el miembro especial DESCONOCIDO. */
    DELETE FROM dw.DimCanalVenta
    WHERE canal_venta <> 'DESCONOCIDO';

    COMMIT TRANSACTION;

    PRINT 'Datos de la práctica eliminados correctamente.';

END TRY
BEGIN CATCH

    IF XACT_STATE() <> 0
    BEGIN
        ROLLBACK TRANSACTION;
    END;

    THROW;

END CATCH;
GO


PRINT '===== ESTADO POST-RESET =====';

SELECT 'audit.EjecucionETL' AS tabla, COUNT(*) AS registros
FROM audit.EjecucionETL

UNION ALL
SELECT 'audit.ErrorETL', COUNT(*)
FROM audit.ErrorETL

UNION ALL
SELECT 'stg.VueloRaw', COUNT(*)
FROM stg.VueloRaw

UNION ALL
SELECT 'dw.DimFecha', COUNT(*)
FROM dw.DimFecha

UNION ALL
SELECT 'dw.DimAerolinea', COUNT(*)
FROM dw.DimAerolinea

UNION ALL
SELECT 'dw.DimAeropuerto', COUNT(*)
FROM dw.DimAeropuerto

UNION ALL
SELECT 'dw.DimPasajero', COUNT(*)
FROM dw.DimPasajero

UNION ALL
SELECT 'dw.DimAeronave', COUNT(*)
FROM dw.DimAeronave

UNION ALL
SELECT 'dw.DimClaseCabina', COUNT(*)
FROM dw.DimClaseCabina

UNION ALL
SELECT 'dw.DimEstadoVuelo', COUNT(*)
FROM dw.DimEstadoVuelo

UNION ALL
SELECT 'dw.DimCanalVenta', COUNT(*)
FROM dw.DimCanalVenta

UNION ALL
SELECT 'dw.DimMetodoPago', COUNT(*)
FROM dw.DimMetodoPago

UNION ALL
SELECT 'dw.DimMoneda', COUNT(*)
FROM dw.DimMoneda

UNION ALL
SELECT 'dw.FactVueloPasajero', COUNT(*)
FROM dw.FactVueloPasajero

ORDER BY tabla;
GO
