/*
===============================================================================
Universidad de San Carlos de Guatemala
Facultad de Ingeniería
Escuela de Ciencias y Sistemas
Seminario de Sistemas 2

Práctica 1 - ETL con Python
Script: 02_create_model.sql

Descripción:
    Crea las estructuras del proceso ETL y el modelo dimensional tipo estrella
    para el análisis de información de vuelos.

Grano de la tabla de hechos:
    Una fila de dw.FactVueloPasajero representa un registro fuente de un
    pasajero asociado con una reserva y una ocurrencia de vuelo.

Características:
    - Utiliza claves sustitutas (surrogate keys) en las dimensiones.
    - Conserva las claves naturales provenientes de la fuente.
    - Implementa integridad referencial mediante claves foráneas.
    - Implementa restricciones CHECK para reglas de integridad.
    - Incluye staging y auditoría del proceso ETL.
    - Es reejecutable sin eliminar estructuras existentes.
===============================================================================
*/

USE SS2_Practica1_VuelosDW;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO


/* ============================================================================
   1. AUDITORÍA DEL PROCESO ETL
   ============================================================================ */

IF OBJECT_ID(N'audit.EjecucionETL', N'U') IS NULL
BEGIN
    CREATE TABLE audit.EjecucionETL (
        id_ejecucion BIGINT IDENTITY(1,1) NOT NULL,

        archivo_fuente NVARCHAR(260) NOT NULL,

        fecha_inicio DATETIME2(0) NOT NULL
            CONSTRAINT DF_EjecucionETL_FechaInicio
            DEFAULT SYSDATETIME(),

        fecha_fin DATETIME2(0) NULL,

        estado VARCHAR(20) NOT NULL
            CONSTRAINT DF_EjecucionETL_Estado
            DEFAULT 'INICIADO',

        filas_extraidas INT NOT NULL
            CONSTRAINT DF_EjecucionETL_FilasExtraidas
            DEFAULT 0,

        filas_transformadas INT NOT NULL
            CONSTRAINT DF_EjecucionETL_FilasTransformadas
            DEFAULT 0,

        filas_cargadas INT NOT NULL
            CONSTRAINT DF_EjecucionETL_FilasCargadas
            DEFAULT 0,

        filas_rechazadas INT NOT NULL
            CONSTRAINT DF_EjecucionETL_FilasRechazadas
            DEFAULT 0,

        mensaje NVARCHAR(1000) NULL,

        CONSTRAINT PK_EjecucionETL
            PRIMARY KEY (id_ejecucion),

        CONSTRAINT CK_EjecucionETL_Estado
            CHECK (
                estado IN ('INICIADO', 'EXITOSO', 'ERROR')
            ),

        CONSTRAINT CK_EjecucionETL_Fechas
            CHECK (
                fecha_fin IS NULL
                OR fecha_fin >= fecha_inicio
            ),

        CONSTRAINT CK_EjecucionETL_Contadores
            CHECK (
                filas_extraidas >= 0
                AND filas_transformadas >= 0
                AND filas_cargadas >= 0
                AND filas_rechazadas >= 0
            )
    );

    PRINT 'Tabla audit.EjecucionETL creada.';
END
ELSE
BEGIN
    PRINT 'La tabla audit.EjecucionETL ya existe.';
END;
GO


IF OBJECT_ID(N'audit.ErrorETL', N'U') IS NULL
BEGIN
    CREATE TABLE audit.ErrorETL (
        id_error BIGINT IDENTITY(1,1) NOT NULL,

        id_ejecucion BIGINT NOT NULL,

        record_id_fuente NVARCHAR(50) NULL,

        fase VARCHAR(20) NOT NULL,

        tipo_error NVARCHAR(100) NOT NULL,

        detalle NVARCHAR(2000) NOT NULL,

        registro_original NVARCHAR(MAX) NULL,

        fecha_error DATETIME2(0) NOT NULL
            CONSTRAINT DF_ErrorETL_FechaError
            DEFAULT SYSDATETIME(),

        CONSTRAINT PK_ErrorETL
            PRIMARY KEY (id_error),

        CONSTRAINT FK_ErrorETL_EjecucionETL
            FOREIGN KEY (id_ejecucion)
            REFERENCES audit.EjecucionETL(id_ejecucion),

        CONSTRAINT CK_ErrorETL_Fase
            CHECK (
                fase IN ('EXTRACCION', 'TRANSFORMACION', 'CARGA')
            )
    );

    PRINT 'Tabla audit.ErrorETL creada.';
END
ELSE
BEGIN
    PRINT 'La tabla audit.ErrorETL ya existe.';
END;
GO


/* ============================================================================
   2. ÁREA DE STAGING

   Las columnas de la fuente se almacenan inicialmente como texto para evitar
   que una conversión prematura provoque pérdida del valor original.

   La limpieza y conversión de tipos se realiza posteriormente en Python.
   ============================================================================ */

IF OBJECT_ID(N'stg.VueloRaw', N'U') IS NULL
BEGIN
    CREATE TABLE stg.VueloRaw (
        id_staging BIGINT IDENTITY(1,1) NOT NULL,

        id_ejecucion BIGINT NOT NULL,

        record_id NVARCHAR(50) NULL,
        airline_code NVARCHAR(50) NULL,
        airline_name NVARCHAR(100) NULL,
        flight_number NVARCHAR(50) NULL,
        origin_airport NVARCHAR(50) NULL,
        destination_airport NVARCHAR(50) NULL,
        departure_datetime NVARCHAR(100) NULL,
        arrival_datetime NVARCHAR(100) NULL,
        duration_min NVARCHAR(50) NULL,
        status NVARCHAR(50) NULL,
        delay_min NVARCHAR(50) NULL,
        aircraft_type NVARCHAR(50) NULL,
        cabin_class NVARCHAR(50) NULL,
        seat NVARCHAR(50) NULL,
        passenger_id NVARCHAR(100) NULL,
        passenger_gender NVARCHAR(50) NULL,
        passenger_age NVARCHAR(50) NULL,
        passenger_nationality NVARCHAR(50) NULL,
        booking_datetime NVARCHAR(100) NULL,
        sales_channel NVARCHAR(50) NULL,
        payment_method NVARCHAR(50) NULL,
        ticket_price NVARCHAR(50) NULL,
        currency NVARCHAR(50) NULL,
        ticket_price_usd_est NVARCHAR(50) NULL,
        bags_total NVARCHAR(50) NULL,
        bags_checked NVARCHAR(50) NULL,

        fecha_carga DATETIME2(0) NOT NULL
            CONSTRAINT DF_VueloRaw_FechaCarga
            DEFAULT SYSDATETIME(),

        CONSTRAINT PK_VueloRaw
            PRIMARY KEY (id_staging),

        CONSTRAINT FK_VueloRaw_EjecucionETL
            FOREIGN KEY (id_ejecucion)
            REFERENCES audit.EjecucionETL(id_ejecucion)
    );

    PRINT 'Tabla stg.VueloRaw creada.';
END
ELSE
BEGIN
    PRINT 'La tabla stg.VueloRaw ya existe.';
END;
GO


/* ============================================================================
   3. DIMENSIÓN FECHA

   Una única dimensión se reutiliza en la tabla de hechos para:
       - fecha de salida
       - fecha de llegada
       - fecha de reserva

   Convención:
       dia_semana = 1 para lunes ... 7 para domingo.
   ============================================================================ */

IF OBJECT_ID(N'dw.DimFecha', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimFecha (
        id_fecha INT NOT NULL,

        fecha DATE NOT NULL,

        anio SMALLINT NOT NULL,

        semestre TINYINT NOT NULL,

        trimestre TINYINT NOT NULL,

        mes TINYINT NOT NULL,

        nombre_mes VARCHAR(15) NOT NULL,

        dia TINYINT NOT NULL,

        dia_semana TINYINT NOT NULL,

        nombre_dia VARCHAR(15) NOT NULL,

        numero_semana TINYINT NOT NULL,

        es_fin_semana BIT NOT NULL,

        CONSTRAINT PK_DimFecha
            PRIMARY KEY (id_fecha),

        CONSTRAINT UQ_DimFecha_Fecha
            UNIQUE (fecha),

        CONSTRAINT CK_DimFecha_Anio
            CHECK (anio BETWEEN 1900 AND 2200),

        CONSTRAINT CK_DimFecha_Semestre
            CHECK (semestre BETWEEN 1 AND 2),

        CONSTRAINT CK_DimFecha_Trimestre
            CHECK (trimestre BETWEEN 1 AND 4),

        CONSTRAINT CK_DimFecha_Mes
            CHECK (mes BETWEEN 1 AND 12),

        CONSTRAINT CK_DimFecha_Dia
            CHECK (dia BETWEEN 1 AND 31),

        CONSTRAINT CK_DimFecha_DiaSemana
            CHECK (dia_semana BETWEEN 1 AND 7),

        CONSTRAINT CK_DimFecha_NumeroSemana
            CHECK (numero_semana BETWEEN 1 AND 53)
    );

    PRINT 'Tabla dw.DimFecha creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimFecha ya existe.';
END;
GO


/* ============================================================================
   4. DIMENSIÓN AEROLÍNEA
   ============================================================================ */

IF OBJECT_ID(N'dw.DimAerolinea', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimAerolinea (
        id_aerolinea SMALLINT IDENTITY(1,1) NOT NULL,

        codigo_aerolinea CHAR(2) NOT NULL,

        nombre_aerolinea NVARCHAR(100) NOT NULL,

        CONSTRAINT PK_DimAerolinea
            PRIMARY KEY (id_aerolinea),

        CONSTRAINT UQ_DimAerolinea_Codigo
            UNIQUE (codigo_aerolinea)
    );

    PRINT 'Tabla dw.DimAerolinea creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimAerolinea ya existe.';
END;
GO


/* ============================================================================
   5. DIMENSIÓN AEROPUERTO

   Es una dimensión de roles:
       - aeropuerto de origen
       - aeropuerto de destino
   ============================================================================ */

IF OBJECT_ID(N'dw.DimAeropuerto', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimAeropuerto (
        id_aeropuerto SMALLINT IDENTITY(1,1) NOT NULL,

        codigo_aeropuerto CHAR(3) NOT NULL,

        CONSTRAINT PK_DimAeropuerto
            PRIMARY KEY (id_aeropuerto),

        CONSTRAINT UQ_DimAeropuerto_Codigo
            UNIQUE (codigo_aeropuerto)
    );

    PRINT 'Tabla dw.DimAeropuerto creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimAeropuerto ya existe.';
END;
GO


/* ============================================================================
   6. DIMENSIÓN PASAJERO
   ============================================================================ */

IF OBJECT_ID(N'dw.DimPasajero', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimPasajero (
        id_pasajero INT IDENTITY(1,1) NOT NULL,

        passenger_id UNIQUEIDENTIFIER NOT NULL,

        genero CHAR(1) NOT NULL,

        edad TINYINT NULL,

        nacionalidad CHAR(2) NULL,

        CONSTRAINT PK_DimPasajero
            PRIMARY KEY (id_pasajero),

        CONSTRAINT UQ_DimPasajero_PassengerId
            UNIQUE (passenger_id),

        CONSTRAINT CK_DimPasajero_Genero
            CHECK (
                genero IN ('M', 'F', 'X')
            ),

        CONSTRAINT CK_DimPasajero_Edad
            CHECK (
                edad IS NULL
                OR edad BETWEEN 0 AND 120
            )
    );

    PRINT 'Tabla dw.DimPasajero creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimPasajero ya existe.';
END;
GO


/* ============================================================================
   7. DIMENSIÓN AERONAVE
   ============================================================================ */

IF OBJECT_ID(N'dw.DimAeronave', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimAeronave (
        id_aeronave SMALLINT IDENTITY(1,1) NOT NULL,

        tipo_aeronave VARCHAR(10) NOT NULL,

        CONSTRAINT PK_DimAeronave
            PRIMARY KEY (id_aeronave),

        CONSTRAINT UQ_DimAeronave_Tipo
            UNIQUE (tipo_aeronave)
    );

    PRINT 'Tabla dw.DimAeronave creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimAeronave ya existe.';
END;
GO


/* ============================================================================
   8. DIMENSIÓN CLASE DE CABINA
   ============================================================================ */

IF OBJECT_ID(N'dw.DimClaseCabina', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimClaseCabina (
        id_clase_cabina TINYINT IDENTITY(1,1) NOT NULL,

        clase_cabina VARCHAR(20) NOT NULL,

        CONSTRAINT PK_DimClaseCabina
            PRIMARY KEY (id_clase_cabina),

        CONSTRAINT UQ_DimClaseCabina_Clase
            UNIQUE (clase_cabina)
    );

    PRINT 'Tabla dw.DimClaseCabina creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimClaseCabina ya existe.';
END;
GO


/* ============================================================================
   9. DIMENSIÓN ESTADO DEL VUELO
   ============================================================================ */

IF OBJECT_ID(N'dw.DimEstadoVuelo', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimEstadoVuelo (
        id_estado_vuelo TINYINT IDENTITY(1,1) NOT NULL,

        estado_vuelo VARCHAR(20) NOT NULL,

        CONSTRAINT PK_DimEstadoVuelo
            PRIMARY KEY (id_estado_vuelo),

        CONSTRAINT UQ_DimEstadoVuelo_Estado
            UNIQUE (estado_vuelo)
    );

    PRINT 'Tabla dw.DimEstadoVuelo creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimEstadoVuelo ya existe.';
END;
GO


/* ============================================================================
   10. DIMENSIÓN CANAL DE VENTA
   ============================================================================ */

IF OBJECT_ID(N'dw.DimCanalVenta', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimCanalVenta (
        id_canal_venta TINYINT IDENTITY(1,1) NOT NULL,

        canal_venta VARCHAR(20) NOT NULL,

        CONSTRAINT PK_DimCanalVenta
            PRIMARY KEY (id_canal_venta),

        CONSTRAINT UQ_DimCanalVenta_Canal
            UNIQUE (canal_venta)
    );

    PRINT 'Tabla dw.DimCanalVenta creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimCanalVenta ya existe.';
END;
GO


/*
    Miembro especial para registros cuyo canal de venta venga nulo.
    Se crea de manera idempotente.
*/

IF NOT EXISTS (
    SELECT 1
    FROM dw.DimCanalVenta
    WHERE canal_venta = 'DESCONOCIDO'
)
BEGIN
    INSERT INTO dw.DimCanalVenta (canal_venta)
    VALUES ('DESCONOCIDO');

    PRINT 'Miembro DESCONOCIDO agregado a dw.DimCanalVenta.';
END
ELSE
BEGIN
    PRINT 'El miembro DESCONOCIDO ya existe en dw.DimCanalVenta.';
END;
GO


/* ============================================================================
   11. DIMENSIÓN MÉTODO DE PAGO
   ============================================================================ */

IF OBJECT_ID(N'dw.DimMetodoPago', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimMetodoPago (
        id_metodo_pago TINYINT IDENTITY(1,1) NOT NULL,

        metodo_pago VARCHAR(20) NOT NULL,

        CONSTRAINT PK_DimMetodoPago
            PRIMARY KEY (id_metodo_pago),

        CONSTRAINT UQ_DimMetodoPago_Metodo
            UNIQUE (metodo_pago)
    );

    PRINT 'Tabla dw.DimMetodoPago creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimMetodoPago ya existe.';
END;
GO


/* ============================================================================
   12. DIMENSIÓN MONEDA
   ============================================================================ */

IF OBJECT_ID(N'dw.DimMoneda', N'U') IS NULL
BEGIN
    CREATE TABLE dw.DimMoneda (
        id_moneda TINYINT IDENTITY(1,1) NOT NULL,

        codigo_moneda CHAR(3) NOT NULL,

        CONSTRAINT PK_DimMoneda
            PRIMARY KEY (id_moneda),

        CONSTRAINT UQ_DimMoneda_Codigo
            UNIQUE (codigo_moneda)
    );

    PRINT 'Tabla dw.DimMoneda creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.DimMoneda ya existe.';
END;
GO


/* ============================================================================
   13. TABLA DE HECHOS: VUELO - PASAJERO

   Grano:
       Una fila representa un registro fuente de un pasajero asociado con una
       reserva y una ocurrencia de vuelo.

   Dimensiones con múltiples roles:
       DimFecha:
           - id_fecha_salida
           - id_fecha_llegada
           - id_fecha_reserva

       DimAeropuerto:
           - id_aeropuerto_origen
           - id_aeropuerto_destino

   Dimensiones degeneradas:
       - record_id_fuente
       - numero_vuelo
       - asiento

   Medidas principales:
       - duracion_min
       - retraso_min
       - precio_boleto
       - precio_usd_estimado
       - maletas_total
       - maletas_facturadas
       - cantidad_registros
   ============================================================================ */

IF OBJECT_ID(N'dw.FactVueloPasajero', N'U') IS NULL
BEGIN
    CREATE TABLE dw.FactVueloPasajero (
        id_fact_vuelo_pasajero BIGINT IDENTITY(1,1) NOT NULL,

        /* Clave del registro original */
        record_id_fuente INT NOT NULL,

        /* Roles de DimFecha */
        id_fecha_salida INT NOT NULL,
        id_fecha_llegada INT NULL,
        id_fecha_reserva INT NOT NULL,

        /* Dimensiones */
        id_aerolinea SMALLINT NOT NULL,

        id_aeropuerto_origen SMALLINT NOT NULL,
        id_aeropuerto_destino SMALLINT NOT NULL,

        id_pasajero INT NOT NULL,

        id_aeronave SMALLINT NOT NULL,

        id_clase_cabina TINYINT NOT NULL,

        id_estado_vuelo TINYINT NOT NULL,

        id_canal_venta TINYINT NOT NULL,

        id_metodo_pago TINYINT NOT NULL,

        id_moneda TINYINT NOT NULL,

        /* Dimensiones degeneradas */
        numero_vuelo VARCHAR(10) NOT NULL,

        asiento VARCHAR(5) NULL,

        /* Timestamp completo para análisis de hora y validaciones */
        fecha_hora_salida DATETIME2(0) NOT NULL,

        fecha_hora_llegada DATETIME2(0) NULL,

        fecha_hora_reserva DATETIME2(0) NOT NULL,

        /* Medidas */
        duracion_min SMALLINT NULL,

        retraso_min SMALLINT NULL,

        precio_boleto DECIMAL(12,2) NOT NULL,

        precio_usd_estimado DECIMAL(12,2) NOT NULL,

        maletas_total TINYINT NOT NULL,

        maletas_facturadas TINYINT NOT NULL,

        cantidad_registros TINYINT NOT NULL
            CONSTRAINT DF_FactVueloPasajero_Cantidad
            DEFAULT 1,

        /* Trazabilidad ETL */
        id_ejecucion BIGINT NOT NULL,

        fecha_carga DATETIME2(0) NOT NULL
            CONSTRAINT DF_FactVueloPasajero_FechaCarga
            DEFAULT SYSDATETIME(),

        /* --------------------------------------------------------------------
           Clave primaria y unicidad
           -------------------------------------------------------------------- */

        CONSTRAINT PK_FactVueloPasajero
            PRIMARY KEY (id_fact_vuelo_pasajero),

        CONSTRAINT UQ_FactVueloPasajero_RecordIdFuente
            UNIQUE (record_id_fuente),

        /* --------------------------------------------------------------------
           Relaciones con dimensiones
           -------------------------------------------------------------------- */

        CONSTRAINT FK_FactVueloPasajero_FechaSalida
            FOREIGN KEY (id_fecha_salida)
            REFERENCES dw.DimFecha(id_fecha),

        CONSTRAINT FK_FactVueloPasajero_FechaLlegada
            FOREIGN KEY (id_fecha_llegada)
            REFERENCES dw.DimFecha(id_fecha),

        CONSTRAINT FK_FactVueloPasajero_FechaReserva
            FOREIGN KEY (id_fecha_reserva)
            REFERENCES dw.DimFecha(id_fecha),

        CONSTRAINT FK_FactVueloPasajero_Aerolinea
            FOREIGN KEY (id_aerolinea)
            REFERENCES dw.DimAerolinea(id_aerolinea),

        CONSTRAINT FK_FactVueloPasajero_AeropuertoOrigen
            FOREIGN KEY (id_aeropuerto_origen)
            REFERENCES dw.DimAeropuerto(id_aeropuerto),

        CONSTRAINT FK_FactVueloPasajero_AeropuertoDestino
            FOREIGN KEY (id_aeropuerto_destino)
            REFERENCES dw.DimAeropuerto(id_aeropuerto),

        CONSTRAINT FK_FactVueloPasajero_Pasajero
            FOREIGN KEY (id_pasajero)
            REFERENCES dw.DimPasajero(id_pasajero),

        CONSTRAINT FK_FactVueloPasajero_Aeronave
            FOREIGN KEY (id_aeronave)
            REFERENCES dw.DimAeronave(id_aeronave),

        CONSTRAINT FK_FactVueloPasajero_ClaseCabina
            FOREIGN KEY (id_clase_cabina)
            REFERENCES dw.DimClaseCabina(id_clase_cabina),

        CONSTRAINT FK_FactVueloPasajero_EstadoVuelo
            FOREIGN KEY (id_estado_vuelo)
            REFERENCES dw.DimEstadoVuelo(id_estado_vuelo),

        CONSTRAINT FK_FactVueloPasajero_CanalVenta
            FOREIGN KEY (id_canal_venta)
            REFERENCES dw.DimCanalVenta(id_canal_venta),

        CONSTRAINT FK_FactVueloPasajero_MetodoPago
            FOREIGN KEY (id_metodo_pago)
            REFERENCES dw.DimMetodoPago(id_metodo_pago),

        CONSTRAINT FK_FactVueloPasajero_Moneda
            FOREIGN KEY (id_moneda)
            REFERENCES dw.DimMoneda(id_moneda),

        CONSTRAINT FK_FactVueloPasajero_EjecucionETL
            FOREIGN KEY (id_ejecucion)
            REFERENCES audit.EjecucionETL(id_ejecucion),

        /* --------------------------------------------------------------------
           Reglas de integridad
           -------------------------------------------------------------------- */

        CONSTRAINT CK_FactVueloPasajero_RecordId
            CHECK (
                record_id_fuente > 0
            ),

        CONSTRAINT CK_FactVueloPasajero_Aeropuertos
            CHECK (
                id_aeropuerto_origen <> id_aeropuerto_destino
            ),

        CONSTRAINT CK_FactVueloPasajero_Duracion
            CHECK (
                duracion_min IS NULL
                OR duracion_min > 0
            ),

        CONSTRAINT CK_FactVueloPasajero_Retraso
            CHECK (
                retraso_min IS NULL
                OR retraso_min >= 0
            ),

        CONSTRAINT CK_FactVueloPasajero_Precios
            CHECK (
                precio_boleto >= 0
                AND precio_usd_estimado >= 0
            ),

        CONSTRAINT CK_FactVueloPasajero_Equipaje
            CHECK (
                maletas_facturadas <= maletas_total
            ),

        CONSTRAINT CK_FactVueloPasajero_Cantidad
            CHECK (
                cantidad_registros = 1
            ),

        CONSTRAINT CK_FactVueloPasajero_ConsistenciaLlegada
            CHECK (
                (
                    id_fecha_llegada IS NULL
                    AND fecha_hora_llegada IS NULL
                )
                OR
                (
                    id_fecha_llegada IS NOT NULL
                    AND fecha_hora_llegada IS NOT NULL
                )
            ),

        CONSTRAINT CK_FactVueloPasajero_OrdenVuelo
            CHECK (
                fecha_hora_llegada IS NULL
                OR fecha_hora_llegada >= fecha_hora_salida
            ),

        CONSTRAINT CK_FactVueloPasajero_OrdenReserva
            CHECK (
                fecha_hora_reserva <= fecha_hora_salida
            )
    );

    PRINT 'Tabla dw.FactVueloPasajero creada.';
END
ELSE
BEGIN
    PRINT 'La tabla dw.FactVueloPasajero ya existe.';
END;
GO


/* ============================================================================
   14. ÍNDICES PARA CONSULTAS ANALÍTICAS

   SQL Server no crea automáticamente índices para las claves foráneas.
   Estos índices se orientan a los filtros y agrupaciones más probables.
   ============================================================================ */

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE
        object_id = OBJECT_ID(N'dw.FactVueloPasajero')
        AND name = N'IX_FactVueloPasajero_FechaSalida'
)
BEGIN
    CREATE INDEX IX_FactVueloPasajero_FechaSalida
        ON dw.FactVueloPasajero(id_fecha_salida);

    PRINT 'Índice IX_FactVueloPasajero_FechaSalida creado.';
END;
GO


IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE
        object_id = OBJECT_ID(N'dw.FactVueloPasajero')
        AND name = N'IX_FactVueloPasajero_Aerolinea'
)
BEGIN
    CREATE INDEX IX_FactVueloPasajero_Aerolinea
        ON dw.FactVueloPasajero(id_aerolinea);

    PRINT 'Índice IX_FactVueloPasajero_Aerolinea creado.';
END;
GO


IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE
        object_id = OBJECT_ID(N'dw.FactVueloPasajero')
        AND name = N'IX_FactVueloPasajero_Ruta'
)
BEGIN
    CREATE INDEX IX_FactVueloPasajero_Ruta
        ON dw.FactVueloPasajero(
            id_aeropuerto_origen,
            id_aeropuerto_destino
        );

    PRINT 'Índice IX_FactVueloPasajero_Ruta creado.';
END;
GO


IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE
        object_id = OBJECT_ID(N'dw.FactVueloPasajero')
        AND name = N'IX_FactVueloPasajero_Estado'
)
BEGIN
    CREATE INDEX IX_FactVueloPasajero_Estado
        ON dw.FactVueloPasajero(id_estado_vuelo);

    PRINT 'Índice IX_FactVueloPasajero_Estado creado.';
END;
GO


IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE
        object_id = OBJECT_ID(N'dw.FactVueloPasajero')
        AND name = N'IX_FactVueloPasajero_ClaseCabina'
)
BEGIN
    CREATE INDEX IX_FactVueloPasajero_ClaseCabina
        ON dw.FactVueloPasajero(id_clase_cabina);

    PRINT 'Índice IX_FactVueloPasajero_ClaseCabina creado.';
END;
GO


/* ============================================================================
   15. FINALIZACIÓN
   ============================================================================ */

PRINT 'Modelo dimensional creado/verificado correctamente.';
GO
