# Bloque 1A — Infraestructura PostgreSQL

Estado al **12 de octubre de 2026**: **COMPROBADO en ejecución** para la
infraestructura PostgreSQL descrita en este documento.

## Alcance y fuentes de diseño

Esta especificación combina `AGENTS.md`, `compose.yaml`, este documento y la
evidencia guardada en `resultados/01-validacion-postgresql.txt`, fechada
`2026-10-12T22:36:17-06:00`.

- **COMPROBADO:** respaldado por la configuración y la evidencia disponible.
- **PENDIENTE:** aún no realizado o no validado.
- **RECOMENDADO:** medida propuesta, no cumplimiento actual.

El ZIP contiene ocho entradas: seis fuentes operativas y dos apoyos. Se copiaron
sin transformación a `data/` únicamente `sgfood_oltp.sql`,
`inventario_bodega.csv`, `devoluciones.csv`, `metas_ventas.csv`,
`promociones.csv` y `proveedores_precios.csv`. `casos_calidad_opcionales.csv`
queda reservado para fixtures de calidad; `catalogo_insumos_sgfood.xlsx` queda
como catálogo/diccionario. Ninguno de los dos se usa como dato operativo.

## Arquitectura física

```text
sgfood_access_net (bridge)
├── sgfood-oltp-postgres
└── sgfood-dw-postgres

sgfood_elt_net (internal)
├── sgfood-oltp-postgres
├── sgfood-dw-postgres
└── sgfood-airflow-postgres
```

Todos usan la etiqueta fija `postgres:16.15-bookworm`, sin `latest`, sin
`container_name` y sin reutilizar recursos externos. Cada servicio tiene
healthcheck `pg_isready`, límites locales de memoria/CPU y un volumen exclusivo.
La red es interna de Compose (`internal: true`) y `sgfood_access_net` usa el
driver `bridge`. El proyecto declara el nombre
`sgfood-ss2-g6-proyecto1`. Compose generará efectivamente la red
`sgfood-ss2-g6-proyecto1_sgfood_elt_net` y los volúmenes
`sgfood-ss2-g6-proyecto1_sgfood_elt_oltp_data`,
`sgfood-ss2-g6-proyecto1_sgfood_elt_dw_data` y
`sgfood-ss2-g6-proyecto1_sgfood_elt_airflow_data` a partir de las claves
lógicas. No se utilizan recursos externos preexistentes; antes del primer
arranque el operador debe comprobar que esos nombres no existan. OLTP y DW
están conectados a ambas redes; Airflow está conectado únicamente a la red
interna. La red interna restringe la conectividad externa de sus servicios.

## Servicios, puertos y variables

| Servicio | Base | Puerto publicado | Propósito |
|---|---|---:|---|
| `sgfood-oltp-postgres` | `sgfood_oltp` | `127.0.0.1:15433` | Fuente transaccional |
| `sgfood-dw-postgres` | `sgfood_dw` | `127.0.0.1:15434` | Raw y modelos analíticos futuros |
| `sgfood-airflow-postgres` | `airflow` | Ninguno | Metadatos de Airflow |

**COMPROBADO:** los tres servicios usan `postgres:16.15-bookworm`, reportan
estado `healthy`, y los puertos publicados son `127.0.0.1:15433` y
`127.0.0.1:15434`. Los nombres de usuario, contraseñas, bases, puertos, red y volúmenes provienen
de `.env`. `.env.example` contiene solo marcadores de secreto y valores de
validación; nunca se deben versionar contraseñas reales. El arranque requiere
un archivo `.env` local con credenciales propias; nunca deben usarse los
marcadores de `.env.example`. Los servicios futuros
deben usar los nombres DNS de Compose, no direcciones IP fijas.

## Inicialización

El OLTP monta `data/sgfood_oltp.sql` como
`/docker-entrypoint-initdb.d/001-sgfood_oltp.sql`, mediante el mecanismo oficial
de la imagen PostgreSQL. Ese SQL contiene `DROP SCHEMA IF EXISTS
oltp_sgfood CASCADE`; por ello, su aplicación se considera segura únicamente
durante la creación de un directorio de datos vacío y aislado del volumen
`sgfood_elt_oltp_data`. PostgreSQL no vuelve a ejecutar scripts de esa carpeta
cuando el directorio ya está inicializado: los scripts solo se ejecutan
automáticamente con el directorio de datos vacío. Una inicialización fallida no
se resuelve necesariamente reiniciando el contenedor; requiere revisar la
causa y el estado del directorio de datos.

**COMPROBADO:** la primera inicialización OLTP fue exitosa. La evidencia
registra `sucursal` 6, `categoria` 8, `marca` 10, `producto` 80, `cliente` 250,
`venta` 1200 y `venta_detalle` 3209.

El DW monta `docker/postgres/dw/init/001-create-schemas.sql`, que crea de forma
idempotente `raw`, `staging`, `intermediate` y `marts` en un directorio nuevo.
No crea todavía tablas raw, dimensiones, hechos ni modelos dbt.

**COMPROBADO:** la inicialización de los cuatro schemas DW fue exitosa:
`raw`, `staging`, `intermediate` y `marts`.

## Permisos futuros

La implementación posterior deberá separar, como mínimo:

- lectura controlada del OLTP para extracción;
- escritura limitada en `raw`;
- ejecución de transformaciones dbt sobre `staging`, `intermediate` y `marts`;
- lectura de modelos analíticos para consumidores.

No se otorgan permisos cruzados ni privilegios amplios en el Bloque 1A. La
conectividad entre PostgreSQL requerirá una decisión posterior sobre credenciales
y roles. En la imagen oficial, `POSTGRES_USER` genera el usuario inicial de la
base con privilegios administrativos elevados; los futuros procesos ETL y dbt
deberán utilizar roles separados con privilegios mínimos. No se implementan
todavía esos roles ni se considera al administrador una solución final.

**COMPROBADO:** la conexión autenticada con `airflow_admin` fue exitosa.
**PENDIENTE:** implementar y validar los roles separados de ETL y dbt.
**RECOMENDADO:** no utilizar administradores como solución final y aplicar
privilegios mínimos.

## Procedimiento de arranque propuesto

1. Copiar `.env.example` a `.env` y reemplazar cada marcador por credenciales
   propias locales; nunca iniciar con los marcadores de `.env.example`.
2. Comprobar que `15433` y `15434` estén libres y que no existan la red ni los
   tres volúmenes con los nombres efectivos previstos para este proyecto.
3. Ejecutar `docker compose --env-file .env config --quiet`.
4. Solo con esa revisión aprobada, ejecutar `docker compose --env-file .env up
   -d`.
5. Esperar los healthchecks y revisar los logs de cada servicio.

**COMPROBADO:** se recrearon OLTP y DW conservando sus volúmenes, y las
pruebas TCP desde Ubuntu fueron satisfactorias. La ejecución inicial y la
validación indicada en `resultados/01-validacion-postgresql.txt` ya ocurrieron.

No usar `docker compose down -v`, `docker system prune` ni comandos de borrado
de volúmenes como parte del procedimiento normal.

## Verificación propuesta

Después del primer arranque, comprobar sin exponer secretos:

- `docker compose ps` muestra los tres servicios saludables;
- `docker volume ls` muestra solo los tres nombres `sgfood_elt_*` esperados;
- `docker network ls` muestra `sgfood_elt_net`;
- el OLTP contiene el schema `oltp_sgfood` y sus tablas;
- el DW contiene exactamente los cuatro schemas iniciales;
- el contenedor Airflow responde a `pg_isready` dentro de la red.

`pg_isready` solo indica disponibilidad del servidor; no valida credenciales ni
la existencia de datos. **COMPROBADO:** las tablas y schemas se verificaron con
SQL y los resultados se conservaron en `resultados/`; los servicios están
saludables, existen los cuatro schemas DW y funcionó la conexión autenticada de
Airflow. **PENDIENTE:** validar el flujo completo de aplicaciones y modelos.

## Parada segura

Para una pausa normal, usar `docker compose --env-file .env stop`. Para retirar
los contenedores conservando datos, usar `docker compose --env-file .env down`
sin `-v`, previa revisión del contexto. No detener ni modificar contenedores,
redes o volúmenes de otros proyectos.

## Integridad de fuentes

Las copias de `data/` se obtuvieron byte a byte desde el ZIP. SHA-256 verificado
contra la entrada correspondiente:

| Archivo | Filas de datos | SHA-256 |
|---|---:|---|
| `sgfood_oltp.sql` | SQL original | `09504cd1257e598462d7432020104835a519d2de3d978d355c4c13a342817c4a` |
| `inventario_bodega.csv` | 3840 | `7e8794981f5e1fff24b92af8e6676c01bed0ad5b8c441d4b7c134a4e85c9c426` |
| `devoluciones.csv` | 80 | `52e2a98e40258aadc90e143184bc33a6503bc2580afa30a8dee975c57bb96d8b` |
| `metas_ventas.csv` | 48 | `01aeb8884b82fd21403807c9b7d1c1d4eb2aab4b8e8b9cc9817d85ae8b0a2251` |
| `promociones.csv` | 30 | `3d257f794e3eeae778bbcb2e4a52379d84741caba54ed0675568ae3f7e997874` |
| `proveedores_precios.csv` | 103 | `2f4afa9b693308d42f0636553094be9d86dd0fb99be0fd478969f9f3b88eb703` |

Los CSV conservan UTF-8 con BOM, encabezados y registros de origen. La
verificación en el repositorio se repetirá con `sha256sum data/*` antes de una
carga futura.

## Riesgos y limitaciones

- **Riesgo destructivo del SQL OLTP:** mitigado solo por el volumen nuevo y el
  ciclo de inicialización oficial; no ejecutar sobre un volumen existente.
- **Recursos limitados:** límites de 768 MiB para OLTP/DW y 512 MiB para
  Airflow, sin servicios de aplicación en esta fase. Los límites son una
  configuración propuesta y no han sido probados en ejecución.
- **Colisiones:** la disponibilidad real de los nombres efectivos de red y
  volumen y de los puertos sigue PENDIENTE; debe comprobarse antes de iniciar.
- **Secretos:** no hay credenciales reales versionadas; la seguridad efectiva
  del `.env` local y de Docker queda pendiente de revisión del operador.
- **Compatibilidad:** `postgres:16.15-bookworm` es una etiqueta fija elegida
  para esta entrega; la compatibilidad con Airflow/dbt se debe comprobar cuando se
  incorporen esos componentes.
- **Estado funcional parcial:** la evidencia confirma la infraestructura y las
  verificaciones indicadas, pero no la implementación de las capas posteriores.

## Criterios pendientes

**PENDIENTE:** creación y validación de roles mínimos, implementación de
Airflow, Python ETL y dbt, carga de fuentes adicionales, modelos analíticos,
pruebas de calidad, consultas analíticas y validación funcional del flujo
completo. **RECOMENDADO:** conservar nuevas ejecuciones en `resultados/` con
fecha, alcance y resultados verificables, sin secretos.
