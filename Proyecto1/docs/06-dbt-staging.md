# Bloque 2B1 — dbt Core y staging

Estado al 13 de octubre de 2026: **staging ejecutado y validado**. La configuración versionable está en `dbt/profiles.example.yml`; el perfil local `dbt/profiles.yml` no se versiona ni se modifica en esta fase.

## Alcance y auditoría

Se revisaron `AGENTS.md`, `docs/00-matriz-requisitos.md`, `docs/01-catalogo-fuentes.md`, `docs/02-arquitectura-y-decisiones.md`, `docs/04-permisos.md`, `docs/05-carga-raw.md`, `sql/03-create-raw.sql`, `requirements-etl.txt`, `compose.yaml` y `.env.example`. La auditoría confirmó Python 3.12.3 local, PostgreSQL `16.15-bookworm` en Compose, el commit previo `2c81a81` y un Git status inicial limpio.

La carga raw está documentada como comprobada: 12 tablas y 8,864 registros reconciliados.

La validación del 13/10/2026 reportó dbt-core `1.11.12`, dbt-postgres `1.10.2`, `pip check` sin conflictos, `dbt debug` aprobado y `dbt parse` aprobado sin advertencias. Se crearon 12 vistas por `sgfood_dbt_runner`; `dbt run` terminó `PASS=12 WARN=0 ERROR=0` y `dbt test` terminó `PASS=41 WARN=0 ERROR=0`.

La validación independiente comprobó `8,864` registros, conteos raw y staging coincidentes, además de propiedad y tipos correctos en las vistas. También se aprobaron 26 pruebas locales Python. Evidencias: [07-dbt-staging-run.txt](../resultados/07-dbt-staging-run.txt), [08-dbt-staging-tests.txt](../resultados/08-dbt-staging-tests.txt) y [09-validacion-staging-independiente.txt](../resultados/09-validacion-staging-independiente.txt).

## Compatibilidad propuesta

`requirements-dbt.txt` fija `dbt-core==1.11.12` y `dbt-postgres==1.10.2`; ambas versiones fueron comprobadas en la ejecución real descrita arriba.

La evidencia operativa de esta entrega está en los resultados enlazados arriba.

## Arquitectura y estructura

```text
dbt/
├── dbt_project.yml
├── profiles.example.yml         # plantilla sin credenciales
├── profiles.yml                 # configuración local ignorada
├── macros/generate_schema_name.sql
├── models/
│   ├── sources.yml              # las 12 tablas raw exactas
│   └── staging/
│       ├── stg_*.sql             # 12 vistas, una por fuente
│       └── schema.yml            # documentación y tests nativos
└── tests/
    ├── source_and_staging_counts.sql
    └── staging_row_counts.sql
```

`dbt_project.yml` configura todas las vistas de este bloque y el schema lógico `staging`. No existen modelos `intermediate` ni `marts`; quedan reservados para fases posteriores. No se construyen dimensiones, hechos, SCD, Airflow, promociones aplicadas ni uniones de devoluciones.

## Sources y modelos

Se declararon exactamente estas fuentes bajo `sgfood_dw.raw`: `oltp_sucursal`, `oltp_categoria`, `oltp_marca`, `oltp_producto`, `oltp_cliente`, `oltp_venta`, `oltp_venta_detalle`, `csv_inventario_bodega`, `csv_devoluciones`, `csv_metas_ventas`, `csv_promociones` y `csv_proveedores_precios`. Cada una tiene un modelo `stg_` con `source('raw', ...)`, proyección explícita y columnas técnicas `_etl_*` pertinentes.

Los modelos OLTP conservan los tipos ya definidos por `sql/03-create-raw.sql`. Los CSV parten de texto y convierten fechas, enteros y numéricos mediante `NULLIF(btrim(valor), '')::tipo`: espacios exteriores se quitan, una cadena vacía se vuelve `NULL`, y un valor no vacío con formato inválido produce error de PostgreSQL cuando dbt se ejecute. No hay conversión silenciosa. La representación `periodo` de metas se conserva como `date`; debe confirmarse en ejecución contra el formato real de la fuente.

Las claves, granularidades y columnas de negocio se documentan en `models/staging/schema.yml`. El `subtotal` de ventas se conserva; no se reemplaza por una fórmula. Las promociones no se vinculan con ventas. Las devoluciones permanecen separadas. `fecha_vencimiento` no se interpreta como vencida sin compararla con su `fecha_corte`.

## Schemas, perfiles y permisos

`profiles.example.yml` refleja el destino local `dev` validado: base `sgfood_dw`, esquema `staging`, usuario `sgfood_dbt_runner`, host por `DBT_HOST`, puerto entero por `DBT_PORT | int` y contraseña exclusivamente por `SGFOOD_DBT_RUNNER_PASSWORD`. No contiene credenciales reales. El perfil local `profiles.yml` no se modifica.

Para no sobrescribir configuraciones locales, desde `Proyecto1` copie la plantilla solo si no existe un perfil local:

```bash
test -e dbt/profiles.yml || cp dbt/profiles.example.yml dbt/profiles.yml
```

Si ya existe, consérvelo y compare manualmente. Antes de ejecutar dbt, suministre las variables al proceso sin imprimir la contraseña:

```bash
export DBT_HOST=127.0.0.1
export DBT_PORT=15434
export SGFOOD_DBT_RUNNER_PASSWORD='[introducir fuera de la documentación]'
```

No se asume que dbt cargue automáticamente `Proyecto1/.env`; las variables deben estar disponibles en el entorno del proceso. La contraseña se debe suministrar sin imprimir ni versionar contraseñas.

El macro `generate_schema_name` solo permite `staging`, `intermediate` y `marts`, y devuelve el nombre solicitado sin anteponer `target.schema`. Así se evita generar `staging_staging` o `staging_marts`. El target/schema de perfiles es una configuración de conexión, no una licencia para escribir en `raw`. El permiso efectivo depende del PostgreSQL real y debe comprobarse después con el rol runner; este bloque no cambia permisos.

Limitación local: el perfil `dev` asume el puerto publicado local `15434` por defecto; en otro entorno deben exportarse `DBT_HOST` y `DBT_PORT`. En ningún entorno se admite configurar un usuario administrador desde el archivo.

## Tests preparados

- `not_null` y `unique` para claves naturales; también `unique` para `sku`.
- `relationships` para las FK conocidas entre productos, ventas, detalles y fuentes CSV relacionadas.
- Conversión explícita de tipos en SQL; valores no convertibles fallarán al materializar el modelo.
- `staging_row_counts.sql`: reconciliación dinámica activa; verifica que cada staging conserve el conteo de su fuente y no multiplique registros.
- `source_and_staging_counts.sql`: fotografía académica opcional de 8,864 filas, deshabilitada por defecto mediante `var('enable_academic_snapshot', false)`. Se habilita explícitamente con `--vars '{"enable_academic_snapshot": true}'`; conserva los conteos originales (6, 8, 10, 80, 250, 1,200, 3,209, 3,840, 80, 48, 30 y 103) sin bloquear cargas futuras válidas.
- `stg_csv_metas_ventas_periodo_format.sql`: detecta valores no vacíos que no cumplan `YYYY-MM` con mes `01`–`12`.
- Pruebas singulares de no nulidad y unicidad conjunta para las claves de inventario, metas y proveedores/precios. Solo devuelven filas que violan la clave compuesta; no hacen únicos los componentes individuales.

No se agregaron `accepted_values` para estados, canales, métodos o motivos porque el catálogo auditado no aporta un dominio aprobado. Los dominios y reglas de negocio quedan **PENDIENTES** de decisión y ejecución en PostgreSQL.

## Reproducibilidad

La plantilla permite reproducir la configuración en una clonación nueva sin depender de credenciales locales hasta que el operador configure sus variables de entorno. Las ejecuciones comprobadas y sus resultados se conservan en los tres archivos enlazados al inicio.

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile tests/test_dbt_staging_contract.py
```

Las pruebas estáticas verifican fuentes, modelos, seguridad, esquemas, claves, períodos y conteos sin depender de `profiles.yml` ni conectarse a PostgreSQL.

## Riesgos y pendientes

- `intermediate`: **PENDIENTE**.
- `marts`: **PENDIENTE**.
- Airflow: **PENDIENTE**.
- Validación integral del ELT: **PENDIENTE**.
- La normalización mensual requiere que el formato fuente sea `YYYY-MM`; el test singular detecta incumplimientos.
- La fotografía académica es opcional; la reconciliación dinámica permanece activa para no congelar la cantidad de filas.
- Deben definirse dominios comerciales y controles de rangos; no se inventaron en staging.
