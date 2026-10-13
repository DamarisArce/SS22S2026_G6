-- Bloque 2A: contrato de origen raw.
-- Este script debe ejecutarse como sgfood_raw_loader, nunca como administrador.
-- No elimina schemas, tablas ni datos fuera de las doce tablas administradas.

CREATE TABLE IF NOT EXISTS raw.oltp_sucursal (
    id_sucursal INTEGER NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    departamento VARCHAR(100) NOT NULL,
    _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_table TEXT NOT NULL,
    _etl_extracted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_sucursal)
);

CREATE TABLE IF NOT EXISTS raw.oltp_categoria (
    id_categoria INTEGER NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_table TEXT NOT NULL,
    _etl_extracted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_categoria)
);

CREATE TABLE IF NOT EXISTS raw.oltp_marca (
    id_marca INTEGER NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_table TEXT NOT NULL,
    _etl_extracted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_marca)
);

CREATE TABLE IF NOT EXISTS raw.oltp_producto (
    id_producto INTEGER NOT NULL,
    sku VARCHAR(20) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    id_categoria INTEGER NOT NULL,
    id_marca INTEGER NOT NULL,
    unidad_medida VARCHAR(30) NOT NULL,
    costo_base NUMERIC(12,2) NOT NULL,
    precio_lista NUMERIC(12,2) NOT NULL,
    activo BOOLEAN NOT NULL,
    _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_table TEXT NOT NULL,
    _etl_extracted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_producto), UNIQUE (sku)
);

CREATE TABLE IF NOT EXISTS raw.oltp_cliente (
    id_cliente INTEGER NOT NULL,
    nit VARCHAR(20) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    tipo_cliente VARCHAR(40) NOT NULL,
    municipio VARCHAR(100),
    departamento VARCHAR(100),
    fecha_alta DATE NOT NULL,
    _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_table TEXT NOT NULL,
    _etl_extracted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_cliente)
);

CREATE TABLE IF NOT EXISTS raw.oltp_venta (
    id_venta BIGINT NOT NULL,
    fecha DATE NOT NULL,
    id_cliente INTEGER NOT NULL,
    id_sucursal INTEGER NOT NULL,
    canal VARCHAR(30) NOT NULL,
    metodo_pago VARCHAR(30) NOT NULL,
    estado VARCHAR(20) NOT NULL,
    _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_table TEXT NOT NULL,
    _etl_extracted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_venta)
);

CREATE TABLE IF NOT EXISTS raw.oltp_venta_detalle (
    id_detalle BIGINT NOT NULL,
    id_venta BIGINT NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC(12,2) NOT NULL,
    descuento NUMERIC(5,4) NOT NULL,
    subtotal NUMERIC(14,2) NOT NULL,
    _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_table TEXT NOT NULL,
    _etl_extracted_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_detalle)
);

CREATE TABLE IF NOT EXISTS raw.csv_inventario_bodega (
    fecha_corte TEXT NOT NULL, id_sucursal TEXT NOT NULL, id_producto TEXT NOT NULL,
    stock_disponible TEXT NOT NULL, stock_minimo TEXT NOT NULL, stock_maximo TEXT NOT NULL,
    lote TEXT NOT NULL, fecha_vencimiento TEXT NOT NULL,
    _etl_load_id UUID NOT NULL, _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_name TEXT NOT NULL, _etl_source_sha256 CHAR(64) NOT NULL,
    _etl_row_number BIGINT NOT NULL,
    UNIQUE (fecha_corte, id_sucursal, id_producto, lote)
);

CREATE TABLE IF NOT EXISTS raw.csv_devoluciones (
    id_devolucion TEXT NOT NULL, fecha TEXT NOT NULL, id_venta TEXT NOT NULL,
    id_producto TEXT NOT NULL, cantidad TEXT NOT NULL, motivo TEXT NOT NULL,
    _etl_load_id UUID NOT NULL, _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_name TEXT NOT NULL, _etl_source_sha256 CHAR(64) NOT NULL,
    _etl_row_number BIGINT NOT NULL, UNIQUE (id_devolucion)
);

CREATE TABLE IF NOT EXISTS raw.csv_metas_ventas (
    periodo TEXT NOT NULL, id_sucursal TEXT NOT NULL, meta_ventas TEXT NOT NULL,
    meta_unidades TEXT NOT NULL, _etl_load_id UUID NOT NULL,
    _etl_loaded_at TIMESTAMPTZ NOT NULL, _etl_source_name TEXT NOT NULL,
    _etl_source_sha256 CHAR(64) NOT NULL, _etl_row_number BIGINT NOT NULL,
    UNIQUE (periodo, id_sucursal)
);

CREATE TABLE IF NOT EXISTS raw.csv_promociones (
    id_promocion TEXT NOT NULL, nombre TEXT NOT NULL, fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL, id_categoria TEXT NOT NULL, porcentaje_descuento TEXT NOT NULL,
    _etl_load_id UUID NOT NULL, _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_name TEXT NOT NULL, _etl_source_sha256 CHAR(64) NOT NULL,
    _etl_row_number BIGINT NOT NULL, UNIQUE (id_promocion)
);

CREATE TABLE IF NOT EXISTS raw.csv_proveedores_precios (
    id_proveedor TEXT NOT NULL, proveedor TEXT NOT NULL, id_producto TEXT NOT NULL,
    costo_proveedor TEXT NOT NULL, plazo_dias TEXT NOT NULL, fecha_vigencia TEXT NOT NULL,
    _etl_load_id UUID NOT NULL, _etl_loaded_at TIMESTAMPTZ NOT NULL,
    _etl_source_name TEXT NOT NULL, _etl_source_sha256 CHAR(64) NOT NULL,
    _etl_row_number BIGINT NOT NULL,
    UNIQUE (id_proveedor, id_producto, fecha_vigencia)
);
