# Modelo dimensional en estrella


    DimFecha {
        INT id_fecha PK
        DATE fecha UK
        SMALLINT anio
        TINYINT semestre
        TINYINT trimestre
        TINYINT mes
        VARCHAR nombre_mes
        TINYINT dia
        TINYINT dia_semana
        VARCHAR nombre_dia
        TINYINT numero_semana
        BIT es_fin_semana
    }

    DimAerolinea {
        SMALLINT id_aerolinea PK
        CHAR codigo_aerolinea UK
        NVARCHAR nombre_aerolinea
    }

    DimAeropuerto {
        SMALLINT id_aeropuerto PK
        CHAR codigo_aeropuerto UK
    }

    DimPasajero {
        INT id_pasajero PK
        UNIQUEIDENTIFIER passenger_id UK
        CHAR genero
        TINYINT edad
        CHAR nacionalidad
    }

    DimAeronave {
        SMALLINT id_aeronave PK
        VARCHAR tipo_aeronave UK
    }

    DimClaseCabina {
        TINYINT id_clase_cabina PK
        VARCHAR clase_cabina UK
    }

    DimEstadoVuelo {
        TINYINT id_estado_vuelo PK
        VARCHAR estado_vuelo UK
    }

    DimCanalVenta {
        TINYINT id_canal_venta PK
        VARCHAR canal_venta UK
    }

    DimMetodoPago {
        TINYINT id_metodo_pago PK
        VARCHAR metodo_pago UK
    }

    DimMoneda {
        TINYINT id_moneda PK
        CHAR codigo_moneda UK
    }

    FactVueloPasajero {
        BIGINT id_fact_vuelo_pasajero PK
        INT record_id_fuente UK

        INT id_fecha_salida FK
        INT id_fecha_llegada FK
        INT id_fecha_reserva FK

        SMALLINT id_aerolinea FK
        SMALLINT id_aeropuerto_origen FK
        SMALLINT id_aeropuerto_destino FK

        INT id_pasajero FK
        SMALLINT id_aeronave FK
        TINYINT id_clase_cabina FK
        TINYINT id_estado_vuelo FK
        TINYINT id_canal_venta FK
        TINYINT id_metodo_pago FK
        TINYINT id_moneda FK

        VARCHAR numero_vuelo
        VARCHAR asiento

        DATETIME2 fecha_hora_salida
        DATETIME2 fecha_hora_llegada
        DATETIME2 fecha_hora_reserva

        SMALLINT duracion_min
        SMALLINT retraso_min

        DECIMAL precio_boleto
        DECIMAL precio_usd_estimado

        TINYINT maletas_total
        TINYINT maletas_facturadas
        TINYINT cantidad_registros

        BIGINT id_ejecucion
        DATETIME2 fecha_carga
    }

