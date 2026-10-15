# Seguridad de datos y control de acceso

## Principio de privilegio mínimo

SG-Food separa la lectura de datos transaccionales, la administración de tablas raw y la ejecución de transformaciones. El aprovisionamiento se define en [`sql/01-provision-roles-oltp.sql`](../sql/01-provision-roles-oltp.sql), [`sql/02-provision-roles-dw.sql`](../sql/02-provision-roles-dw.sql) y [`scripts/provision_roles.py`](../scripts/provision_roles.py).

| Rol | Base | Acceso previsto |
|---|---|---|
| `sgfood_oltp_reader` | `sgfood_oltp` | `CONNECT`, `USAGE` y `SELECT` sobre siete tablas de `oltp_sgfood`; sin modificaciones |
| `sgfood_raw_loader` | `sgfood_dw` | Creación y administración de tablas que escribe en `raw`; sin escritura en `staging`, `intermediate` o `marts` |
| `sgfood_dbt_runner` | `sgfood_dw` | `SELECT` sobre tablas raw; `USAGE` y `CREATE` sobre `staging`, `intermediate` y `marts`; sin modificación de raw |

El acceso de dbt a nuevas tablas creadas por el loader se habilita mediante los privilegios predeterminados de PostgreSQL configurados para el creador de objetos `sgfood_raw_loader`. El motor de dbt no necesita permisos administrativos sobre el origen transaccional.

## Credenciales y configuración

Los secretos se definen únicamente en el archivo local `.env` y se inyectan por variables de entorno. El perfil dbt utiliza `env_var('SGFOOD_DBT_RUNNER_PASSWORD')`; el [perfil de ejemplo](../dbt/profiles.example.yml) no incluye contraseñas reales. No publicar `.env`, logs con valores secretos o comandos que expongan claves en argumentos.

## Aprovisionamiento y comprobación

Tras iniciar PostgreSQL y preparar `.env`, desde `Proyecto1/`:

```bash
python scripts/provision_roles.py --env-file .env oltp
python scripts/provision_roles.py --env-file .env dw
python scripts/provision_roles.py --self-test
```

Los permisos pueden verificarse mediante los scripts [`validar_permisos_oltp.py`](../scripts/validar_permisos_oltp.py) y [`validar_permisos_dw.py`](../scripts/validar_permisos_dw.py), conforme a la documentación de estos scripts y las [evidencias 02](../resultados/02-validacion-permisos-dw.txt) y [03](../resultados/03-validacion-permisos-oltp.txt).

Las pruebas documentadas confirman autenticación de roles, acceso permitido y rechazo de operaciones no autorizadas. Entre los casos relevantes se verificó que el runner lee tablas raw presentes y futuras, mientras que las operaciones de escritura sobre raw se rechazan para ese rol.

## Límites de seguridad

El entorno está orientado a uso local académico y no integra gestión externa de secretos, políticas corporativas de rotación o auditoría centralizada. La existencia de controles de acceso probados no implica una certificación de seguridad de la plataforma. Deben evitarse operaciones destructivas, especialmente en volúmenes persistentes y la base transaccional.
