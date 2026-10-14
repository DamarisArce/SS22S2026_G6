with origen as (
    select
        date_trunc('month', fecha)::date as periodo,
        id_sucursal,
        count(*) as lineas_registradas,
        count(distinct id_venta) as ventas_distintas_registradas,
        sum(cantidad) as cantidad_registrada,
        sum(subtotal) as subtotal_registrado
    from {{ ref('int_venta_detalle_enriquecida') }}
    group by periodo, id_sucursal
), modelo as (
    select
        periodo,
        id_sucursal,
        sum(lineas_registradas) as lineas_registradas,
        sum(ventas_distintas_registradas) as ventas_distintas_registradas,
        sum(cantidad_registrada) as cantidad_registrada,
        sum(subtotal_registrado) as subtotal_registrado
    from {{ ref('int_ventas_mensuales_sucursal') }}
    group by periodo, id_sucursal
)
select
    origen.periodo as origen_periodo,
    modelo.periodo as modelo_periodo,
    origen.id_sucursal as origen_id_sucursal,
    modelo.id_sucursal as modelo_id_sucursal,
    origen.lineas_registradas as origen_lineas_registradas,
    modelo.lineas_registradas as modelo_lineas_registradas,
    origen.ventas_distintas_registradas as origen_ventas_distintas_registradas,
    modelo.ventas_distintas_registradas as modelo_ventas_distintas_registradas,
    origen.cantidad_registrada as origen_cantidad_registrada,
    modelo.cantidad_registrada as modelo_cantidad_registrada,
    origen.subtotal_registrado as origen_subtotal_registrado,
    modelo.subtotal_registrado as modelo_subtotal_registrado
from origen
full outer join modelo
    on origen.periodo = modelo.periodo
   and origen.id_sucursal = modelo.id_sucursal
where origen.periodo is null
   or modelo.periodo is null
   or origen.id_sucursal is null
   or modelo.id_sucursal is null
   or origen.lineas_registradas is distinct from modelo.lineas_registradas
   or origen.ventas_distintas_registradas is distinct from modelo.ventas_distintas_registradas
   or origen.cantidad_registrada is distinct from modelo.cantidad_registrada
   or origen.subtotal_registrado is distinct from modelo.subtotal_registrado
