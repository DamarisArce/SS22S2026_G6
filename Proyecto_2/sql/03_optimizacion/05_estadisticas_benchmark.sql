-- Historial de jobs del propio usuario: bytes/tiempos, sin caché.
-- Si no aparecen jobs, revisar permisos para INFORMATION_SCHEMA.JOBS_BY_USER.
SELECT
  creation_time, job_id,
  CASE WHEN REGEXP_CONTAINS(query, r'P2_BENCH_BASE') THEN 'BASE' ELSE 'OPTIMIZADA' END AS variante,
  total_bytes_processed,
  total_bytes_billed,
  ROUND(total_bytes_processed/POW(1024,3),3) AS gib_procesados,
  TIMESTAMP_DIFF(end_time,start_time,MILLISECOND) AS milisegundos,
  total_slot_ms,
  cache_hit,
  error_result.message AS error
FROM `__PROJECT_ID__.region-us.INFORMATION_SCHEMA.JOBS_BY_USER`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 DAY)
  AND (REGEXP_CONTAINS(query, r'P2_BENCH_BASE') OR REGEXP_CONTAINS(query, r'P2_BENCH_OPT'))
  AND NOT REGEXP_CONTAINS(query, r'INFORMATION_SCHEMA')
  AND statement_type='SELECT'
ORDER BY creation_time DESC LIMIT 20;
