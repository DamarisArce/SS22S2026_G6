# Bloque 1A — Roles y permisos mínimos

Estado: **PREPARADO; no ejecutado en esta tarea**.

Este documento define el aprovisionamiento reproducible para los roles de
lectura OLTP y de carga/transformación DW. La configuración se basa en
`compose.yaml`, `.env.example`, los schemas definidos por la inicialización del
DW y las siete tablas OLTP verificadas en
`resultados/01-validacion-postgresql.txt`.

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

## Archivos preparados

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

Los scripts no contienen contraseñas. El wrapper no elimina roles, bases,
schemas ni tablas; las operaciones son repetibles y se ejecutan dentro de una
transacción por base. Antes de cualquier modificación verifica la base, el
administrador esperado, los schemas, las tablas OLTP y las membresías de los
roles objetivo. Comprueba tanto si un rol objetivo pertenece a otro rol como si
otro rol pertenece a un rol objetivo. Si encuentra cualquiera de esas
membresías preexistentes, se detiene sin revocarla ni alterar otros roles. No
dependen de `initdb` ni de que el volumen sea nuevo.

## Procedimiento propuesto

**PENDIENTE de ejecución:**

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

No ejecutar todavía este procedimiento como parte de esta tarea. No se
ejecutaron SQL, conexiones autenticadas ni cambios en bases existentes.

## Verificaciones preparadas

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

### Autenticación y autorización reales

Estas pruebas deben ejecutarse después del aprovisionamiento, usando cada
contraseña desde un mecanismo seguro y no desde argumentos visibles. No se han
ejecutado y sus resultados deben guardarse sin secretos.

- Conectar a `sgfood_oltp` como `sgfood_oltp_reader` y consultar una de las
  siete tablas: esta es una autorización positiva. Probar cada `INSERT`,
  `UPDATE`, `DELETE`, `TRUNCATE` y `CREATE` en transacciones independientes o
  usando `SAVEPOINT`; cada operación debe ser rechazada sin dejar cambios.
- Conectar a `sgfood_dw` como `sgfood_raw_loader`, ejecutar
  `BEGIN; CREATE TABLE raw.__acl_probe_loader (probe_id integer); ROLLBACK;`: la creación en
  `raw` debe ser positiva y el `ROLLBACK` debe dejar la base sin la tabla.
  Ejecutar la creación equivalente en `marts` en otra transacción; debe ser
  rechazada.
- Conectar a `sgfood_dw` como `sgfood_dbt_runner`, leer una tabla de `raw` y
  ejecutar `BEGIN; CREATE TABLE marts.__acl_probe_dbt (probe_id integer); ROLLBACK;`: ambas
  autorizaciones positivas deben funcionar sin persistir la tabla. Probar
  `INSERT`, `UPDATE`, `DELETE` y `TRUNCATE` sobre una tabla `raw` en
  transacciones independientes; deben ser rechazados.
- Crear posteriormente una tabla como `sgfood_raw_loader` en `raw`, verificar
  que `sgfood_dbt_runner` puede leerla y después eliminar la tabla solo en un
  entorno de prueba autorizado. Esta prueba demuestra el
  `ALTER DEFAULT PRIVILEGES`; no debe ejecutarse sobre datos operativos sin
  aprobación.

El resultado de estas pruebas reales debe distinguirse de las consultas de
catálogo y marcarse como **PENDIENTE** hasta contar con evidencia ejecutada.

La prueba unitaria local del formato SCRAM, sin conexión a PostgreSQL, se
prepara y ejecuta con:

```bash
python3 scripts/provision_roles.py --self-test
```

Debe verificar el prefijo `SCRAM-SHA-256`, las iteraciones, los tamaños de
salt/verificadores y que la contraseña correcta valida mientras una incorrecta
no valida. Esta prueba no crea roles ni modifica bases.

## Riesgos pendientes

- Las contraseñas de los tres roles todavía deben generarse localmente y
  protegerse fuera del repositorio.
- El aprovisionamiento requiere conectividad y credenciales administrativas
  correctas para cada base; eso no autoriza modificar otras bases o roles.
- No se ha demostrado aún la autorización efectiva mediante conexiones reales.
- Los privilegios de objetos existentes creados por propietarios distintos no se
  sustituyen automáticamente por los privilegios predeterminados futuros; deben
  revisarse explícitamente si el DW ya contiene tablas.
