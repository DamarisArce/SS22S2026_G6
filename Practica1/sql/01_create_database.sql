/*
===============================================================================
Universidad de San Carlos de Guatemala
Facultad de Ingeniería
Escuela de Ciencias y Sistemas
Seminario de Sistemas 2

Práctica 1 - ETL con Python
Script: 01_create_database.sql

Descripción:
    Crea la base de datos utilizada para el Data Warehouse de vuelos y los
    esquemas lógicos que separan staging, modelo dimensional y auditoría.

Características:
    - Reejecutable.
    - No elimina una base existente.
    - No destruye información previamente cargada.
===============================================================================
*/

USE master;
GO

SET NOCOUNT ON;
GO

/* ============================================================================
   1. CREACIÓN DE BASE DE DATOS
   ============================================================================ */

IF DB_ID(N'SS2_Practica1_VuelosDW') IS NULL
BEGIN
    PRINT 'Creando base de datos SS2_Practica1_VuelosDW...';

    CREATE DATABASE SS2_Practica1_VuelosDW;

    PRINT 'Base de datos creada correctamente.';
END
ELSE
BEGIN
    PRINT 'La base de datos SS2_Practica1_VuelosDW ya existe. No se recreará.';
END;
GO


/* ============================================================================
   2. SELECCIÓN DE BASE DE DATOS
   ============================================================================ */

USE SS2_Practica1_VuelosDW;
GO


/* ============================================================================
   3. CREACIÓN DEL ESQUEMA STAGING
   Datos provenientes directamente de las fuentes antes de su transformación.
   ============================================================================ */

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = N'stg'
)
BEGIN
    EXEC(N'CREATE SCHEMA stg AUTHORIZATION dbo;');
    PRINT 'Esquema stg creado correctamente.';
END
ELSE
BEGIN
    PRINT 'El esquema stg ya existe.';
END;
GO


/* ============================================================================
   4. CREACIÓN DEL ESQUEMA DATA WAREHOUSE
   Contendrá dimensiones y tabla de hechos del modelo estrella.
   ============================================================================ */

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = N'dw'
)
BEGIN
    EXEC(N'CREATE SCHEMA dw AUTHORIZATION dbo;');
    PRINT 'Esquema dw creado correctamente.';
END
ELSE
BEGIN
    PRINT 'El esquema dw ya existe.';
END;
GO


/* ============================================================================
   5. CREACIÓN DEL ESQUEMA DE AUDITORÍA
   Contendrá información sobre ejecuciones y errores del proceso ETL.
   ============================================================================ */

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = N'audit'
)
BEGIN
    EXEC(N'CREATE SCHEMA audit AUTHORIZATION dbo;');
    PRINT 'Esquema audit creado correctamente.';
END
ELSE
BEGIN
    PRINT 'El esquema audit ya existe.';
END;
GO


/* ============================================================================
   6. INFORMACIÓN DE CONFIRMACIÓN
   ============================================================================ */

PRINT 'Configuración inicial de la base de datos finalizada.';
GO
