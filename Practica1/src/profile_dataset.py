"""
Perfilado reproducible del dataset crudo.

El objetivo es identificar problemas de calidad antes de aplicar las
transformaciones del ETL.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.extract import extract_dataset


def is_blank(value: object) -> bool:
    """Determina si un valor de la fuente está vacío."""

    if value is None:
        return True

    return str(value).strip() == ""


def date_candidates(value: object) -> list[datetime]:
    """
    Obtiene todas las interpretaciones válidas conocidas para una fecha.

    El dataset contiene:
        DD/MM/YYYY HH:MM
        MM-DD-YYYY HH:MM AM/PM

    Para fechas con '/' y día/mes <= 12 se consideran además ambas
    interpretaciones posibles para detectar ambigüedad.
    """

    text = str(value).strip()

    if not text:
        return []

    parsed: list[datetime] = []

    if "/" in text:
        formats = (
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M",
        )
    elif "-" in text:
        formats = (
            "%m-%d-%Y %I:%M %p",
        )
    else:
        formats = ()

    for date_format in formats:
        try:
            candidate = datetime.strptime(
                text,
                date_format,
            )
        except ValueError:
            continue

        if candidate not in parsed:
            parsed.append(candidate)

    return parsed


def conventional_parse(value: object) -> datetime | None:
    """
    Simula una interpretación convencional:
        '/' -> día/mes
        '-' -> mes-día con AM/PM.

    Se utiliza únicamente para evidenciar por qué no basta con aplicar una
    conversión ingenua de fechas.
    """

    text = str(value).strip()

    if not text:
        return None

    formats = []

    if "/" in text:
        formats.append("%d/%m/%Y %H:%M")

    if "-" in text:
        formats.append("%m-%d-%Y %I:%M %p")

    for date_format in formats:
        try:
            return datetime.strptime(
                text,
                date_format,
            )
        except ValueError:
            pass

    return None


def print_section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    df = extract_dataset()

    print_section("1. RESUMEN GENERAL")

    print(f"Registros: {len(df)}")
    print(f"Columnas: {len(df.columns)}")
    print(
        "record_id únicos: "
        f"{df['record_id'].nunique()}"
    )
    print(
        "passenger_id únicos: "
        f"{df['passenger_id'].nunique()}"
    )


    print_section("2. VALORES VACÍOS")

    blank_counts = {
        column: int(df[column].map(is_blank).sum())
        for column in df.columns
    }

    for column, count in blank_counts.items():
        if count > 0:
            print(f"{column:<26} {count:>6}")


    print_section("3. CARDINALIDAD CRUDA")

    for column in df.columns:
        non_blank = df.loc[
            ~df[column].map(is_blank),
            column,
        ]

        print(
            f"{column:<26} "
            f"{non_blank.nunique():>6}"
        )


    print_section("4. NORMALIZACIONES DETECTADAS")

    lower_origin = (
        df["origin_airport"].str.strip()
        != df["origin_airport"].str.strip().str.upper()
    ).sum()

    lower_destination = (
        df["destination_airport"].str.strip()
        != df["destination_airport"].str.strip().str.upper()
    ).sum()

    lower_flight = (
        df["flight_number"].str.strip()
        != df["flight_number"].str.strip().str.upper()
    ).sum()

    comma_prices = (
        df["ticket_price"]
        .str.contains(",", regex=False)
        .sum()
    )

    print(
        "Aeropuertos origen en minúscula: "
        f"{int(lower_origin)}"
    )
    print(
        "Aeropuertos destino en minúscula: "
        f"{int(lower_destination)}"
    )
    print(
        "Números de vuelo con minúsculas: "
        f"{int(lower_flight)}"
    )
    print(
        "Precios con coma decimal: "
        f"{int(comma_prices)}"
    )

    print(
        "Variantes crudas de género: "
        f"{df['passenger_gender'].nunique()}"
    )

    print(
        "Variantes crudas de nombre de aerolínea: "
        f"{df['airline_name'].nunique()}"
    )


    print_section("5. VARIANTES DE GÉNERO")

    gender_counts = (
        df["passenger_gender"]
        .value_counts()
        .sort_index()
    )

    for value, count in gender_counts.items():
        print(f"{value:<20} {int(count):>6}")


    print_section("6. AEROLÍNEAS POR CÓDIGO")

    airline_data = df.copy()

    airline_data["code_normalized"] = (
        airline_data["airline_code"]
        .str.strip()
        .str.upper()
    )

    for code, group in airline_data.groupby(
        "code_normalized",
        sort=True,
    ):
        names = sorted(
            set(
                group["airline_name"]
                .str.strip()
                .tolist()
            )
        )

        print(
            f"{code}: "
            + " | ".join(names)
        )


    print_section("7. ESTADOS DEL VUELO")

    for status, count in (
        df["status"]
        .str.strip()
        .str.upper()
        .value_counts()
        .items()
    ):
        print(f"{status:<20} {int(count):>6}")


    print_section("8. AMBIGÜEDAD DE FECHAS")

    date_columns = (
        "departure_datetime",
        "arrival_datetime",
        "booking_datetime",
    )

    for column in date_columns:
        candidate_counts = df[column].map(
            lambda value: len(
                date_candidates(value)
            )
        )

        empty = int((candidate_counts == 0).sum())
        unique = int((candidate_counts == 1).sum())
        ambiguous = int((candidate_counts > 1).sum())

        print(column)
        print(f"  sin fecha/candidato: {empty}")
        print(f"  interpretación única: {unique}")
        print(f"  interpretación ambigua: {ambiguous}")


    print_section(
        "9. PROBLEMAS DE UNA INTERPRETACIÓN INGENUA"
    )

    departures = df[
        "departure_datetime"
    ].map(conventional_parse)

    arrivals = df[
        "arrival_datetime"
    ].map(conventional_parse)

    bookings = df[
        "booking_datetime"
    ].map(conventional_parse)

    arrival_before_departure = 0
    booking_after_departure = 0

    for departure, arrival, booking in zip(
        departures,
        arrivals,
        bookings,
    ):
        if (
            arrival is not None
            and departure is not None
            and arrival < departure
        ):
            arrival_before_departure += 1

        if (
            booking is not None
            and departure is not None
            and booking > departure
        ):
            booking_after_departure += 1

    print(
        "Llegadas anteriores a la salida: "
        f"{arrival_before_departure}"
    )

    print(
        "Reservas posteriores a la salida: "
        f"{booking_after_departure}"
    )


    print_section(
        "10. RELACIÓN ENTRE DURACIÓN, RETRASO Y FECHAS NO AMBIGUAS"
    )

    timing_differences: list[float] = []

    booking_leads: list[float] = []

    for _, row in df.iterrows():
        departure_candidates = date_candidates(
            row["departure_datetime"]
        )

        arrival_candidates = date_candidates(
            row["arrival_datetime"]
        )

        booking_candidates = date_candidates(
            row["booking_datetime"]
        )

        if (
            len(departure_candidates) == 1
            and len(arrival_candidates) == 1
            and row["status"].strip().upper()
                != "CANCELLED"
        ):
            departure = departure_candidates[0]
            arrival = arrival_candidates[0]

            duration = int(
                row["duration_min"].strip()
            )

            delay = int(
                row["delay_min"].strip()
            )

            elapsed_minutes = (
                arrival - departure
            ).total_seconds() / 60

            timing_differences.append(
                elapsed_minutes
                - (duration + delay)
            )

        if (
            len(departure_candidates) == 1
            and len(booking_candidates) == 1
        ):
            departure = departure_candidates[0]
            booking = booking_candidates[0]

            lead_days = (
                departure - booking
            ).total_seconds() / 86400

            if lead_days >= 0:
                booking_leads.append(
                    lead_days
                )

    if timing_differences:
        print(
            "Diferencia mínima "
            "[tiempo real - (duración + retraso)]: "
            f"{min(timing_differences):.0f} min"
        )

        print(
            "Diferencia máxima "
            "[tiempo real - (duración + retraso)]: "
            f"{max(timing_differences):.0f} min"
        )

    if booking_leads:
        print(
            "Anticipación mínima de reserva observada: "
            f"{min(booking_leads):.2f} días"
        )

        print(
            "Anticipación máxima de reserva observada: "
            f"{max(booking_leads):.2f} días"
        )


    print_section("11. CONSISTENCIA DE CANCELACIONES")

    statuses = (
        df["status"]
        .str.strip()
        .str.upper()
    )

    cancelled = statuses == "CANCELLED"
    not_cancelled = ~cancelled

    print(
        "Vuelos CANCELLED: "
        f"{int(cancelled.sum())}"
    )

    for column in (
        "arrival_datetime",
        "duration_min",
        "delay_min",
        "seat",
    ):
        cancelled_blank = int(
            df.loc[
                cancelled,
                column,
            ].map(is_blank).sum()
        )

        active_blank = int(
            df.loc[
                not_cancelled,
                column,
            ].map(is_blank).sum()
        )

        print(
            f"{column}: "
            f"vacíos CANCELLED={cancelled_blank}, "
            f"vacíos no CANCELLED={active_blank}"
        )


if __name__ == "__main__":
    main()
