#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

PROJECT_ID="${P2_PROJECT_ID:-}"
DATASET="${P2_DATASET:-ss2_proyecto2_g6}"
ACTION="${1:-}"
MAX_BYTES="${P2_MAX_BYTES:-10000000000}"

if [[ ! "$PROJECT_ID" =~ ^[a-z][a-z0-9-]{4,62}$ ]]; then
  echo 'ERROR: define P2_PROJECT_ID con el ID de GCP aprobado.' >&2; exit 2
fi
if [[ ! "$DATASET" =~ ^[a-zA-Z_][a-zA-Z_0-9]{0,100}$ ]]; then
  echo 'ERROR: nombre de dataset inválido.' >&2; exit 2
fi
if [[ ! "$MAX_BYTES" =~ ^[0-9]+$ ]]; then echo 'ERROR: P2_MAX_BYTES inválido' >&2;exit 2;fi

mkdir -p evidencias/logs
STAMP="$(date +%Y%m%d_%H%M%S)"
render_sql() {
 sed -e "s/__PROJECT_ID__/${PROJECT_ID}/g"      -e "s/__DATASET__/${DATASET}/g" "$1"
}
verify_auth() {
 if [[ "${P2_AUTORIZO_GCP:-NO}" != "SI" ]]; then
   echo 'BLOQUEADO. Confirma facturación y autorización, exporta P2_AUTORIZO_GCP=SI.' >&2
   exit 3
 fi
}
# Evitar costos duplicados por CREATE OR REPLACE ejecutado accidentalmente.
# P2_FORZAR_REEMPLAZO=SI solamente cuando se desee reconstruir deliberadamente.
no_repetir() {
  local tipo="$1" nombre="$2"
  [[ "${P2_FORZAR_REEMPLAZO:-NO}" = "SI" ]] && return 0
  local flag=()
  if [[ "$tipo" = "modelo" ]]; then flag=(--model); fi
  if bq --project_id="$PROJECT_ID" show "${flag[@]}" "$PROJECT_ID:$DATASET.$nombre" >/dev/null 2>&1; then
    echo "DETENIDO: ya existe $tipo $nombre. Para evitar costo duplicado NO se sobrescribe." >&2
    echo "Si es imprescindible rehacerlo, usa P2_FORZAR_REEMPLAZO=SI con criterio." >&2
    exit 4
  fi
}
query() {
 local key="$1";local path="$2"
 echo "== Ejecutando $key ($PROJECT_ID:$DATASET) =="
 # Para cada query activar máximo de bytes facturables de análisis.
 render_sql "$path" | bq --project_id="$PROJECT_ID" --location=US query       --use_legacy_sql=false --maximum_bytes_billed="$MAX_BYTES"       --format=prettyjson --quiet 2>&1 | tee "evidencias/logs/${STAMP}_${key}.log"
}
benchmark() {
 local key="$1"; local path="$2"
 echo "== Benchmark $key sin cache =="
 render_sql "$path" | bq --project_id="$PROJECT_ID" --location=US query       --use_legacy_sql=false --nouse_cache --maximum_bytes_billed="$MAX_BYTES"       --format=prettyjson --quiet 2>&1 | tee "evidencias/logs/${STAMP}_${key}.log"
}
case "$ACTION" in
  preflight)
    echo "Proyecto: $PROJECT_ID; Dataset previsto: $DATASET; region: US"
    gcloud projects describe "$PROJECT_ID" --format='table(projectId,name,lifecycleState)'
    gcloud billing projects describe "$PROJECT_ID" --format='json(billingEnabled)'
    bq show --format=prettyjson bigquery-public-data:new_york_taxi_trips.tlc_yellow_trips_2022        | python3 -c 'import sys,json;d=json.load(sys.stdin); print("Filas publicas:",d.get("numRows"),"ubicacion:",d.get("location"))'
    bq --project_id="$PROJECT_ID" --location=US query --use_legacy_sql=false --dry_run        --format=prettyjson 'SELECT COUNT(*),AVG(trip_distance) FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`'        | python3 -c 'import sys,json;d=json.load(sys.stdin);print("Bytes estimados:",d.get("statistics",{}).get("totalBytesProcessed"))'
  ;;
  crear-dataset)
    verify_auth
    if bq --project_id="$PROJECT_ID" show "$PROJECT_ID:$DATASET" >/dev/null 2>&1; then
      echo 'Dataset ya existe; no se modificó.'
    else
      bq --project_id="$PROJECT_ID" mk --dataset --location=US "$PROJECT_ID:$DATASET"
    fi
  ;;
  calidad) verify_auth;query calidad sql/01_exploracion/01_calidad.sql ;;
  exploracion) verify_auth;query exploracion sql/01_exploracion/02_exploracion.sql ;;
  crear-tablas)
    verify_auth
    no_repetir tabla viajes_base
    no_repetir tabla viajes_optimizada
    query base sql/02_transformaciones/01_base_comparable.sql
    query optimizada sql/03_optimizacion/01_particionado_clustering.sql
    query igualdad sql/03_optimizacion/02_prueba_igualdad.sql
  ;;
  benchmark)
    verify_auth
    if [[ "${P2_FORZAR_REEMPLAZO:-NO}" != SI ]] && find evidencias/logs -maxdepth 1 -name "*_estadisticas.log" -print -quit | grep -q .; then
      echo "DETENIDO: ya existe evidencia de benchmark. No repetir por costo." >&2; exit 4
    fi
    benchmark base sql/03_optimizacion/03_benchmark_base.sql
    benchmark optimizada sql/03_optimizacion/04_benchmark_optimizada.sql
    query estadisticas sql/03_optimizacion/05_estadisticas_benchmark.sql
  ;;
  datos-ml)
    verify_auth
    no_repetir tabla datos_ml
    query muestra_ml sql/04_bigquery_ml/01_crear_muestra.sql
    query splits sql/04_bigquery_ml/02_verificar_splits.sql
  ;;
  entrenar-lineal)
    verify_auth
    [[ "${P2_AUTORIZO_ENTRENAMIENTO:-NO}" = SI ]] || { echo 'Falta P2_AUTORIZO_ENTRENAMIENTO=SI';exit 3; }
    no_repetir modelo modelo_lineal
    query modelo_lineal sql/04_bigquery_ml/03_entrenar_lineal.sql
  ;;
  entrenar-arbol)
    [[ "${P2_AUTORIZO_ARBOL_EXTERNO:-NO}" == SI ]] || { echo "BLOQUEADO: arbol externo falló 3 veces. Elige entrenar-logistico para evitar mas costos." >&2; exit 9; }
    verify_auth
    [[ "${P2_AUTORIZO_ENTRENAMIENTO:-NO}" = SI ]] || { echo 'Falta P2_AUTORIZO_ENTRENAMIENTO=SI';exit 3; }
    no_repetir modelo modelo_arbol
    query modelo_arbol sql/04_bigquery_ml/04_entrenar_arbol.sql
  ;;
  entrenar-logistico)
    verify_auth
    [[ "${P2_AUTORIZO_ENTRENAMIENTO:-NO}" = SI ]] || { echo 'Falta P2_AUTORIZO_ENTRENAMIENTO=SI';exit 3; }
    no_repetir modelo modelo_logistico
    query modelo_logistico sql/04_bigquery_ml/04_entrenar_logistico.sql
  ;;
  evaluar)
    verify_auth
    no_repetir tabla metricas_modelos
    no_repetir tabla matriz_confusion_logistica
    query evaluacion sql/04_bigquery_ml/05_evaluacion.sql
  ;;
  predecir) verify_auth;no_repetir tabla predicciones_lineal;no_repetir tabla predicciones_logistica;no_repetir tabla predicciones_comparadas;no_repetir tabla metricas_comparacion_clasificacion;query predicciones sql/04_bigquery_ml/06_predicciones.sql ;;
  dashboard) verify_auth;no_repetir tabla resumen_eda_dashboard;query vistas_dashboard sql/05_dashboard/01_tablas_vistas.sql ;;
  *) echo 'Uso: bash ejecutar.sh {preflight|crear-dataset|calidad|exploracion|crear-tablas|benchmark|datos-ml|entrenar-lineal|entrenar-arbol|evaluar|predecir|dashboard|entrenar-logistico}' >&2;exit 2 ;;
esac
