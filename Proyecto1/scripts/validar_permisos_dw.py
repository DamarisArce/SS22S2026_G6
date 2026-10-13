from pathlib import Path
import runpy
import secrets
import psycopg
from psycopg import sql

m = runpy.run_path('Proyecto1/scripts/provision_roles.py', run_name='dw_acl_tests')
m['load_dotenv'](Path('Proyecto1/.env'))
base = m['connection_values']('dw')
if (base['dbname'], base['host'], int(base['port'])) != ('sgfood_dw', '127.0.0.1', 15434):
    raise SystemExit('ERROR: destino DW inesperado')

probe = '__sgfood_acl_' + secrets.token_hex(8)

def connect_role(name, env_key):
    p = base.copy()
    p.update(user=name, password=m['required'](env_key), connect_timeout=5)
    return psycopg.connect(**p)

def assert_rejected(cur, statement, label):
    cur.execute('SAVEPOINT sgfood_acl_savepoint')
    try:
        cur.execute(statement)
    except psycopg.errors.InsufficientPrivilege:
        cur.execute('ROLLBACK TO SAVEPOINT sgfood_acl_savepoint')
        cur.execute('RELEASE SAVEPOINT sgfood_acl_savepoint')
        print('OK: denegado ' + label)
        return
    except Exception:
        cur.execute('ROLLBACK TO SAVEPOINT sgfood_acl_savepoint')
        cur.execute('RELEASE SAVEPOINT sgfood_acl_savepoint')
        raise
    cur.execute('ROLLBACK TO SAVEPOINT sgfood_acl_savepoint')
    cur.execute('RELEASE SAVEPOINT sgfood_acl_savepoint')
    raise AssertionError('ERROR: operación inesperadamente permitida: ' + label)

# Acceso real del cargador. Todo cambio se revierte.
with connect_role('sgfood_raw_loader', 'SGFOOD_RAW_LOADER_PASSWORD') as conn:
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL('CREATE TABLE {} (probe_id integer)').format(sql.Identifier('raw', probe)))
            cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier('raw', probe)))
            assert cur.fetchone()[0] == 0
            print('OK: raw_loader puede crear y leer en raw')
            for schema in ('staging', 'intermediate', 'marts'):
                assert_rejected(cur, sql.SQL('CREATE TABLE {} (probe_id integer)').format(
                    sql.Identifier(schema, probe)), f'raw_loader CREATE en {schema}')
    finally:
        conn.rollback()

# Acceso real de dbt. Todo cambio se revierte.
with connect_role('sgfood_dbt_runner', 'SGFOOD_DBT_RUNNER_PASSWORD') as conn:
    try:
        with conn.cursor() as cur:
            for schema in ('staging', 'intermediate', 'marts'):
                cur.execute(sql.SQL('CREATE TABLE {} (probe_id integer)').format(
                    sql.Identifier(schema, probe)))
                print(f'OK: dbt_runner puede crear en {schema}')
            assert_rejected(cur, sql.SQL('CREATE TABLE {} (probe_id integer)').format(
                sql.Identifier('raw', probe)), 'dbt_runner CREATE en raw')
    finally:
        conn.rollback()

# Comprobar ALTER DEFAULT PRIVILEGES: misma transacción, dos identidades
# activadas por el administrador. Ningún objeto queda persistido.
with psycopg.connect(**base, connect_timeout=5) as conn:
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT current_database(), current_user')
            if cur.fetchone() != ('sgfood_dw', m['required']('POSTGRES_DW_USER')):
                raise RuntimeError('ERROR: identidad administrativa inesperada')
            cur.execute('SELECT to_regclass(%s)', ('raw.' + probe,))
            if cur.fetchone()[0] is not None:
                raise RuntimeError('ERROR: el nombre de prueba ya existe')
            cur.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier('sgfood_raw_loader')))
            cur.execute(sql.SQL('CREATE TABLE {} (probe_id integer)').format(sql.Identifier('raw', probe)))
            cur.execute('SELECT current_user')
            assert cur.fetchone()[0] == 'sgfood_raw_loader'
            cur.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier('sgfood_dbt_runner')))
            cur.execute('SELECT current_user')
            assert cur.fetchone()[0] == 'sgfood_dbt_runner'
            cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier('raw', probe)))
            assert cur.fetchone()[0] == 0
            cur.execute('SELECT has_table_privilege(current_user,%s,\'SELECT\'), '
                        'has_table_privilege(current_user,%s,\'INSERT\'), '
                        'has_table_privilege(current_user,%s,\'UPDATE\'), '
                        'has_table_privilege(current_user,%s,\'DELETE\')',
                        ('raw.'+probe,)*4)
            assert cur.fetchone() == (True, False, False, False)
            print('OK: dbt_runner puede leer una tabla raw futura')
            for op, statement in {
                'INSERT': sql.SQL('INSERT INTO {} (probe_id) SELECT 1 WHERE FALSE').format(sql.Identifier('raw', probe)),
                'UPDATE': sql.SQL('UPDATE {} SET probe_id = 2 WHERE FALSE').format(sql.Identifier('raw', probe)),
                'DELETE': sql.SQL('DELETE FROM {} WHERE FALSE').format(sql.Identifier('raw', probe)),
            }.items():
                assert_rejected(cur, statement, f'dbt_runner {op} sobre raw')
    finally:
        conn.rollback()

with psycopg.connect(**base, connect_timeout=5) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace '
                    'WHERE c.relname=%s AND n.nspname=ANY(%s)',
                    (probe, ['raw','staging','intermediate','marts']))
        assert cur.fetchone()[0] == 0, 'ERROR: quedó una tabla de prueba'
print('OK: ninguna tabla de prueba persistió')
print('VALIDACIÓN FUNCIONAL DE PERMISOS DW APROBADA')
