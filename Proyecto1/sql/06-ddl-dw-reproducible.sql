-- BLOQUE 3C6D: DDL reproducible extraído del catálogo real de sgfood_dw.
-- Fuente: pg_dump 16.15 sobre el contenedor DW activo.
-- Comando: pg_dump --schema-only --no-owner --no-privileges --no-tablespaces
--   --schema=raw --schema=staging --schema=intermediate --schema=marts.
-- Alcance comprobado: 12 tablas raw, 21 vistas dbt y 13 constraints raw.
-- No ejecutado; no modifica PostgreSQL. dbt conserva la propiedad operativa de las vistas.
--
-- PostgreSQL database dump
--

\restrict YhcviEQaWPxSjdpnwkbQ9UZQCcaXJ9QjHvnf0jAheUhPD42cgevdwrZFt8mFg8T

-- Dumped from database version 16.15 (Debian 16.15-1.pgdg12+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg12+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: intermediate; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA intermediate;


--
-- Name: marts; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA marts;


--
-- Name: raw; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA raw;


--
-- Name: staging; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA staging;


SET default_table_access_method = heap;

--
-- Name: csv_devoluciones; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.csv_devoluciones (
    id_devolucion text NOT NULL,
    fecha text NOT NULL,
    id_venta text NOT NULL,
    id_producto text NOT NULL,
    cantidad text NOT NULL,
    motivo text NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_name text NOT NULL,
    _etl_source_sha256 character(64) NOT NULL,
    _etl_row_number bigint NOT NULL
);


--
-- Name: oltp_producto; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.oltp_producto (
    id_producto integer NOT NULL,
    sku character varying(20) NOT NULL,
    nombre character varying(150) NOT NULL,
    id_categoria integer NOT NULL,
    id_marca integer NOT NULL,
    unidad_medida character varying(30) NOT NULL,
    costo_base numeric(12,2) NOT NULL,
    precio_lista numeric(12,2) NOT NULL,
    activo boolean NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_table text NOT NULL,
    _etl_extracted_at timestamp with time zone NOT NULL
);


--
-- Name: oltp_venta; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.oltp_venta (
    id_venta bigint NOT NULL,
    fecha date NOT NULL,
    id_cliente integer NOT NULL,
    id_sucursal integer NOT NULL,
    canal character varying(30) NOT NULL,
    metodo_pago character varying(30) NOT NULL,
    estado character varying(20) NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_table text NOT NULL,
    _etl_extracted_at timestamp with time zone NOT NULL
);


--
-- Name: stg_csv_devoluciones; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_csv_devoluciones AS
 SELECT (NULLIF(btrim(id_devolucion), ''::text))::bigint AS id_devolucion,
    (NULLIF(btrim(fecha), ''::text))::date AS fecha,
    (NULLIF(btrim(id_venta), ''::text))::bigint AS id_venta,
    (NULLIF(btrim(id_producto), ''::text))::integer AS id_producto,
    (NULLIF(btrim(cantidad), ''::text))::numeric AS cantidad,
    NULLIF(btrim(motivo), ''::text) AS motivo,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
   FROM raw.csv_devoluciones;


--
-- Name: stg_oltp_producto; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_oltp_producto AS
 SELECT id_producto,
    sku,
    nombre,
    id_categoria,
    id_marca,
    unidad_medida,
    costo_base,
    precio_lista,
    activo,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM raw.oltp_producto;


--
-- Name: stg_oltp_venta; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_oltp_venta AS
 SELECT id_venta,
    fecha,
    id_cliente,
    id_sucursal,
    canal,
    metodo_pago,
    estado,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM raw.oltp_venta;


--
-- Name: int_devoluciones_enriquecida; Type: VIEW; Schema: intermediate; Owner: -
--

CREATE VIEW intermediate.int_devoluciones_enriquecida AS
 SELECT devolucion.id_devolucion,
    devolucion.fecha,
    devolucion.id_venta,
    devolucion.id_producto,
    devolucion.cantidad,
    devolucion.motivo,
    devolucion._etl_load_id,
    devolucion._etl_loaded_at,
    devolucion._etl_source_name,
    devolucion._etl_source_sha256,
    devolucion._etl_row_number,
    venta.fecha AS fecha_venta,
    venta.id_cliente,
    venta.id_sucursal,
    venta.canal,
    venta.metodo_pago,
    venta.estado,
    producto.sku,
    producto.nombre AS nombre_producto,
    producto.id_categoria,
    producto.id_marca,
    producto.unidad_medida
   FROM ((staging.stg_csv_devoluciones devolucion
     LEFT JOIN staging.stg_oltp_venta venta ON ((devolucion.id_venta = venta.id_venta)))
     LEFT JOIN staging.stg_oltp_producto producto ON ((devolucion.id_producto = producto.id_producto)));


--
-- Name: csv_inventario_bodega; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.csv_inventario_bodega (
    fecha_corte text NOT NULL,
    id_sucursal text NOT NULL,
    id_producto text NOT NULL,
    stock_disponible text NOT NULL,
    stock_minimo text NOT NULL,
    stock_maximo text NOT NULL,
    lote text NOT NULL,
    fecha_vencimiento text NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_name text NOT NULL,
    _etl_source_sha256 character(64) NOT NULL,
    _etl_row_number bigint NOT NULL
);


--
-- Name: oltp_sucursal; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.oltp_sucursal (
    id_sucursal integer NOT NULL,
    nombre character varying(100) NOT NULL,
    ciudad character varying(100) NOT NULL,
    departamento character varying(100) NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_table text NOT NULL,
    _etl_extracted_at timestamp with time zone NOT NULL
);


--
-- Name: stg_csv_inventario_bodega; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_csv_inventario_bodega AS
 SELECT (NULLIF(btrim(fecha_corte), ''::text))::date AS fecha_corte,
    (NULLIF(btrim(id_sucursal), ''::text))::integer AS id_sucursal,
    (NULLIF(btrim(id_producto), ''::text))::integer AS id_producto,
    (NULLIF(btrim(stock_disponible), ''::text))::numeric AS stock_disponible,
    (NULLIF(btrim(stock_minimo), ''::text))::numeric AS stock_minimo,
    (NULLIF(btrim(stock_maximo), ''::text))::numeric AS stock_maximo,
    NULLIF(btrim(lote), ''::text) AS lote,
    (NULLIF(btrim(fecha_vencimiento), ''::text))::date AS fecha_vencimiento,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
   FROM raw.csv_inventario_bodega;


--
-- Name: stg_oltp_sucursal; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_oltp_sucursal AS
 SELECT id_sucursal,
    nombre,
    ciudad,
    departamento,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM raw.oltp_sucursal;


--
-- Name: int_inventario_snapshot; Type: VIEW; Schema: intermediate; Owner: -
--

CREATE VIEW intermediate.int_inventario_snapshot AS
 SELECT inventario.fecha_corte,
    inventario.id_sucursal,
    inventario.id_producto,
    inventario.lote,
    inventario.stock_disponible,
    inventario.stock_minimo,
    inventario.stock_maximo,
    inventario.fecha_vencimiento,
    inventario._etl_load_id,
    inventario._etl_loaded_at,
    inventario._etl_source_name,
    inventario._etl_source_sha256,
    inventario._etl_row_number,
    producto.sku,
    producto.nombre AS nombre_producto,
    sucursal.nombre AS nombre_sucursal,
        CASE
            WHEN (inventario.fecha_vencimiento IS NULL) THEN NULL::boolean
            ELSE (inventario.fecha_vencimiento < inventario.fecha_corte)
        END AS es_vencido_en_corte,
        CASE
            WHEN (inventario.fecha_vencimiento IS NULL) THEN NULL::integer
            ELSE (inventario.fecha_vencimiento - inventario.fecha_corte)
        END AS dias_para_vencer
   FROM ((staging.stg_csv_inventario_bodega inventario
     LEFT JOIN staging.stg_oltp_producto producto ON ((inventario.id_producto = producto.id_producto)))
     LEFT JOIN staging.stg_oltp_sucursal sucursal ON ((inventario.id_sucursal = sucursal.id_sucursal)));


--
-- Name: oltp_venta_detalle; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.oltp_venta_detalle (
    id_detalle bigint NOT NULL,
    id_venta bigint NOT NULL,
    id_producto integer NOT NULL,
    cantidad integer NOT NULL,
    precio_unitario numeric(12,2) NOT NULL,
    descuento numeric(5,4) NOT NULL,
    subtotal numeric(14,2) NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_table text NOT NULL,
    _etl_extracted_at timestamp with time zone NOT NULL
);


--
-- Name: stg_oltp_venta_detalle; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_oltp_venta_detalle AS
 SELECT id_detalle,
    id_venta,
    id_producto,
    cantidad,
    precio_unitario,
    descuento,
    subtotal,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM raw.oltp_venta_detalle;


--
-- Name: int_venta_detalle_enriquecida; Type: VIEW; Schema: intermediate; Owner: -
--

CREATE VIEW intermediate.int_venta_detalle_enriquecida AS
 SELECT detalle.id_detalle,
    detalle.id_venta,
    detalle.id_producto,
    detalle.cantidad,
    detalle.precio_unitario,
    detalle.descuento,
    detalle.subtotal,
    venta.fecha,
    venta.id_cliente,
    venta.id_sucursal,
    venta.canal,
    venta.metodo_pago,
    venta.estado,
    producto.sku,
    producto.nombre AS nombre_producto,
    producto.id_categoria,
    producto.id_marca,
    producto.unidad_medida,
    detalle._etl_load_id,
    detalle._etl_loaded_at,
    detalle._etl_source_table,
    detalle._etl_extracted_at
   FROM ((staging.stg_oltp_venta_detalle detalle
     LEFT JOIN staging.stg_oltp_venta venta ON ((detalle.id_venta = venta.id_venta)))
     LEFT JOIN staging.stg_oltp_producto producto ON ((detalle.id_producto = producto.id_producto)));


--
-- Name: int_ventas_mensuales_sucursal; Type: VIEW; Schema: intermediate; Owner: -
--

CREATE VIEW intermediate.int_ventas_mensuales_sucursal AS
 SELECT (date_trunc('month'::text, (fecha)::timestamp with time zone))::date AS periodo,
    id_sucursal,
    count(*) AS lineas_registradas,
    count(DISTINCT id_venta) AS ventas_distintas_registradas,
    sum(cantidad) AS cantidad_registrada,
    sum(subtotal) AS subtotal_registrado
   FROM intermediate.int_venta_detalle_enriquecida venta_detalle
  GROUP BY ((date_trunc('month'::text, (fecha)::timestamp with time zone))::date), id_sucursal;


--
-- Name: oltp_cliente; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.oltp_cliente (
    id_cliente integer NOT NULL,
    nit character varying(20) NOT NULL,
    nombre character varying(150) NOT NULL,
    tipo_cliente character varying(40) NOT NULL,
    municipio character varying(100),
    departamento character varying(100),
    fecha_alta date NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_table text NOT NULL,
    _etl_extracted_at timestamp with time zone NOT NULL
);


--
-- Name: stg_oltp_cliente; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_oltp_cliente AS
 SELECT id_cliente,
    nit,
    nombre,
    tipo_cliente,
    municipio,
    departamento,
    fecha_alta,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM raw.oltp_cliente;


--
-- Name: dim_cliente; Type: VIEW; Schema: marts; Owner: -
--

CREATE VIEW marts.dim_cliente AS
 SELECT id_cliente,
    nit,
    nombre,
    tipo_cliente,
    municipio,
    departamento,
    fecha_alta,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM staging.stg_oltp_cliente;


--
-- Name: dim_fecha; Type: VIEW; Schema: marts; Owner: -
--

CREATE VIEW marts.dim_fecha AS
 WITH fechas_fuente AS (
         SELECT stg_oltp_venta.fecha
           FROM staging.stg_oltp_venta
          WHERE (stg_oltp_venta.fecha IS NOT NULL)
        UNION ALL
         SELECT int_ventas_mensuales_sucursal.periodo AS fecha
           FROM intermediate.int_ventas_mensuales_sucursal
          WHERE (int_ventas_mensuales_sucursal.periodo IS NOT NULL)
        ), limites AS (
         SELECT min(fechas_fuente.fecha) AS fecha_minima,
            max(fechas_fuente.fecha) AS fecha_maxima
           FROM fechas_fuente
        ), calendario AS (
         SELECT (serie.fecha_generada)::date AS fecha
           FROM (limites
             CROSS JOIN LATERAL generate_series((limites.fecha_minima)::timestamp without time zone, (limites.fecha_maxima)::timestamp without time zone, '1 day'::interval) serie(fecha_generada))
        )
 SELECT fecha,
    (EXTRACT(year FROM fecha))::integer AS anio,
    (EXTRACT(isoyear FROM fecha))::integer AS anio_iso,
    (EXTRACT(quarter FROM fecha))::smallint AS trimestre,
    (EXTRACT(month FROM fecha))::smallint AS mes,
    (EXTRACT(day FROM fecha))::smallint AS dia_mes,
    (EXTRACT(isodow FROM fecha))::smallint AS dia_semana,
    (EXTRACT(week FROM fecha))::smallint AS numero_semana,
    (date_trunc('month'::text, (fecha)::timestamp with time zone))::date AS inicio_mes,
    ((date_trunc('month'::text, (fecha)::timestamp with time zone) + '1 mon -1 days'::interval))::date AS fin_mes,
    (date_trunc('quarter'::text, (fecha)::timestamp with time zone))::date AS inicio_trimestre,
    (date_trunc('year'::text, (fecha)::timestamp with time zone))::date AS inicio_anio,
    (EXTRACT(isodow FROM fecha) = ANY (ARRAY[(6)::numeric, (7)::numeric])) AS es_fin_semana
   FROM calendario;


--
-- Name: dim_producto; Type: VIEW; Schema: marts; Owner: -
--

CREATE VIEW marts.dim_producto AS
 SELECT id_producto,
    sku,
    nombre,
    id_categoria,
    id_marca,
    unidad_medida,
    costo_base,
    precio_lista,
    activo,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM staging.stg_oltp_producto;


--
-- Name: dim_sucursal; Type: VIEW; Schema: marts; Owner: -
--

CREATE VIEW marts.dim_sucursal AS
 SELECT id_sucursal,
    nombre,
    ciudad,
    departamento,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM staging.stg_oltp_sucursal;


--
-- Name: fct_ventas_detalle; Type: VIEW; Schema: marts; Owner: -
--

CREATE VIEW marts.fct_ventas_detalle AS
 SELECT id_detalle,
    id_venta,
    id_producto,
    id_cliente,
    id_sucursal,
    fecha,
    cantidad,
    precio_unitario,
    descuento,
    subtotal,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM intermediate.int_venta_detalle_enriquecida;


--
-- Name: csv_metas_ventas; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.csv_metas_ventas (
    periodo text NOT NULL,
    id_sucursal text NOT NULL,
    meta_ventas text NOT NULL,
    meta_unidades text NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_name text NOT NULL,
    _etl_source_sha256 character(64) NOT NULL,
    _etl_row_number bigint NOT NULL
);


--
-- Name: csv_promociones; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.csv_promociones (
    id_promocion text NOT NULL,
    nombre text NOT NULL,
    fecha_inicio text NOT NULL,
    fecha_fin text NOT NULL,
    id_categoria text NOT NULL,
    porcentaje_descuento text NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_name text NOT NULL,
    _etl_source_sha256 character(64) NOT NULL,
    _etl_row_number bigint NOT NULL
);


--
-- Name: csv_proveedores_precios; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.csv_proveedores_precios (
    id_proveedor text NOT NULL,
    proveedor text NOT NULL,
    id_producto text NOT NULL,
    costo_proveedor text NOT NULL,
    plazo_dias text NOT NULL,
    fecha_vigencia text NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_name text NOT NULL,
    _etl_source_sha256 character(64) NOT NULL,
    _etl_row_number bigint NOT NULL
);


--
-- Name: oltp_categoria; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.oltp_categoria (
    id_categoria integer NOT NULL,
    nombre character varying(100) NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_table text NOT NULL,
    _etl_extracted_at timestamp with time zone NOT NULL
);


--
-- Name: oltp_marca; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.oltp_marca (
    id_marca integer NOT NULL,
    nombre character varying(100) NOT NULL,
    _etl_load_id uuid NOT NULL,
    _etl_loaded_at timestamp with time zone NOT NULL,
    _etl_source_table text NOT NULL,
    _etl_extracted_at timestamp with time zone NOT NULL
);


--
-- Name: stg_csv_metas_ventas; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_csv_metas_ventas AS
 SELECT
        CASE
            WHEN (NULLIF(btrim(periodo), ''::text) IS NULL) THEN NULL::date
            ELSE ((btrim(periodo) || '-01'::text))::date
        END AS periodo,
    (NULLIF(btrim(id_sucursal), ''::text))::integer AS id_sucursal,
    (NULLIF(btrim(meta_ventas), ''::text))::numeric AS meta_ventas,
    (NULLIF(btrim(meta_unidades), ''::text))::numeric AS meta_unidades,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
   FROM raw.csv_metas_ventas;


--
-- Name: stg_csv_promociones; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_csv_promociones AS
 SELECT (NULLIF(btrim(id_promocion), ''::text))::bigint AS id_promocion,
    NULLIF(btrim(nombre), ''::text) AS nombre,
    (NULLIF(btrim(fecha_inicio), ''::text))::date AS fecha_inicio,
    (NULLIF(btrim(fecha_fin), ''::text))::date AS fecha_fin,
    (NULLIF(btrim(id_categoria), ''::text))::integer AS id_categoria,
    (NULLIF(btrim(porcentaje_descuento), ''::text))::numeric AS porcentaje_descuento,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
   FROM raw.csv_promociones;


--
-- Name: stg_csv_proveedores_precios; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_csv_proveedores_precios AS
 SELECT (NULLIF(btrim(id_proveedor), ''::text))::bigint AS id_proveedor,
    NULLIF(btrim(proveedor), ''::text) AS proveedor,
    (NULLIF(btrim(id_producto), ''::text))::integer AS id_producto,
    (NULLIF(btrim(costo_proveedor), ''::text))::numeric AS costo_proveedor,
    (NULLIF(btrim(plazo_dias), ''::text))::integer AS plazo_dias,
    (NULLIF(btrim(fecha_vigencia), ''::text))::date AS fecha_vigencia,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
   FROM raw.csv_proveedores_precios;


--
-- Name: stg_oltp_categoria; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_oltp_categoria AS
 SELECT id_categoria,
    nombre,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM raw.oltp_categoria;


--
-- Name: stg_oltp_marca; Type: VIEW; Schema: staging; Owner: -
--

CREATE VIEW staging.stg_oltp_marca AS
 SELECT id_marca,
    nombre,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
   FROM raw.oltp_marca;


--
-- Name: csv_devoluciones csv_devoluciones_id_devolucion_key; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.csv_devoluciones
    ADD CONSTRAINT csv_devoluciones_id_devolucion_key UNIQUE (id_devolucion);


--
-- Name: csv_inventario_bodega csv_inventario_bodega_fecha_corte_id_sucursal_id_producto_l_key; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.csv_inventario_bodega
    ADD CONSTRAINT csv_inventario_bodega_fecha_corte_id_sucursal_id_producto_l_key UNIQUE (fecha_corte, id_sucursal, id_producto, lote);


--
-- Name: csv_metas_ventas csv_metas_ventas_periodo_id_sucursal_key; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.csv_metas_ventas
    ADD CONSTRAINT csv_metas_ventas_periodo_id_sucursal_key UNIQUE (periodo, id_sucursal);


--
-- Name: csv_promociones csv_promociones_id_promocion_key; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.csv_promociones
    ADD CONSTRAINT csv_promociones_id_promocion_key UNIQUE (id_promocion);


--
-- Name: csv_proveedores_precios csv_proveedores_precios_id_proveedor_id_producto_fecha_vige_key; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.csv_proveedores_precios
    ADD CONSTRAINT csv_proveedores_precios_id_proveedor_id_producto_fecha_vige_key UNIQUE (id_proveedor, id_producto, fecha_vigencia);


--
-- Name: oltp_categoria oltp_categoria_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_categoria
    ADD CONSTRAINT oltp_categoria_pkey PRIMARY KEY (id_categoria);


--
-- Name: oltp_cliente oltp_cliente_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_cliente
    ADD CONSTRAINT oltp_cliente_pkey PRIMARY KEY (id_cliente);


--
-- Name: oltp_marca oltp_marca_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_marca
    ADD CONSTRAINT oltp_marca_pkey PRIMARY KEY (id_marca);


--
-- Name: oltp_producto oltp_producto_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_producto
    ADD CONSTRAINT oltp_producto_pkey PRIMARY KEY (id_producto);


--
-- Name: oltp_producto oltp_producto_sku_key; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_producto
    ADD CONSTRAINT oltp_producto_sku_key UNIQUE (sku);


--
-- Name: oltp_sucursal oltp_sucursal_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_sucursal
    ADD CONSTRAINT oltp_sucursal_pkey PRIMARY KEY (id_sucursal);


--
-- Name: oltp_venta_detalle oltp_venta_detalle_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_venta_detalle
    ADD CONSTRAINT oltp_venta_detalle_pkey PRIMARY KEY (id_detalle);


--
-- Name: oltp_venta oltp_venta_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.oltp_venta
    ADD CONSTRAINT oltp_venta_pkey PRIMARY KEY (id_venta);


--
-- PostgreSQL database dump complete
--

\unrestrict YhcviEQaWPxSjdpnwkbQ9UZQCcaXJ9QjHvnf0jAheUhPD42cgevdwrZFt8mFg8T
