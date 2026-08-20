/*
===============================================================================
Universidad de San Carlos de Guatemala
Facultad de Ingeniería
Escuela de Ciencias y Sistemas
Seminario de Sistemas 2

Práctica 1 - ETL con Python
Script: 04_validation_queries.sql

Descripción:
    Ejecuta pruebas de integridad sobre el modelo dimensional.

Objetivos:
    - Comprobar que un registro válido puede cargarse correctamente.
    - Verificar restricciones CHECK.
    - Verificar integridad referencial.
    - Confirmar que los datos inválidos son rechazados por SQL Server.
    - Ejecutar todas las pruebas sin dejar datos de prueba persistentes.

Importante:
    Todos los datos utilizados en estas pruebas se crean dentro de una
    transacción que se revierte mediante ROLLBACK.
===============================================================================
*/

USE SS2_Practica1_VuelosDW;
GO

SET NOCOUNT ON;
SET XACT_ABORT OFF;
GO


DECLARE @Resultados TABLE (
    numero INT IDENTITY(1,1) NOT NULL,
    prueba NVARCHAR(150) NOT NULL,
    resultado VARCHAR(10) NOT NULL,
    detalle NVARCHAR(4000) NULL
);


BEGIN TRY

    BEGIN TRANSACTION;


    /* ========================================================================
       1. FIXTURES VÁLIDOS PARA LAS PRUEBAS
       ======================================================================== */

    INSERT INTO audit.EjecucionETL (
        archivo_fuente,
        estado
    )
    VALUES (
        N'__VALIDACION_INTERNA__.csv',
        'INICIADO'
    );

    DECLARE @id_ejecucion BIGINT;
    SET @id_ejecucion = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Fechas temporales
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimFecha (
        id_fecha,
        fecha,
        anio,
        semestre,
        trimestre,
        mes,
        nombre_mes,
        dia,
        dia_semana,
        nombre_dia,
        numero_semana,
        es_fin_semana
    )
    VALUES
    (
        20981231,
        '2098-12-31',
        2098,
        2,
        4,
        12,
        'DICIEMBRE',
        31,
        3,
        'MIERCOLES',
        1,
        0
    ),
    (
        20990101,
        '2099-01-01',
        2099,
        1,
        1,
        1,
        'ENERO',
        1,
        4,
        'JUEVES',
        1,
        0
    );


    /* ------------------------------------------------------------------------
       Aerolínea temporal
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimAerolinea (
        codigo_aerolinea,
        nombre_aerolinea
    )
    VALUES (
        'ZZ',
        N'AEROLINEA VALIDACION'
    );

    DECLARE @id_aerolinea SMALLINT;
    SET @id_aerolinea = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Aeropuertos temporales
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimAeropuerto (
        codigo_aeropuerto
    )
    VALUES ('ZZA');

    DECLARE @id_aeropuerto_origen SMALLINT;
    SET @id_aeropuerto_origen = SCOPE_IDENTITY();


    INSERT INTO dw.DimAeropuerto (
        codigo_aeropuerto
    )
    VALUES ('ZZB');

    DECLARE @id_aeropuerto_destino SMALLINT;
    SET @id_aeropuerto_destino = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Pasajero temporal válido
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimPasajero (
        passenger_id,
        genero,
        edad,
        nacionalidad
    )
    VALUES (
        '00000000-0000-0000-0000-000000000001',
        'M',
        30,
        'GT'
    );

    DECLARE @id_pasajero INT;
    SET @id_pasajero = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Aeronave temporal
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimAeronave (
        tipo_aeronave
    )
    VALUES ('TEST1');

    DECLARE @id_aeronave SMALLINT;
    SET @id_aeronave = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Clase de cabina temporal
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimClaseCabina (
        clase_cabina
    )
    VALUES ('VALIDACION');

    DECLARE @id_clase_cabina TINYINT;
    SET @id_clase_cabina = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Estado temporal
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimEstadoVuelo (
        estado_vuelo
    )
    VALUES ('TEST');

    DECLARE @id_estado_vuelo TINYINT;
    SET @id_estado_vuelo = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Canal de venta temporal
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimCanalVenta (
        canal_venta
    )
    VALUES ('VALIDACION');

    DECLARE @id_canal_venta TINYINT;
    SET @id_canal_venta = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Método de pago temporal
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimMetodoPago (
        metodo_pago
    )
    VALUES ('PRUEBA');

    DECLARE @id_metodo_pago TINYINT;
    SET @id_metodo_pago = SCOPE_IDENTITY();


    /* ------------------------------------------------------------------------
       Moneda temporal
       ------------------------------------------------------------------------ */

    INSERT INTO dw.DimMoneda (
        codigo_moneda
    )
    VALUES ('ZZZ');

    DECLARE @id_moneda TINYINT;
    SET @id_moneda = SCOPE_IDENTITY();



    /* ========================================================================
       PRUEBA 1
       CONTROL POSITIVO:
       Un registro completamente válido debe poder insertarse.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000001,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados (
            prueba,
            resultado,
            detalle
        )
        VALUES (
            N'Control positivo: registro válido',
            'PASS',
            N'El registro válido fue aceptado correctamente.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados (
            prueba,
            resultado,
            detalle
        )
        VALUES (
            N'Control positivo: registro válido',
            'FAIL',
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 2
       Género inválido.
       Debe activar CK_DimPasajero_Genero.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.DimPasajero (
            passenger_id,
            genero,
            edad,
            nacionalidad
        )
        VALUES (
            '00000000-0000-0000-0000-000000000002',
            'Z',
            30,
            'GT'
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: género inválido',
            'FAIL',
            N'SQL Server aceptó un género fuera de M, F y X.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: género inválido',
            CASE
                WHEN CHARINDEX(
                    'CK_DimPasajero_Genero',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 3
       Edad inválida.
       Debe activar CK_DimPasajero_Edad.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.DimPasajero (
            passenger_id,
            genero,
            edad,
            nacionalidad
        )
        VALUES (
            '00000000-0000-0000-0000-000000000003',
            'M',
            200,
            'GT'
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: edad fuera de rango',
            'FAIL',
            N'SQL Server aceptó edad 200.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: edad fuera de rango',
            CASE
                WHEN CHARINDEX(
                    'CK_DimPasajero_Edad',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 4
       Clave foránea inexistente.
       Debe activar FK_FactVueloPasajero_Aerolinea.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000002,
            20990101,
            20990101,
            20981231,
            -1,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'FK: aerolínea inexistente',
            'FAIL',
            N'SQL Server aceptó una FK de aerolínea inexistente.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'FK: aerolínea inexistente',
            CASE
                WHEN CHARINDEX(
                    'FK_FactVueloPasajero_Aerolinea',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 5
       Aeropuerto origen = destino.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000003,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_origen,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: origen igual a destino',
            'FAIL',
            N'SQL Server aceptó origen y destino iguales.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: origen igual a destino',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_Aeropuertos',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 6
       Precio negativo.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000004,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            -1.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: precio negativo',
            'FAIL',
            N'SQL Server aceptó un precio negativo.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: precio negativo',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_Precios',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 7
       Maletas facturadas > maletas totales.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000005,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            2,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: equipaje inconsistente',
            'FAIL',
            N'SQL Server aceptó más maletas facturadas que totales.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: equipaje inconsistente',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_Equipaje',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 8
       Llegada anterior a salida.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000006,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T09:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: llegada anterior a salida',
            'FAIL',
            N'SQL Server aceptó una llegada anterior a la salida.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: llegada anterior a salida',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_OrdenVuelo',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 9
       Reserva posterior a salida.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000007,
            20990101,
            20990101,
            20990101,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2099-01-01T11:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: reserva posterior a salida',
            'FAIL',
            N'SQL Server aceptó una reserva posterior a la salida.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: reserva posterior a salida',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_OrdenReserva',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 10
       Duración igual a cero.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000008,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            0,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: duración igual a cero',
            'FAIL',
            N'SQL Server aceptó duración igual a cero.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: duración igual a cero',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_Duracion',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 11
       Retraso negativo.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000009,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            -1,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: retraso negativo',
            'FAIL',
            N'SQL Server aceptó retraso negativo.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: retraso negativo',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_Retraso',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 12
       Inconsistencia entre fecha de llegada dimensional y timestamp.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000010,
            20990101,
            NULL,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: llegada dimensional/timestamp inconsistente',
            'FAIL',
            N'SQL Server aceptó una llegada dimensional/timestamp inconsistente.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: llegada dimensional/timestamp inconsistente',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_ConsistenciaLlegada',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 13
       record_id_fuente debe ser positivo.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            0,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            1,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: record_id_fuente no positivo',
            'FAIL',
            N'SQL Server aceptó record_id_fuente igual a cero.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: record_id_fuente no positivo',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_RecordId',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       PRUEBA 14
       cantidad_registros debe permanecer en 1.
       ======================================================================== */

    BEGIN TRY

        INSERT INTO dw.FactVueloPasajero (
            record_id_fuente,
            id_fecha_salida,
            id_fecha_llegada,
            id_fecha_reserva,
            id_aerolinea,
            id_aeropuerto_origen,
            id_aeropuerto_destino,
            id_pasajero,
            id_aeronave,
            id_clase_cabina,
            id_estado_vuelo,
            id_canal_venta,
            id_metodo_pago,
            id_moneda,
            numero_vuelo,
            asiento,
            fecha_hora_salida,
            fecha_hora_llegada,
            fecha_hora_reserva,
            duracion_min,
            retraso_min,
            precio_boleto,
            precio_usd_estimado,
            maletas_total,
            maletas_facturadas,
            cantidad_registros,
            id_ejecucion
        )
        VALUES (
            900000011,
            20990101,
            20990101,
            20981231,
            @id_aerolinea,
            @id_aeropuerto_origen,
            @id_aeropuerto_destino,
            @id_pasajero,
            @id_aeronave,
            @id_clase_cabina,
            @id_estado_vuelo,
            @id_canal_venta,
            @id_metodo_pago,
            @id_moneda,
            'ZZ9999',
            '1A',
            '2099-01-01T10:00:00',
            '2099-01-01T12:00:00',
            '2098-12-31T12:00:00',
            120,
            0,
            100.00,
            100.00,
            1,
            1,
            2,
            @id_ejecucion
        );

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: cantidad_registros distinta de 1',
            'FAIL',
            N'SQL Server aceptó cantidad_registros distinta de 1.'
        );

    END TRY
    BEGIN CATCH

        INSERT INTO @Resultados
        VALUES (
            N'CHECK: cantidad_registros distinta de 1',
            CASE
                WHEN CHARINDEX(
                    'CK_FactVueloPasajero_Cantidad',
                    ERROR_MESSAGE()
                ) > 0
                    THEN 'PASS'
                ELSE 'FAIL'
            END,
            ERROR_MESSAGE()
        );

    END CATCH;



    /* ========================================================================
       RESULTADOS
       ======================================================================== */

    PRINT '===== RESULTADO DETALLADO DE PRUEBAS =====';

    SELECT
        numero,
        prueba,
        resultado,
        detalle
    FROM @Resultados
    ORDER BY numero;


    PRINT '===== RESUMEN =====';

    SELECT
        COUNT(*) AS total_pruebas,
        SUM(
            CASE
                WHEN resultado = 'PASS' THEN 1
                ELSE 0
            END
        ) AS pruebas_exitosas,
        SUM(
            CASE
                WHEN resultado = 'FAIL' THEN 1
                ELSE 0
            END
        ) AS pruebas_fallidas
    FROM @Resultados;


    /* ========================================================================
       ROLLBACK OBLIGATORIO
       Ningún dato temporal debe permanecer en el Data Warehouse.
       ======================================================================== */

    ROLLBACK TRANSACTION;

END TRY
BEGIN CATCH

    IF XACT_STATE() <> 0
    BEGIN
        ROLLBACK TRANSACTION;
    END;

    PRINT 'ERROR NO CONTROLADO DURANTE LA VALIDACIÓN:';
    PRINT ERROR_MESSAGE();

    THROW;

END CATCH;
GO


/* ============================================================================
   VALIDACIÓN POST-ROLLBACK
   ============================================================================ */

PRINT '===== VALIDACION DE LIMPIEZA POST-ROLLBACK =====';

SELECT
    (
        SELECT COUNT(*)
        FROM audit.EjecucionETL
        WHERE archivo_fuente = N'__VALIDACION_INTERNA__.csv'
    ) AS ejecuciones_prueba_restantes,

    (
        SELECT COUNT(*)
        FROM dw.DimAerolinea
        WHERE codigo_aerolinea = 'ZZ'
    ) AS aerolineas_prueba_restantes,

    (
        SELECT COUNT(*)
        FROM dw.DimAeropuerto
        WHERE codigo_aeropuerto IN ('ZZA', 'ZZB')
    ) AS aeropuertos_prueba_restantes,

    (
        SELECT COUNT(*)
        FROM dw.FactVueloPasajero
        WHERE record_id_fuente >= 900000000
    ) AS hechos_prueba_restantes;
GO


PRINT 'Validaciones de integridad finalizadas.';
GO
