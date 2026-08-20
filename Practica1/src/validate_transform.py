"""
Validación reproducible de la transformación del dataset.

No escribe en SQL Server.
No modifica el dataset.
No persiste datos transformados.

Su función es comprobar que la transformación satisface las reglas
establecidas antes de habilitar la fase de carga.
"""

from collections import Counter
from hashlib import sha256
import sys

from src.config import settings
from src.extract import extract_dataset
from src.transform import transform_dataset


EXPECTED_SHA256 = (
    "a3a6b5cc67697a069a7057789accde217ecc580d03098b643db672978abd753e"
)


def calculate_sha256() -> str:
    """Calcula SHA-256 del dataset utilizado."""

    digest = sha256()

    with settings.dataset_path.open(
        "rb"
    ) as file:
        while chunk := file.read(
            1024 * 1024
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> int:
    raw = extract_dataset()

    transformed, report = (
        transform_dataset(raw)
    )

    checks: list[
        tuple[str, bool, str]
    ] = []


    def check(
        name: str,
        condition: bool,
        detail: str,
    ) -> None:
        checks.append(
            (
                name,
                bool(condition),
                detail,
            )
        )


    # -------------------------------------------------------------------------
    # Fuente
    # -------------------------------------------------------------------------

    dataset_hash = calculate_sha256()

    check(
        "SHA-256 del dataset",
        dataset_hash == EXPECTED_SHA256,
        dataset_hash,
    )

    check(
        "Cantidad de registros recibidos",
        report.rows_received == 10000,
        str(report.rows_received),
    )

    check(
        "Cantidad de registros transformados",
        report.rows_transformed == 10000,
        str(report.rows_transformed),
    )


    # -------------------------------------------------------------------------
    # Identificadores
    # -------------------------------------------------------------------------

    check(
        "record_id sin duplicados",
        transformed[
            "record_id"
        ].nunique() == 10000,
        str(
            transformed[
                "record_id"
            ].nunique()
        ),
    )

    check(
        "passenger_id sin duplicados",
        transformed[
            "passenger_id"
        ].nunique() == 10000,
        str(
            transformed[
                "passenger_id"
            ].nunique()
        ),
    )


    # -------------------------------------------------------------------------
    # Homologaciones
    # -------------------------------------------------------------------------

    gender_counts = Counter(
        transformed[
            "passenger_gender"
        ]
    )

    expected_genders = {
        "M": 4912,
        "F": 4698,
        "X": 390,
    }

    check(
        "Homologación de género",
        dict(gender_counts)
        == expected_genders,
        str(
            dict(gender_counts)
        ),
    )


    status_counts = Counter(
        transformed["status"]
    )

    expected_statuses = {
        "ON_TIME": 7278,
        "DELAYED": 1970,
        "CANCELLED": 560,
        "DIVERTED": 192,
    }

    check(
        "Distribución de estados",
        dict(status_counts)
        == expected_statuses,
        str(
            dict(status_counts)
        ),
    )


    airline_codes = transformed[
        "airline_code"
    ].nunique()

    airline_names = transformed[
        "airline_name"
    ].nunique()

    check(
        "Aerolíneas homologadas",
        (
            airline_codes == 12
            and airline_names == 12
        ),
        (
            f"códigos={airline_codes}, "
            f"nombres={airline_names}"
        ),
    )


    airports = (
        set(
            transformed[
                "origin_airport"
            ]
        )
        |
        set(
            transformed[
                "destination_airport"
            ]
        )
    )

    check(
        "Aeropuertos homologados",
        len(airports) == 15,
        str(len(airports)),
    )


    unknown_sales = int(
        (
            transformed[
                "sales_channel"
            ]
            == "DESCONOCIDO"
        ).sum()
    )

    check(
        "Canal DESCONOCIDO para nulos",
        unknown_sales == 144,
        str(unknown_sales),
    )


    # -------------------------------------------------------------------------
    # Fechas
    # -------------------------------------------------------------------------

    arrival_before_departure = int(
        (
            transformed[
                "arrival_datetime"
            ].notna()
            &
            (
                transformed[
                    "arrival_datetime"
                ]
                <
                transformed[
                    "departure_datetime"
                ]
            )
        ).sum()
    )

    check(
        "No hay llegadas anteriores a salida",
        arrival_before_departure == 0,
        str(
            arrival_before_departure
        ),
    )


    booking_after_departure = int(
        (
            transformed[
                "booking_datetime"
            ]
            >
            transformed[
                "departure_datetime"
            ]
        ).sum()
    )

    check(
        "No hay reservas posteriores a salida",
        booking_after_departure == 0,
        str(
            booking_after_departure
        ),
    )


    booking_lead_days = (
        (
            transformed[
                "departure_datetime"
            ]
            -
            transformed[
                "booking_datetime"
            ]
        )
        .dt.total_seconds()
        / 86400
    )

    booking_min = float(
        booking_lead_days.min()
    )

    booking_max = float(
        booking_lead_days.max()
    )

    check(
        "Rango de anticipación de reserva",
        (
            booking_min >= 1
            and booking_max <= 121
        ),
        (
            f"mínimo={booking_min:.5f}, "
            f"máximo={booking_max:.5f}"
        ),
    )


    active = transformed[
        transformed["status"]
        != "CANCELLED"
    ].copy()

    timing_residual = (
        (
            active[
                "arrival_datetime"
            ]
            -
            active[
                "departure_datetime"
            ]
        )
        .dt.total_seconds()
        / 60
        -
        (
            active[
                "duration_min"
            ]
            +
            active[
                "delay_min"
            ]
        )
    )

    residual_min = float(
        timing_residual.min()
    )

    residual_max = float(
        timing_residual.max()
    )

    check(
        "Rango residual duración/retraso",
        (
            residual_min >= -10
            and residual_max <= 25
        ),
        (
            f"mínimo={residual_min:.0f}, "
            f"máximo={residual_max:.0f}"
        ),
    )


    # -------------------------------------------------------------------------
    # Cancelaciones y valores nulos
    # -------------------------------------------------------------------------

    cancelled = transformed[
        transformed["status"]
        == "CANCELLED"
    ]

    not_cancelled = transformed[
        transformed["status"]
        != "CANCELLED"
    ]

    check(
        "Cantidad de cancelaciones",
        len(cancelled) == 560,
        str(len(cancelled)),
    )

    for column in (
        "arrival_datetime",
        "duration_min",
        "delay_min",
        "seat",
    ):
        cancelled_nulls = int(
            cancelled[
                column
            ].isna().sum()
        )

        active_nulls = int(
            not_cancelled[
                column
            ].isna().sum()
        )

        check(
            (
                f"Nulos correctos en "
                f"{column}"
            ),
            (
                cancelled_nulls == 560
                and active_nulls == 0
            ),
            (
                f"CANCELLED={cancelled_nulls}, "
                f"no_CANCELLED={active_nulls}"
            ),
        )


    age_nulls = int(
        transformed[
            "passenger_age"
        ].isna().sum()
    )

    nationality_nulls = int(
        transformed[
            "passenger_nationality"
        ].isna().sum()
    )

    check(
        "Edades nulas preservadas",
        age_nulls == 112,
        str(age_nulls),
    )

    check(
        "Nacionalidades nulas preservadas",
        nationality_nulls == 209,
        str(nationality_nulls),
    )


    seat_none_count = sum(
        value is None
        for value in cancelled["seat"]
    )

    nationality_none_count = sum(
        value is None
        for value in transformed[
            "passenger_nationality"
        ]
    )

    check(
        "Asientos faltantes son None nativo",
        seat_none_count == 560,
        str(seat_none_count),
    )

    check(
        "Nacionalidades faltantes son None nativo",
        nationality_none_count == 209,
        str(nationality_none_count),
    )


    # -------------------------------------------------------------------------
    # Resolución de ambigüedad
    # -------------------------------------------------------------------------

    check(
        "Filas con solución temporal única",
        report.temporal_unique == 8297,
        str(
            report.temporal_unique
        ),
    )

    check(
        "Filas con múltiples soluciones válidas",
        report.temporal_multiple == 1703,
        str(
            report.temporal_multiple
        ),
    )

    check(
        "Máximo de combinaciones válidas por fila",
        report.max_temporal_candidates == 4,
        str(
            report.max_temporal_candidates
        ),
    )


    # -------------------------------------------------------------------------
    # Integridad restante
    # -------------------------------------------------------------------------

    duplicated_records = int(
        transformed[
            "record_id"
        ].duplicated().sum()
    )

    checked_exceeds_total = int(
        (
            transformed[
                "bags_checked"
            ]
            >
            transformed[
                "bags_total"
            ]
        ).sum()
    )

    equal_airports = int(
        (
            transformed[
                "origin_airport"
            ]
            ==
            transformed[
                "destination_airport"
            ]
        ).sum()
    )

    check(
        "Sin record_id duplicados",
        duplicated_records == 0,
        str(
            duplicated_records
        ),
    )

    check(
        "Equipaje consistente",
        checked_exceeds_total == 0,
        str(
            checked_exceeds_total
        ),
    )

    check(
        "Origen diferente de destino",
        equal_airports == 0,
        str(
            equal_airports
        ),
    )


    # -------------------------------------------------------------------------
    # Presentación
    # -------------------------------------------------------------------------

    print(
        "===== VALIDACIÓN DE TRANSFORMACIÓN ====="
    )

    print(
        f"SHA-256: {dataset_hash}"
    )

    print(
        f"Registros recibidos: "
        f"{report.rows_received}"
    )

    print(
        f"Registros transformados: "
        f"{report.rows_transformed}"
    )

    print(
        f"Resolución temporal única: "
        f"{report.temporal_unique}"
    )

    print(
        f"Resolución temporal con desempate: "
        f"{report.temporal_multiple}"
    )

    print(
        f"Máximo de candidatos temporales: "
        f"{report.max_temporal_candidates}"
    )

    print()
    print(
        "===== PRUEBAS ====="
    )

    passed = 0

    for number, (
        name,
        success,
        detail,
    ) in enumerate(
        checks,
        start=1,
    ):
        result = (
            "PASS"
            if success
            else "FAIL"
        )

        if success:
            passed += 1

        print(
            f"{number:02d}. "
            f"[{result}] "
            f"{name}: {detail}"
        )

    failed = len(checks) - passed

    print()
    print(
        "===== RESUMEN ====="
    )

    print(
        f"Pruebas totales: {len(checks)}"
    )

    print(
        f"Pruebas exitosas: {passed}"
    )

    print(
        f"Pruebas fallidas: {failed}"
    )


    print()
    print(
        "===== EJEMPLOS TRANSFORMADOS ====="
    )

    example_columns = [
        "record_id",
        "airline_code",
        "airline_name",
        "flight_number",
        "origin_airport",
        "destination_airport",
        "status",
        "passenger_gender",
        "ticket_price",
    ]

    print(
        transformed[
            example_columns
        ]
        .head(5)
        .to_string(
            index=False
        )
    )


    if failed:
        print()
        print(
            "RESULTADO GENERAL: FAIL"
        )

        return 1

    print()
    print(
        "RESULTADO GENERAL: PASS"
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
