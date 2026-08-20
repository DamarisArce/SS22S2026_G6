"""
Aplicación principal de la Práctica 1.

Orquesta las tres fases del proceso ETL:

    1. Extracción
    2. Transformación
    3. Carga

Además mantiene trazabilidad mediante las tablas del esquema audit.
"""

import sys

from src.config import settings
from src.extract import extract_dataset
from src.load import (
    finish_execution_error,
    finish_execution_success,
    load_data_warehouse,
    load_staging,
    start_execution,
    update_extracted_rows,
)
from src.transform import transform_dataset


def main() -> int:
    """Ejecuta el proceso ETL completo."""

    execution_id: int | None = None

    phase = "EXTRACCION"

    rows_extracted = 0
    rows_transformed = 0

    try:
        print(
            "===== INICIANDO ETL ====="
        )

        print(
            f"Fuente: "
            f"{settings.dataset_path}"
        )


        # ---------------------------------------------------------------------
        # Auditoría
        # ---------------------------------------------------------------------

        execution_id = start_execution(
            settings.dataset_path.name
        )

        print(
            f"Ejecución ETL: "
            f"{execution_id}"
        )


        # ---------------------------------------------------------------------
        # EXTRACT
        # ---------------------------------------------------------------------

        phase = "EXTRACCION"

        print()
        print(
            "===== 1. EXTRACCION ====="
        )

        raw_dataframe = (
            extract_dataset()
        )

        rows_extracted = len(
            raw_dataframe
        )

        update_extracted_rows(
            execution_id,
            rows_extracted,
        )

        print(
            f"Registros extraídos: "
            f"{rows_extracted}"
        )

        print(
            f"Columnas extraídas: "
            f"{len(raw_dataframe.columns)}"
        )


        # ---------------------------------------------------------------------
        # STAGING
        # ---------------------------------------------------------------------

        phase = "CARGA"

        print()
        print(
            "===== STAGING ====="
        )

        staging_rows = load_staging(
            raw_dataframe,
            execution_id,
        )

        print(
            f"Registros crudos cargados "
            f"en staging: {staging_rows}"
        )


        # ---------------------------------------------------------------------
        # TRANSFORM
        # ---------------------------------------------------------------------

        phase = "TRANSFORMACION"

        print()
        print(
            "===== 2. TRANSFORMACION ====="
        )

        (
            transformed_dataframe,
            transformation_report,
        ) = transform_dataset(
            raw_dataframe
        )

        rows_transformed = len(
            transformed_dataframe
        )

        print(
            f"Registros transformados: "
            f"{rows_transformed}"
        )

        print(
            "Resolución temporal única: "
            f"{transformation_report.temporal_unique}"
        )

        print(
            "Resolución temporal con desempate: "
            f"{transformation_report.temporal_multiple}"
        )

        print(
            "Máximo de candidatos temporales: "
            f"{transformation_report.max_temporal_candidates}"
        )


        # ---------------------------------------------------------------------
        # LOAD
        # ---------------------------------------------------------------------

        phase = "CARGA"

        print()
        print(
            "===== 3. CARGA ====="
        )

        load_report = (
            load_data_warehouse(
                transformed_dataframe,
                execution_id,
                staging_rows,
            )
        )

        finish_execution_success(
            execution_id,
            rows_extracted=rows_extracted,
            rows_transformed=rows_transformed,
            rows_loaded=(
                load_report
                .fact_rows_inserted
            ),
        )


        # ---------------------------------------------------------------------
        # RESUMEN
        # ---------------------------------------------------------------------

        print()
        print(
            "===== DIMENSIONES ====="
        )

        for (
            dimension,
            count,
        ) in (
            load_report
            .dimension_counts
            .items()
        ):
            print(
                f"{dimension:<20} "
                f"{count:>7}"
            )

        print()
        print(
            "===== TABLA DE HECHOS ====="
        )

        print(
            "Registros insertados: "
            f"{load_report.fact_rows_inserted}"
        )

        print(
            "Registros ya existentes: "
            f"{load_report.fact_rows_existing}"
        )

        print(
            "Total de hechos: "
            f"{load_report.fact_rows_total}"
        )

        print()
        print(
            "===== RESULTADO ====="
        )

        print(
            "ETL COMPLETADO CORRECTAMENTE"
        )

        return 0


    except Exception as error:

        if execution_id is not None:

            try:
                finish_execution_error(
                    execution_id,
                    phase=phase,
                    error=error,
                    rows_extracted=(
                        rows_extracted
                    ),
                    rows_transformed=(
                        rows_transformed
                    ),
                )

            except Exception as audit_error:
                print(
                    "ADVERTENCIA: tampoco fue "
                    "posible registrar el error "
                    "en auditoría:"
                )

                print(
                    audit_error
                )

        print()
        print(
            "===== ERROR DEL ETL ====="
        )

        print(
            f"Fase: {phase}"
        )

        print(
            f"Tipo: "
            f"{type(error).__name__}"
        )

        print(
            f"Detalle: {error}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )
