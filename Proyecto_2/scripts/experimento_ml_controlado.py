#!/usr/bin/env python3
"""Auditoría y experimentos BQML incrementales; el modo predeterminado no entrena."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
SQL = BASE / "sql" / "04_bigquery_ml"
PROJECT = "ss2-p2-g6-2026-nc-1026"
DATASET = "ss2_proyecto2_g6"
LOCATION = "US"
MODELS = {
    "custom": ("modelo_lineal_custom_l2_1", "07_lineal_custom_l2_1.sql"),
    "seq": ("modelo_lineal_seq_eval20", "08_lineal_seq_eval20.sql"),
}
REQUIRED = {"pickup_date", "fecha_orden", "tarifa", "distancia_millas", "pasajeros",
            "hora_utc", "dia_semana_utc", "mes_utc", "proveedor", "origen", "destino",
            "es_validacion"}


def cmd(args, stdin=None, check=True):
    p = subprocess.run(args, input=stdin, text=True, capture_output=True)
    if check and p.returncode:
        print(p.stdout, file=sys.stderr)
        print(p.stderr, file=sys.stderr)
        raise SystemExit(f"ERROR: bq devolvió código {p.returncode}. No se ejecutan pasos posteriores.")
    return p


def bq(*args, stdin=None, check=True):
    return cmd(["bq", f"--project_id={PROJECT}", *args], stdin=stdin, check=check)


def render(name):
    sql = (SQL / name).read_text(encoding="utf-8")
    return sql.replace("__PROJECT_ID__", PROJECT).replace("__DATASET__", DATASET)


def listar_modelos():
    """Consulta la lista del dataset; un modelo ausente no es un error de IAM."""
    result = bq("ls", "--models", "--format=prettyjson", f"{PROJECT}:{DATASET}", check=False)
    if result.returncode:
        detalle = (result.stderr + "\n" + result.stdout).strip()
        raise SystemExit(f"ERROR: no se pudo listar los modelos del dataset: {detalle[:1000]}")
    try:
        datos = json.loads(result.stdout.strip() or "[]")
    except ValueError as exc:
        raise SystemExit(f"ERROR: respuesta no JSON de bq ls --models: {result.stdout[:500]}") from exc
    if not isinstance(datos, list):
        raise SystemExit(f"ERROR: estructura imprevista al listar modelos: {type(datos).__name__}")
    modelos = set()
    for item in datos:
        if not isinstance(item, dict):
            raise SystemExit("ERROR: entrada inválida en lista de modelos")
        ref = item.get("modelReference") or {}
        nombre = ref.get("modelId") if isinstance(ref, dict) else None
        nombre = nombre or item.get("modelId")
        if not nombre:
            raise SystemExit(f"ERROR: no se reconoce un modelo listado: {str(item)[:300]}")
        modelos.add(nombre)
    return modelos


def metadata(target, model=False):
    if model and target not in listar_modelos():
        return None
    args = ["show", "--format=prettyjson"]
    if model:
        args += ["--model"]
    result = bq(*args, f"{PROJECT}:{DATASET}.{target}", check=False)
    if result.returncode:
        detalle = (result.stderr + "\n" + result.stdout).strip()
        raise SystemExit(f"ERROR: no se pudo leer {target}: {detalle[:1000]}")
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise SystemExit(f"ERROR: metadatos ilegibles para {target}")


def dry_run(sql, tag):
    output = bq(f"--location={LOCATION}", "query", "--use_legacy_sql=false",
                "--dry_run", "--format=prettyjson", "--quiet", stdin=sql)
    text = output.stdout.strip()
    print(f"DRY RUN OK: {tag}")
    try:
        obj = json.loads(text)
        stats = obj.get("statistics", {}).get("query", {})
        estimate = stats.get("totalBytesProcessed") or obj.get("totalBytesProcessed")
        if estimate is not None:
            print(f"  Bytes iniciales estimados: {estimate} (NO es costo total de entrenamiento)")
        else:
            print(f"  Salida del dry run: {text[:550] or '[sin estimación publicada]'}")
    except ValueError:
        print(f"  {text[:550] or '[sin estimación publicada]'}")


def preflight():
    print("=== ENTORNO ===")
    print(f"Proyecto: {PROJECT}; dataset: {DATASET}; ubicación: {LOCATION}")
    table = metadata("datos_ml")
    if table is None:
        raise SystemExit("ERROR: no existe datos_ml")
    if table.get("location", LOCATION).upper() != LOCATION:
        raise SystemExit("ERROR: el dataset no está en US")
    cols = {f.get("name"): f.get("type") for f in table.get("schema", {}).get("fields", [])}
    missing = REQUIRED - set(cols)
    if missing:
        raise SystemExit("ERROR: columnas ausentes en datos_ml: " + repr(sorted(missing)))
    if cols["fecha_orden"] not in ("TIMESTAMP", "DATETIME", "DATE"):
        raise SystemExit("ERROR: fecha_orden no es temporal y no se puede usar en SEQ")
    if metadata("modelo_lineal", model=True) is None:
        raise SystemExit("ERROR: no existe el modelo lineal original")
    if metadata("metricas_modelos") is None:
        raise SystemExit("ERROR: no existe metricas_modelos")
    print("OK: muestra, columna temporal, modelo original y métricas presentes")
    for tag, (name, file) in MODELS.items():
        exists = metadata(name, model=True) is not None
        print(f"{name}: {'YA EXISTE (no se reemplazará)' if exists else 'NO EXISTE'}")
        if not exists:
            dry_run(render(file), tag)
    print("PREFLIGHT COMPLETADO. No se creó ni reentrenó ningún modelo.")


def train(which):
    if os.environ.get("P2_AUTORIZO_GCP") != "SI" or os.environ.get("P2_AUTORIZO_ENTRENAMIENTO_EXTRA") != "SI":
        raise SystemExit("BLOQUEADO. Se requieren P2_AUTORIZO_GCP=SI y P2_AUTORIZO_ENTRENAMIENTO_EXTRA=SI.")
    name, sqlfile = MODELS[which]
    if metadata(name, model=True) is not None:
        print(f"NO OP: ya existe {name}; se conserva intacto")
        return
    preflight()
    print(f"INICIANDO UN SOLO ENTRENAMIENTO: {name}")
    print("AVISO: máximo de bytes facturables no es garantía de tope monetario para ML.")
    output = bq(f"--location={LOCATION}", "query", "--use_legacy_sql=false",
                "--maximum_bytes_billed=1073741824", "--format=prettyjson", "--quiet",
                stdin=render(sqlfile))
    print(output.stdout.strip()[:2000] or "Consulta concluida")
    if metadata(name, model=True) is None:
        raise SystemExit("ERROR: el trabajo terminó sin registrar modelo")
    print(f"MODELO EXISTENTE Y VERIFICADO: {name}")


def evaluate():
    for name, _ in MODELS.values():
        if metadata(name, model=True) is None:
            raise SystemExit(f"ERROR: falta modelo {name}; no se puede evaluar")
    text = render("09_comparacion_experimentos.sql")
    dry_run(text, "evaluacion-tres-modelos")
    print("=== RESULTADOS SOBRE NOVIEMBRE INDEPENDIENTE ===")
    result = bq(f"--location={LOCATION}", "query", "--use_legacy_sql=false",
                "--maximum_bytes_billed=104857600", "--nouse_cache",
                "--format=prettyjson", "--quiet", stdin=text)
    print(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=["preflight", "train-custom", "train-seq", "evaluate"])
    args = parser.parse_args()
    if args.accion == "preflight":
        preflight()
    elif args.accion == "train-custom":
        train("custom")
    elif args.accion == "train-seq":
        train("seq")
    else:
        evaluate()


if __name__ == "__main__":
    main()
