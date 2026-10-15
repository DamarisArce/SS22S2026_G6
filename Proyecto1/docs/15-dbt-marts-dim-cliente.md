# Dimensión de clientes — `marts.dim_cliente`

## Modelo y origen

[`dim_cliente`](../dbt/models/marts/dim_cliente.sql) contiene **una fila por `id_cliente`** procedente de `stg_oltp_cliente`. Conserva las columnas `id_cliente`, `nit`, `nombre`, `tipo_cliente`, `municipio`, `departamento`, `fecha_alta` y cuatro campos técnicos de linaje. La materialización es una vista PostgreSQL.

## Cobertura de ventas

El hecho `fct_ventas_detalle` referencia `id_cliente` a través de la cabecera `venta`. Los tests de integridad comprueban unicidad, valores requeridos, correspondencia con staging y cobertura de clientes de ventas, sin convertir clientes sin compras en registros faltantes.

| Control sobre el conjunto validado | Resultado |
|---|---:|
| Clientes preservados | 250 |
| Claves `id_cliente` únicas | 250 |
| Cabeceras de venta | 1,200 |
| Clientes distintos referenciados por ventas | 249 |
| Clientes sin cabeceras de venta | 1 |
| Referencias a clientes inexistentes | 0 |
| Líneas de venta conservadas | 3,209 |

El cliente sin ventas se conserva legítimamente como miembro de la dimensión. No se atribuye una compra a un cliente sin relación explícita en el origen.

## Evidencias

- [Construcción 34](../resultados/34-dbt-marts-dim-cliente-run.txt).
- [Pruebas 35](../resultados/35-dbt-marts-dim-cliente-tests.txt).
- [Validación 36](../resultados/36-validacion-marts-dim-cliente-independiente.txt).

## Privacidad e historia

El conjunto académico es sintético, pero `nit`, nombre y residencia son categorías de información potencialmente personal en sistemas reales. La exposición de estos atributos debe estar sujeta a permisos apropiados. No existe una estrategia SCD2 que permita reconstruir cambios históricos en la clasificación o ubicación de un cliente.
