# Bloque 1A — Roles y permisos mínimos

Estado al **13 de octubre de 2026**: **COMPROBADO en ejecución** para el
aprovisionamiento y la validación funcional de los roles descritos.

Este documento define el aprovisionamiento reproducible para los roles de
lectura OLTP y de carga/transformación DW. La configuración se basa en
`compose.yaml`, `.env.example`, los schemas definidos por la inicialización del
DW y las siete tablas OLTP verificadas en
`resultados/01-validacion-postgresql.txt`.
Los resultados de seguridad se conservan en
`resultados/02-validacion-permisos-dw.txt` y
`resultados/03-validacion-permisos-oltp.txt`.

## Roles y decisiones de privilegios

| Rol | Base | Privilegios permitidos | Privilegios excluidos |
|---|---|---|---|
| `sgfood_oltp_reader` | `sgfood_oltp` | `CONNECT`, `USAGE` en `oltp_sgfood`, `SELECT` en `sucursal`, `categoria`, `marca`, `producto`, `cliente`, `venta`, `venta_detalle` | administración, creación, inserción, actualización, borrado y truncado |
| `sgfood_raw_loader` | `sgfood_dw` | `CONNECT`, `USAGE` y `CREATE` en `raw`; propiedad operativa de las tablas que cree | escritura en `staging`, `intermediate` y `marts` |
| `sgfood_dbt_runner` | `sgfood_dw` | `CONNECT`; `USAGE` y `SELECT` en `raw`; `USAGE` y `CREATE` en `staging`, `intermediate` y `marts` | modificación de tablas `raw` |

Los tres roles se configuran como `LOGIN`, `NOSUPERUSER`, `NOCREATEDB`,
`NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS` y `NOINHERIT`. No se otorga
`ALL PRIVILEGES` como concesión y no se modifican roles ajenos ni otras bases.

La revocación de `CONNECT` y `TEMPORARY` sobre cada rol no elimina los
privilegios que PostgreSQL pueda heredar desde `PUBLIC`. Esta tarea no ejecuta
`REVOKE` sobre `PUBLIC`; por tanto, la efectividad final de esos dos privilegios
debe comprobarse en el catálogo y mediante conexión real.

El rol `sgfood_raw_loader` es el creador explícito de los objetos futuros en
`raw`. Por eso `02-provision-roles-dw.sql` configura:

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE sgfood_raw_loader IN SCHEMA raw
GRANT SELECT ON TABLES TO sgfood_dbt_runner;
```

Esto permite que dbt lea tablas nuevas creadas por el loader, sin conceder a
dbt permisos de escritura sobre `raw`. Los privilegios predeterminados no
afectan objetos creados por otro propietario.

## Archivos de aprovisionamiento y validación

- `sql/01-provision-roles-oltp.sql`: crea/configura el reader y concede acceso
  únicamente a las siete tablas OLTP.
- `sql/02-provision-roles-dw.sql`: crea/configura loader y runner, permisos por
  schema y privilegios predeterminados para tablas futuras de `raw`.
- `scripts/provision_roles.py`: carga `.env` local sin sobrescribir variables
  exportadas, valida identidad/base/schemas/tablas/membresías antes de modificar,
  conecta con las credenciales administrativas existentes y genera verificadores
  SCRAM-SHA-256 en el cliente. PostgreSQL recibe el verificador, nunca la
  contraseña original. No acepta contraseñas en argumentos ni imprime
  contraseñas o verificadores.
- `.env.example`: agrega tres marcadores de contraseñas distintas para los
  roles, sin modificar las credenciales administrativas existentes.
- `scripts/validar_permisos_oltp.py`: valida autenticación real del lector,
  atributos restringidos, lectura de las siete tablas y rechazos de escritura
  y creación.
- `scripts/validar_permisos_dw.py`: valida autenticación real del loader y del
  runner, aislamiento por schema, lectura de tablas `raw` futuras y rechazos
  de modificación.

Los scripts no contienen contraseñas. El wrapper no elimina roles, bases,
schemas ni tablas; las operaciones son repetibles y se ejecutan dentro de una
transacción por base. Antes de cualquier modificación verifica la base, el
administrador esperado, los schemas, las tablas OLTP y las membresías de los
roles objetivo. Comprueba tanto si un rol objetivo pertenece a otro rol como si
otro rol pertenece a un rol objetivo. Si encuentra cualquiera de esas
membresías preexistentes, se detiene sin revocarla ni alterar otros roles. No
dependen de `initdb` ni de que el volumen sea nuevo.

## Procedimiento de aprovisionamiento y validación

El aprovisionamiento de los tres roles fue realizado. Las rutas de los
validadores se expresan desde la raíz de `Proyecto1`:

```bash
python3 scripts/validar_permisos_oltp.py
python3 scripts/validar_permisos_dw.py
```

Las evidencias de esas ejecuciones son, respectivamente,
`resultados/03-validacion-permisos-oltp.txt` y
`resultados/02-validacion-permisos-dw.txt`.

El siguiente procedimiento conserva la guía para reproducir el
aprovisionamiento en un entorno autorizado:

1. `Proyecto1/.env` ya existe y contiene las credenciales administrativas
   operativas. No sobrescribirlo, reemplazarlo ni copiar `.env.example` sobre
   él. Añadir únicamente estas tres variables nuevas, si aún no existen, con
   valores locales distintos y fuera de Git:

   ```text
   SGFOOD_OLTP_READER_PASSWORD=<secreto-único>
   SGFOOD_RAW_LOADER_PASSWORD=<secreto-único>
   SGFOOD_DBT_RUNNER_PASSWORD=<secreto-único>
   ```

2. Confirmar que las bases ya están disponibles y que el usuario administrativo
   de cada base es el previsto en `.env`. No sobrescribir `.env` real.
3. Ejecutar desde la raíz del proyecto, sin pasar contraseñas como argumentos:

   ```bash
   python3 scripts/provision_roles.py oltp
   python3 scripts/provision_roles.py dw
   ```

   El script usa `127.0.0.1` y los puertos `POSTGRES_OLTP_HOST_PORT`/
   `POSTGRES_DW_HOST_PORT` por defecto. Para otro entorno, definir
   `POSTGRES_OLTP_HOST` o `POSTGRES_DW_HOST` en el entorno local, sin registrar
   secretos.
4. Revisar únicamente la salida de estado de roles; no registrar el contenido
   de `.env` ni las contraseñas.

El preflight fija `sgfood_oltp` para `oltp` y `sgfood_dw` para `dw`; falla si la
base conectada o la variable correspondiente de `.env` no coincide con ese
nombre, si la conexión no corresponde al administrador superusuario esperado,
si faltan schemas o tablas requeridos, o si existe una membresía en cualquiera
de los dos sentidos para un rol objetivo. El aprovisionamiento no continúa en
ninguno de esos casos.

La ejecución documentada de esta tarea no modifica los scripts de
aprovisionamiento ni las credenciales locales.

## Verificaciones y resultados

### Catálogo, sin autenticación de los roles

Ejecutar como administrador de cada base para revisar el catálogo, sin afirmar
que estas consultas hayan sido ejecutadas:

```sql
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname IN (
    'sgfood_oltp_reader', 'sgfood_raw_loader', 'sgfood_dbt_runner'
)
ORDER BY rolname;
```

Verificar los permisos efectivos y los schemas:

```sql
SELECT has_database_privilege('sgfood_oltp_reader', 'sgfood_oltp', 'CONNECT'),
       has_schema_privilege('sgfood_oltp_reader', 'oltp_sgfood', 'USAGE'),
       has_table_privilege('sgfood_oltp_reader',
                           'oltp_sgfood.venta', 'SELECT'),
       has_table_privilege('sgfood_oltp_reader',
                           'oltp_sgfood.venta', 'INSERT');

SELECT has_schema_privilege('sgfood_raw_loader', 'raw', 'CREATE'),
       has_schema_privilege('sgfood_raw_loader', 'marts', 'CREATE'),
       has_schema_privilege('sgfood_dbt_runner', 'raw', 'USAGE'),
       has_table_privilege('sgfood_dbt_runner', 'raw.<tabla_existente>', 'SELECT');
```

Sustituir `<tabla_existente>` por una tabla real de `raw` obtenida del catálogo.
Estas son verificaciones de catálogo; no demuestran que una contraseña permita
autenticarse.

Comprobar el privilegio predeterminado del propietario correcto:

```sql
SELECT owner.rolname AS owner_role,
       namespace.nspname AS schema_name,
       defaults.defaclobjtype,
       defaults.defaclacl
FROM pg_default_acl AS defaults
JOIN pg_roles AS owner ON owner.oid = defaults.defaclrole
JOIN pg_namespace AS namespace ON namespace.oid = defaults.defaclnamespace
WHERE owner.rolname = 'sgfood_raw_loader'
  AND namespace.nspname = 'raw'
  AND defaults.defaclobjtype = 'r';
```

### Autenticación y autorización reales — 13/10/2026

Estas pruebas se ejecutaron después del aprovisionamiento, usando cada
contraseña desde un mecanismo seguro y sin registrarla en las evidencias.

- **COMPROBADO:** `sgfood_oltp_reader` se autenticó, consultó las siete tablas
  y obtuvo 4763 registros. `INSERT`, `UPDATE`, `DELETE` y `CREATE` fueron
  rechazados efectivamente.
- **COMPROBADO:** `sgfood_raw_loader` se autenticó y creó una tabla de prueba
  en `raw`; `CREATE` fue rechazado en `staging`, `intermediate` y `marts`.
- **COMPROBADO:** `sgfood_dbt_runner` se autenticó y creó tablas de prueba en
  `staging`, `intermediate` y `marts`; `CREATE` fue rechazado en `raw`.
- **COMPROBADO:** `sgfood_dbt_runner` leyó una tabla futura creada en `raw` por
  `sgfood_raw_loader`; `INSERT`, `UPDATE` y `DELETE` sobre ella fueron
  rechazados.
- Se creó una tabla de prueba como `sgfood_raw_loader` en `raw`, se verificó
  que `sgfood_dbt_runner` puede leerla y después eliminar la tabla solo en un
  entorno de prueba autorizado. La prueba demuestra el
  `ALTER DEFAULT PRIVILEGES`; las pruebas del DW se revirtieron y no dejaron
  tablas de prueba.

**COMPROBADO:** la validación OLTP aprobó autenticación, atributos
restringidos, lectura de 4763 registros y rechazo efectivo de `INSERT`,
`UPDATE`, `DELETE` y `CREATE`. La validación DW aprobó las autorizaciones y
rechazos descritos arriba, incluida la lectura de una tabla `raw` futura.

La prueba unitaria local del formato SCRAM, sin conexión a PostgreSQL, se
prepara y ejecuta con:

```bash
python3 scripts/provision_roles.py --self-test
```

Debe verificar el prefijo `SCRAM-SHA-256`, las iteraciones, los tamaños de
salt/verificadores y que la contraseña correcta valida mientras una incorrecta
no valida. Esta prueba no crea roles ni modifica bases.

## Riesgos y límites pendientes

- Las contraseñas de los tres roles todavía deben generarse localmente y
  protegerse fuera del repositorio.
- El aprovisionamiento requiere conectividad y credenciales administrativas
  correctas para cada base; eso no autoriza modificar otras bases o roles.
- La observación sobre `PUBLIC` se mantiene: la revocación de `CONNECT` y
  `TEMPORARY` sobre cada rol no elimina los privilegios que PostgreSQL pueda
  heredar desde `PUBLIC`. Esta tarea no ejecuta `REVOKE` sobre `PUBLIC`; por
  tanto, los límites de esos privilegios predeterminados deben seguir
  comprobándose en el catálogo y mediante conexión real cuando corresponda.
- Los privilegios de objetos existentes creados por propietarios distintos no se
  sustituyen automáticamente por los privilegios predeterminados futuros; deben
  revisarse explícitamente si el DW ya contiene tablas.
