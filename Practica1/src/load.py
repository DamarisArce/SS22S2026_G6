"""
Fase de carga del ETL.

Este módulo se encarga de:
    - Registrar ejecuciones del ETL.
    - Cargar el dataset crudo en staging.
    - Cargar las dimensiones del modelo estrella.
    - Resolver surrogate keys.
    - Cargar la tabla de hechos.
    - Evitar duplicados en ejecuciones posteriores.
    - Registrar errores de carga y resultados de auditoría.

La carga dimensional y de hechos se ejecuta dentro de una misma transacción.
Si ocurre un error, esa transacción se revierte completamente.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

import pandas as pd
import pyodbc

from src.database import build_connection_string, get_connection
from src.extract import EXPECTED_COLUMNS


MONTH_NAMES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}

DAY_NAMES = {
    1: "LUNES",
    2: "MARTES",
    3: "MIERCOLES",
    4: "JUEVES",
    5: "VIERNES",
    6: "SABADO",
    7: "DOMINGO",
}


@dataclass(frozen=True)
class LoadReport:
    """Resumen de la carga al Data Warehouse."""

    staging_rows: int
    fact_rows_inserted: int
    fact_rows_existing: int
    fact_rows_total: int
    dimension_counts: dict[str, int]


def _new_connection() -> pyodbc.Connection:
    """Crea una conexión transaccional directa."""

    return pyodbc.connect(
        build_connection_string(),
        autocommit=False,
    )


def _native_int(value: object) -> int | None:
    """Convierte enteros pandas/NumPy a int estándar de Python."""

    if pd.isna(value):
        return None

    return int(value)


def _native_datetime(
    value: object,
) -> datetime | None:
    """Convierte Timestamp de pandas a datetime estándar."""

    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, datetime):
        return value

    raise TypeError(
        f"Valor de fecha no reconocido: {value!r}"
    )


def _native_nullable_text(
    value: object,
) -> str | None:
    """
    Convierte un texto anulable a un valor nativo apto para pyodbc.

    Pandas puede representar un valor textual faltante como NaN, pd.NA u
    otros marcadores propios. Ninguno debe enviarse directamente a ODBC.
    """

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    return text or None


def _date_key(value: object) -> int | None:
    """Convierte una fecha a la clave YYYYMMDD de DimFecha."""

    value_datetime = _native_datetime(value)

    if value_datetime is None:
        return None

    return int(
        value_datetime.strftime("%Y%m%d")
    )


def _normalize_sql_text(
    value: object,
) -> str:
    """Normaliza valores CHAR/VARCHAR recuperados desde SQL Server."""

    return str(value).strip()


def start_execution(
    source_file: str,
) -> int:
    """
    Crea una ejecución de auditoría antes de iniciar el ETL.

    Se confirma inmediatamente para que la ejecución permanezca registrada
    incluso si una fase posterior falla.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO audit.EjecucionETL (
                archivo_fuente,
                estado,
                filas_extraidas,
                filas_transformadas,
                filas_cargadas,
                filas_rechazadas
            )
            OUTPUT INSERTED.id_ejecucion
            VALUES (?, 'INICIADO', 0, 0, 0, 0);
            """,
            source_file,
        )

        row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "No fue posible obtener el id de la ejecución ETL."
            )

        return int(row[0])


def update_extracted_rows(
    execution_id: int,
    rows_extracted: int,
) -> None:
    """Actualiza el contador de filas extraídas."""

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE audit.EjecucionETL
            SET filas_extraidas = ?
            WHERE id_ejecucion = ?;
            """,
            rows_extracted,
            execution_id,
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "No fue posible actualizar filas_extraidas."
            )


def load_staging(
    raw_dataframe: pd.DataFrame,
    execution_id: int,
) -> int:
    """
    Carga la representación cruda del CSV en stg.VueloRaw.

    Se conservan los valores exactamente como fueron extraídos.
    """

    columns = list(EXPECTED_COLUMNS)

    destination_columns = [
        "id_ejecucion",
        *columns,
    ]

    placeholders = ", ".join(
        "?"
        for _ in destination_columns
    )

    column_list = ", ".join(
        destination_columns
    )

    statement = (
        f"INSERT INTO stg.VueloRaw "
        f"({column_list}) "
        f"VALUES ({placeholders});"
    )

    rows = [
        (
            execution_id,
            *tuple(row),
        )
        for row in raw_dataframe[
            columns
        ].itertuples(
            index=False,
            name=None,
        )
    ]

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.fast_executemany = True

        cursor.executemany(
            statement,
            rows,
        )

        cursor.fast_executemany = False

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM stg.VueloRaw
            WHERE id_ejecucion = ?;
            """,
            execution_id,
        )

        count = int(
            cursor.fetchone()[0]
        )

        if count != len(raw_dataframe):
            raise RuntimeError(
                "La cantidad cargada en staging no coincide "
                "con la cantidad extraída."
            )

        return count


def _build_date_rows(
    dataframe: pd.DataFrame,
) -> list[tuple]:
    """Construye los registros requeridos por DimFecha."""

    all_dates: set[date] = set()

    for column in (
        "departure_datetime",
        "arrival_datetime",
        "booking_datetime",
    ):
        values = dataframe[
            column
        ].dropna()

        for value in values:
            value_datetime = (
                _native_datetime(value)
            )

            if value_datetime is not None:
                all_dates.add(
                    value_datetime.date()
                )

    rows: list[tuple] = []

    for value in sorted(all_dates):
        iso = value.isocalendar()

        day_number = (
            value.weekday() + 1
        )

        rows.append(
            (
                int(
                    value.strftime(
                        "%Y%m%d"
                    )
                ),
                value,
                value.year,
                (
                    1
                    if value.month <= 6
                    else 2
                ),
                (
                    (value.month - 1)
                    // 3
                    + 1
                ),
                value.month,
                MONTH_NAMES[
                    value.month
                ],
                value.day,
                day_number,
                DAY_NAMES[
                    day_number
                ],
                iso.week,
                int(
                    day_number >= 6
                ),
            )
        )

    return rows


def _insert_missing_rows(
    cursor: pyodbc.Cursor,
    *,
    select_sql: str,
    insert_sql: str,
    rows: list[tuple],
    key_position: int = 0,
    normalize: Callable[[object], object] = lambda value: value,
) -> int:
    """Inserta solo claves que todavía no existen."""

    cursor.execute(
        select_sql
    )

    existing = {
        normalize(row[0])
        for row in cursor.fetchall()
    }

    missing = [
        row
        for row in rows
        if normalize(
            row[key_position]
        )
        not in existing
    ]

    if missing:
        cursor.fast_executemany = True

        cursor.executemany(
            insert_sql,
            missing,
        )

        cursor.fast_executemany = False

    return len(missing)


def _load_dimensions(
    cursor: pyodbc.Cursor,
    dataframe: pd.DataFrame,
) -> None:
    """Carga todas las dimensiones utilizando sus claves naturales."""

    # -------------------------------------------------------------------------
    # DimFecha
    # -------------------------------------------------------------------------

    date_rows = _build_date_rows(
        dataframe
    )

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT id_fecha "
            "FROM dw.DimFecha;"
        ),
        insert_sql="""
            INSERT INTO dw.DimFecha (
                id_fecha,
                fecha,
                anio,
                semestre,
                trimestre,
                mes,
                nombre_mes,
                dia,
                dia_semana,
                nombre_dia,
                numero_semana,
                es_fin_semana
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows=date_rows,
    )


    # -------------------------------------------------------------------------
    # DimAerolinea
    # -------------------------------------------------------------------------

    airline_rows = sorted(
        set(
            zip(
                dataframe[
                    "airline_code"
                ],
                dataframe[
                    "airline_name"
                ],
            )
        )
    )

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT codigo_aerolinea "
            "FROM dw.DimAerolinea;"
        ),
        insert_sql="""
            INSERT INTO dw.DimAerolinea (
                codigo_aerolinea,
                nombre_aerolinea
            )
            VALUES (?, ?);
        """,
        rows=airline_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


    # -------------------------------------------------------------------------
    # DimAeropuerto
    # -------------------------------------------------------------------------

    airport_values = sorted(
        set(
            dataframe[
                "origin_airport"
            ]
        )
        |
        set(
            dataframe[
                "destination_airport"
            ]
        )
    )

    airport_rows = [
        (value,)
        for value in airport_values
    ]

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT codigo_aeropuerto "
            "FROM dw.DimAeropuerto;"
        ),
        insert_sql="""
            INSERT INTO dw.DimAeropuerto (
                codigo_aeropuerto
            )
            VALUES (?);
        """,
        rows=airport_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


    # -------------------------------------------------------------------------
    # DimPasajero
    # -------------------------------------------------------------------------

    passenger_rows = []

    for row in dataframe[
        [
            "passenger_id",
            "passenger_gender",
            "passenger_age",
            "passenger_nationality",
        ]
    ].itertuples(
        index=False,
        name=None,
    ):
        (
            passenger_id,
            gender,
            age,
            nationality,
        ) = row

        passenger_rows.append(
            (
                str(
                    passenger_id
                ).lower(),
                gender,
                _native_int(
                    age
                ),
                _native_nullable_text(
                    nationality
                ),
            )
        )

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT passenger_id "
            "FROM dw.DimPasajero;"
        ),
        insert_sql="""
            INSERT INTO dw.DimPasajero (
                passenger_id,
                genero,
                edad,
                nacionalidad
            )
            VALUES (?, ?, ?, ?);
        """,
        rows=passenger_rows,
        normalize=lambda value: (
            str(value)
            .strip()
            .lower()
        ),
    )


    # -------------------------------------------------------------------------
    # DimAeronave
    # -------------------------------------------------------------------------

    aircraft_rows = [
        (value,)
        for value in sorted(
            set(
                dataframe[
                    "aircraft_type"
                ]
            )
        )
    ]

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT tipo_aeronave "
            "FROM dw.DimAeronave;"
        ),
        insert_sql="""
            INSERT INTO dw.DimAeronave (
                tipo_aeronave
            )
            VALUES (?);
        """,
        rows=aircraft_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


    # -------------------------------------------------------------------------
    # DimClaseCabina
    # -------------------------------------------------------------------------

    cabin_rows = [
        (value,)
        for value in sorted(
            set(
                dataframe[
                    "cabin_class"
                ]
            )
        )
    ]

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT clase_cabina "
            "FROM dw.DimClaseCabina;"
        ),
        insert_sql="""
            INSERT INTO dw.DimClaseCabina (
                clase_cabina
            )
            VALUES (?);
        """,
        rows=cabin_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


    # -------------------------------------------------------------------------
    # DimEstadoVuelo
    # -------------------------------------------------------------------------

    status_rows = [
        (value,)
        for value in sorted(
            set(
                dataframe[
                    "status"
                ]
            )
        )
    ]

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT estado_vuelo "
            "FROM dw.DimEstadoVuelo;"
        ),
        insert_sql="""
            INSERT INTO dw.DimEstadoVuelo (
                estado_vuelo
            )
            VALUES (?);
        """,
        rows=status_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


    # -------------------------------------------------------------------------
    # DimCanalVenta
    # -------------------------------------------------------------------------

    channel_rows = [
        (value,)
        for value in sorted(
            set(
                dataframe[
                    "sales_channel"
                ]
            )
        )
    ]

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT canal_venta "
            "FROM dw.DimCanalVenta;"
        ),
        insert_sql="""
            INSERT INTO dw.DimCanalVenta (
                canal_venta
            )
            VALUES (?);
        """,
        rows=channel_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


    # -------------------------------------------------------------------------
    # DimMetodoPago
    # -------------------------------------------------------------------------

    payment_rows = [
        (value,)
        for value in sorted(
            set(
                dataframe[
                    "payment_method"
                ]
            )
        )
    ]

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT metodo_pago "
            "FROM dw.DimMetodoPago;"
        ),
        insert_sql="""
            INSERT INTO dw.DimMetodoPago (
                metodo_pago
            )
            VALUES (?);
        """,
        rows=payment_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


    # -------------------------------------------------------------------------
    # DimMoneda
    # -------------------------------------------------------------------------

    currency_rows = [
        (value,)
        for value in sorted(
            set(
                dataframe[
                    "currency"
                ]
            )
        )
    ]

    _insert_missing_rows(
        cursor,
        select_sql=(
            "SELECT codigo_moneda "
            "FROM dw.DimMoneda;"
        ),
        insert_sql="""
            INSERT INTO dw.DimMoneda (
                codigo_moneda
            )
            VALUES (?);
        """,
        rows=currency_rows,
        normalize=lambda value: (
            _normalize_sql_text(
                value
            ).upper()
        ),
    )


def _fetch_dimension_maps(
    cursor: pyodbc.Cursor,
) -> dict[str, dict]:
    """Recupera mapas business key -> surrogate key."""

    maps: dict[str, dict] = {}


    cursor.execute(
        """
        SELECT
            codigo_aerolinea,
            id_aerolinea
        FROM dw.DimAerolinea;
        """
    )

    maps["airline"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            codigo_aeropuerto,
            id_aeropuerto
        FROM dw.DimAeropuerto;
        """
    )

    maps["airport"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            passenger_id,
            id_pasajero
        FROM dw.DimPasajero;
        """
    )

    maps["passenger"] = {
        str(
            row[0]
        ).strip().lower(): int(
            row[1]
        )
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            tipo_aeronave,
            id_aeronave
        FROM dw.DimAeronave;
        """
    )

    maps["aircraft"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            clase_cabina,
            id_clase_cabina
        FROM dw.DimClaseCabina;
        """
    )

    maps["cabin"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            estado_vuelo,
            id_estado_vuelo
        FROM dw.DimEstadoVuelo;
        """
    )

    maps["status"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            canal_venta,
            id_canal_venta
        FROM dw.DimCanalVenta;
        """
    )

    maps["channel"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            metodo_pago,
            id_metodo_pago
        FROM dw.DimMetodoPago;
        """
    )

    maps["payment"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            codigo_moneda,
            id_moneda
        FROM dw.DimMoneda;
        """
    )

    maps["currency"] = {
        _normalize_sql_text(
            row[0]
        ).upper(): int(row[1])
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            id_fecha
        FROM dw.DimFecha;
        """
    )

    maps["date"] = {
        int(row[0]): int(row[0])
        for row in cursor.fetchall()
    }

    return maps


def _build_fact_rows(
    cursor: pyodbc.Cursor,
    dataframe: pd.DataFrame,
    execution_id: int,
    maps: dict[str, dict],
) -> tuple[list[tuple], int]:
    """
    Construye hechos que todavía no existen según record_id_fuente.

    Esto evita duplicar el Data Warehouse si se ejecuta nuevamente el ETL
    sobre la misma fuente.
    """

    cursor.execute(
        """
        SELECT record_id_fuente
        FROM dw.FactVueloPasajero;
        """
    )

    existing_record_ids = {
        int(row[0])
        for row in cursor.fetchall()
    }

    fact_rows: list[tuple] = []

    skipped = 0

    for row in dataframe.itertuples(
        index=False
    ):
        record_id = int(
            row.record_id
        )

        if record_id in existing_record_ids:
            skipped += 1
            continue

        departure_key = _date_key(
            row.departure_datetime
        )

        arrival_key = _date_key(
            row.arrival_datetime
        )

        booking_key = _date_key(
            row.booking_datetime
        )

        for date_key in (
            departure_key,
            booking_key,
        ):
            if date_key not in maps["date"]:
                raise RuntimeError(
                    f"record_id={record_id}: "
                    f"fecha {date_key} no existe en DimFecha."
                )

        if (
            arrival_key is not None
            and arrival_key not in maps["date"]
        ):
            raise RuntimeError(
                f"record_id={record_id}: "
                f"fecha de llegada {arrival_key} "
                "no existe en DimFecha."
            )

        try:
            fact_row = (
                record_id,

                departure_key,
                arrival_key,
                booking_key,

                maps[
                    "airline"
                ][
                    row.airline_code
                ],

                maps[
                    "airport"
                ][
                    row.origin_airport
                ],

                maps[
                    "airport"
                ][
                    row.destination_airport
                ],

                maps[
                    "passenger"
                ][
                    str(
                        row.passenger_id
                    ).lower()
                ],

                maps[
                    "aircraft"
                ][
                    row.aircraft_type
                ],

                maps[
                    "cabin"
                ][
                    row.cabin_class
                ],

                maps[
                    "status"
                ][
                    row.status
                ],

                maps[
                    "channel"
                ][
                    row.sales_channel
                ],

                maps[
                    "payment"
                ][
                    row.payment_method
                ],

                maps[
                    "currency"
                ][
                    row.currency
                ],

                row.flight_number,
                _native_nullable_text(
                    row.seat
                ),

                _native_datetime(
                    row.departure_datetime
                ),

                _native_datetime(
                    row.arrival_datetime
                ),

                _native_datetime(
                    row.booking_datetime
                ),

                _native_int(
                    row.duration_min
                ),

                _native_int(
                    row.delay_min
                ),

                row.ticket_price,
                row.ticket_price_usd_est,

                int(
                    row.bags_total
                ),

                int(
                    row.bags_checked
                ),

                1,
                execution_id,
            )

        except KeyError as exc:
            raise RuntimeError(
                f"record_id={record_id}: "
                f"no se encontró una surrogate key para {exc}."
            ) from exc

        fact_rows.append(
            fact_row
        )

    return fact_rows, skipped


def _fetch_dimension_counts(
    cursor: pyodbc.Cursor,
) -> dict[str, int]:
    """Obtiene cardinalidad final de cada dimensión."""

    tables = (
        "DimFecha",
        "DimAerolinea",
        "DimAeropuerto",
        "DimPasajero",
        "DimAeronave",
        "DimClaseCabina",
        "DimEstadoVuelo",
        "DimCanalVenta",
        "DimMetodoPago",
        "DimMoneda",
    )

    counts: dict[str, int] = {}

    for table in tables:
        cursor.execute(
            f"SELECT COUNT(*) "
            f"FROM dw.{table};"
        )

        counts[table] = int(
            cursor.fetchone()[0]
        )

    return counts


def load_data_warehouse(
    dataframe: pd.DataFrame,
    execution_id: int,
    staging_rows: int,
) -> LoadReport:
    """
    Carga dimensiones y hechos en una única transacción.

    Si falla cualquier parte de esta función, se revierte toda esta carga.
    """

    connection = _new_connection()

    try:
        cursor = connection.cursor()

        _load_dimensions(
            cursor,
            dataframe,
        )

        maps = _fetch_dimension_maps(
            cursor
        )

        (
            fact_rows,
            existing_rows,
        ) = _build_fact_rows(
            cursor,
            dataframe,
            execution_id,
            maps,
        )

        fact_columns = (
            "record_id_fuente",
            "id_fecha_salida",
            "id_fecha_llegada",
            "id_fecha_reserva",
            "id_aerolinea",
            "id_aeropuerto_origen",
            "id_aeropuerto_destino",
            "id_pasajero",
            "id_aeronave",
            "id_clase_cabina",
            "id_estado_vuelo",
            "id_canal_venta",
            "id_metodo_pago",
            "id_moneda",
            "numero_vuelo",
            "asiento",
            "fecha_hora_salida",
            "fecha_hora_llegada",
            "fecha_hora_reserva",
            "duracion_min",
            "retraso_min",
            "precio_boleto",
            "precio_usd_estimado",
            "maletas_total",
            "maletas_facturadas",
            "cantidad_registros",
            "id_ejecucion",
        )

        if fact_rows:
            placeholders = ", ".join(
                "?"
                for _ in fact_columns
            )

            statement = (
                "INSERT INTO dw.FactVueloPasajero "
                f"({', '.join(fact_columns)}) "
                f"VALUES ({placeholders});"
            )

            cursor.fast_executemany = True

            cursor.executemany(
                statement,
                fact_rows,
            )

            cursor.fast_executemany = False

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM dw.FactVueloPasajero;
            """
        )

        total_fact_rows = int(
            cursor.fetchone()[0]
        )

        dimension_counts = (
            _fetch_dimension_counts(
                cursor
            )
        )

        connection.commit()

        return LoadReport(
            staging_rows=staging_rows,
            fact_rows_inserted=len(
                fact_rows
            ),
            fact_rows_existing=existing_rows,
            fact_rows_total=total_fact_rows,
            dimension_counts=dimension_counts,
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def finish_execution_success(
    execution_id: int,
    *,
    rows_extracted: int,
    rows_transformed: int,
    rows_loaded: int,
) -> None:
    """Marca una ejecución ETL como exitosa."""

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE audit.EjecucionETL
            SET
                fecha_fin = SYSDATETIME(),
                estado = 'EXITOSO',
                filas_extraidas = ?,
                filas_transformadas = ?,
                filas_cargadas = ?,
                filas_rechazadas = 0,
                mensaje = ?
            WHERE id_ejecucion = ?;
            """,
            rows_extracted,
            rows_transformed,
            rows_loaded,
            (
                "Proceso ETL completado correctamente."
            ),
            execution_id,
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "No fue posible finalizar la auditoría ETL."
            )


def finish_execution_error(
    execution_id: int,
    *,
    phase: str,
    error: Exception,
    rows_extracted: int = 0,
    rows_transformed: int = 0,
) -> None:
    """Registra el fallo de una ejecución previamente iniciada."""

    allowed_phases = {
        "EXTRACCION",
        "TRANSFORMACION",
        "CARGA",
    }

    if phase not in allowed_phases:
        phase = "CARGA"

    error_type = type(
        error
    ).__name__

    detail = str(error)

    if len(detail) > 1900:
        detail = (
            detail[:1900]
            + "... [truncado]"
        )

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO audit.ErrorETL (
                id_ejecucion,
                record_id_fuente,
                fase,
                tipo_error,
                detalle,
                registro_original
            )
            VALUES (?, NULL, ?, ?, ?, NULL);
            """,
            execution_id,
            phase,
            error_type,
            detail,
        )

        cursor.execute(
            """
            UPDATE audit.EjecucionETL
            SET
                fecha_fin = SYSDATETIME(),
                estado = 'ERROR',
                filas_extraidas = ?,
                filas_transformadas = ?,
                filas_cargadas = 0,
                filas_rechazadas = 0,
                mensaje = ?
            WHERE id_ejecucion = ?;
            """,
            rows_extracted,
            rows_transformed,
            (
                f"{phase}: "
                f"{error_type}: "
                f"{detail}"
            )[:1000],
            execution_id,
        )
