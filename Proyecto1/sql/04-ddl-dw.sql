/*
  Bloque 3C6B - DDL académico del Data Warehouse SG-Food.

  Procedencia comprobada:
    - docker/postgres/dw/init/001-create-schemas.sql
    - sql/03-create-raw.sql
    - dbt/dbt_project.yml
    - dbt/models/{staging,intermediate,marts}/*.sql y schema.yml

  Este archivo es un inventario DDL de referencia. dbt administra staging,
  intermediate y marts como vistas (materialized=view). Por ello no contiene
  CREATE TABLE/VIEW para esos modelos: ejecutarlo sobre el DW actual podría
  entrar en conflicto con las vistas administradas por dbt. Las columnas y
  tipos indicados para marts se derivan de las expresiones SQL compilables y
  de los tipos de raw; no constituyen tablas físicas ni constraints físicos.
*/

-- Schemas existentes en el DW. Estas sentencias solo representan el contrato;
-- no se ejecutan en este bloque.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;

/*
  RAW (tablas físicas existentes)
  El DDL físico completo y autorizado está en sql/03-create-raw.sql. Incluye
  doce tablas: raw.oltp_sucursal, raw.oltp_categoria, raw.oltp_marca,
  raw.oltp_producto, raw.oltp_cliente, raw.oltp_venta,
  raw.oltp_venta_detalle, raw.csv_inventario_bodega, raw.csv_devoluciones,
  raw.csv_metas_ventas, raw.csv_promociones y raw.csv_proveedores_precios.
  Sus PRIMARY KEY/UNIQUE y NOT NULL son constraints físicos del raw.
*/

/*
  STAGING e INTERMEDIATE (vistas dbt; no se recrean aquí)
  - intermediate.int_venta_detalle_enriquecida: una fila por id_detalle;
    agrega atributos de la venta y producto mediante LEFT JOIN.
  - intermediate.int_inventario_snapshot: una fila por
    (fecha_corte, id_sucursal, id_producto, lote); conserva stocks y deriva
    es_vencido_en_corte y dias_para_vencer.
  - intermediate.int_devoluciones_enriquecida: una fila por id_devolucion;
    conserva la devolución y enriquece venta/producto.
  - intermediate.int_ventas_mensuales_sucursal: una fila por
    (periodo, id_sucursal); conserva lineas_registradas,
    ventas_distintas_registradas, cantidad_registrada y subtotal_registrado.
*/

/*
  MARTS (vistas dbt, tipos efectivos de referencia)

  marts.dim_sucursal — grano: una fila por id_sucursal.
    id_sucursal integer, nombre varchar(100), ciudad varchar(100),
    departamento varchar(100), _etl_load_id uuid,
    _etl_loaded_at timestamptz, _etl_source_table text,
    _etl_extracted_at timestamptz.

  marts.dim_cliente — grano: una fila por id_cliente.
    id_cliente integer, nit varchar(20), nombre varchar(150),
    tipo_cliente varchar(40), municipio varchar(100),
    departamento varchar(100), fecha_alta date, _etl_load_id uuid,
    _etl_loaded_at timestamptz, _etl_source_table text,
    _etl_extracted_at timestamptz.

  marts.dim_producto — grano: una fila por id_producto.
    id_producto integer, sku varchar(20), nombre varchar(150),
    id_categoria integer, id_marca integer, unidad_medida varchar(30),
    costo_base numeric(12,2), precio_lista numeric(12,2), activo boolean,
    _etl_load_id uuid, _etl_loaded_at timestamptz, _etl_source_table text,
    _etl_extracted_at timestamptz.

  marts.dim_fecha — grano: una fila por fecha DATE del rango continuo entre
    las fechas de venta y los periodos mensuales existentes.
    fecha date, anio integer, anio_iso integer, trimestre smallint,
    mes smallint, dia_mes smallint, dia_semana smallint,
    numero_semana smallint, inicio_mes date, fin_mes date,
    inicio_trimestre date, inicio_anio date, es_fin_semana boolean.

  marts.fct_ventas_detalle — grano: una fila por id_detalle.
    id_detalle bigint, id_venta bigint, id_producto integer,
    id_cliente integer, id_sucursal integer, fecha date, cantidad integer,
    precio_unitario numeric(12,2), descuento numeric(5,4),
    subtotal numeric(14,2), _etl_load_id uuid, _etl_loaded_at timestamptz,
    _etl_source_table text, _etl_extracted_at timestamptz.
*/

/*
  Relaciones lógicas verificadas por los modelos/tests dbt:
    fct_ventas_detalle.id_sucursal -> dim_sucursal.id_sucursal (N:1)
    fct_ventas_detalle.id_producto -> dim_producto.id_producto (N:1)
    fct_ventas_detalle.id_cliente  -> dim_cliente.id_cliente  (N:1)
    fct_ventas_detalle.fecha       -> dim_fecha.fecha         (N:1)
    dim_producto.id_categoria -> staging.stg_oltp_categoria.id_categoria
    dim_producto.id_marca     -> staging.stg_oltp_marca.id_marca
    int_inventario_snapshot.id_sucursal -> dim_sucursal.id_sucursal
    int_inventario_snapshot.id_producto -> dim_producto.id_producto
    int_devoluciones_enriquecida.id_venta -> staging.stg_oltp_venta.id_venta
    int_devoluciones_enriquecida.id_producto -> dim_producto.id_producto

  Brecha académica explícita: las vistas no pueden declarar PRIMARY KEY ni
  FOREIGN KEY físicos. Las unicidades, no nulidad, relaciones y
  reconciliaciones indicadas en dbt son pruebas de calidad, no constraints
  PostgreSQL. Satisfacer físicamente ese requisito exigiría materializar
  tablas (o cambiar la arquitectura dbt), lo cual no se hace en este bloque.
*/
