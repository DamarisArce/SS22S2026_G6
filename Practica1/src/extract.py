"""
Fase de extracción del ETL.

Lee el CSV sin realizar conversiones automáticas para preservar exactamente
los valores de la fuente antes de la transformación.
"""

from pathlib import Path

import pandas as pd

from src.config import settings


EXPECTED_COLUMNS = (
    "record_id",
    "airline_code",
    "airline_name",
    "flight_number",
    "origin_airport",
    "destination_airport",
    "departure_datetime",
    "arrival_datetime",
    "duration_min",
    "status",
    "delay_min",
    "aircraft_type",
    "cabin_class",
    "seat",
    "passenger_id",
    "passenger_gender",
    "passenger_age",
    "passenger_nationality",
    "booking_datetime",
    "sales_channel",
    "payment_method",
    "ticket_price",
    "currency",
    "ticket_price_usd_est",
    "bags_total",
    "bags_checked",
)


def extract_dataset(
    path: Path | None = None,
) -> pd.DataFrame:
    """
    Extrae el archivo CSV como texto.

    No interpreta NULL, fechas ni números en esta etapa porque el objetivo
    de extracción es conservar fielmente la representación original.
    """

    dataset_path = path or settings.dataset_path

    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"No se encontró el dataset: {dataset_path}"
        )

    dataframe = pd.read_csv(
        dataset_path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    actual_columns = tuple(dataframe.columns)

    if actual_columns != EXPECTED_COLUMNS:
        raise ValueError(
            "El esquema del CSV no coincide con el esperado.\n"
            f"Esperado: {EXPECTED_COLUMNS}\n"
            f"Recibido: {actual_columns}"
        )

    if dataframe.empty:
        raise ValueError("El dataset no contiene registros.")

    return dataframe


if __name__ == "__main__":
    df = extract_dataset()

    print("===== EXTRACCION =====")
    print(f"Registros: {len(df)}")
    print(f"Columnas: {len(df.columns)}")
    print(f"Archivo: {settings.dataset_path}")
