"""
Fase de transformación del ETL.

Responsabilidades principales:
    - Homologar texto y categorías.
    - Normalizar aerolíneas, aeropuertos y números de vuelo.
    - Homologar género.
    - Convertir tipos numéricos.
    - Convertir precios con punto o coma decimal.
    - Tratar valores faltantes.
    - Resolver fechas ambiguas utilizando restricciones temporales.
    - Validar reglas de calidad antes de cargar SQL Server.

Resolución de fechas
--------------------
El dataset contiene dos representaciones conocidas:

    DD/MM/YYYY HH:MM
    MM-DD-YYYY HH:MM AM/PM

Las fechas con "/" pueden ser ambiguas cuando día y mes son <= 12.

Para resolverlas se generan todos los candidatos válidos y se seleccionan
combinaciones que cumplan:

    reserva <= salida
    llegada >= salida
    1 <= anticipación de reserva <= 121 días
    -10 <= llegada-salida-(duración+retraso) <= 25 minutos

Los límites anteriores se obtuvieron del perfilado de registros cuya
interpretación temporal era única.

Si varias combinaciones continúan siendo válidas, se utiliza como criterio
determinista la convención DD/MM/YYYY para valores con "/".

No se afirma que este desempate reconstruya una fecha original no observable;
su finalidad es proporcionar una transformación reproducible y consistente.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

import pandas as pd


AIRLINE_NAMES = {
    "AA": "American Airlines",
    "AM": "Aeromexico",
    "AV": "Avianca",
    "B6": "JetBlue",
    "BA": "British Airways",
    "CM": "Copa Airlines",
    "DL": "Delta",
    "FR": "Ryanair",
    "IB": "Iberia",
    "LA": "LATAM",
    "UA": "United",
    "WN": "Southwest",
}

GENDER_MAP = {
    "m": "M",
    "masculino": "M",
    "f": "F",
    "femenino": "F",
    "x": "X",
    "nobinario": "X",
}

VALID_STATUSES = {
    "ON_TIME",
    "DELAYED",
    "CANCELLED",
    "DIVERTED",
}

TIMING_RESIDUAL_MIN_MINUTES = -10
TIMING_RESIDUAL_MAX_MINUTES = 25

BOOKING_LEAD_MIN_DAYS = 1
BOOKING_LEAD_MAX_DAYS = 121


@dataclass(frozen=True)
class DateCandidate:
    """Una interpretación posible de una fecha de la fuente."""

    value: datetime

    # 0 = formato preferido de la representación observada.
    # 1 = interpretación alternativa de una fecha "/" ambigua.
    preference: int


@dataclass(frozen=True)
class TemporalResolution:
    """Resultado de resolver conjuntamente las fechas de una fila."""

    departure: datetime
    arrival: datetime | None
    booking: datetime
    candidate_count: int
    timing_residual_minutes: float | None
    booking_lead_days: float


@dataclass(frozen=True)
class TransformationReport:
    """Resumen de la fase de transformación."""

    rows_received: int
    rows_transformed: int
    temporal_unique: int
    temporal_multiple: int
    max_temporal_candidates: int


def _text(value: object) -> str:
    """Convierte un valor a texto limpio."""

    if value is None:
        return ""

    return str(value).strip()


def _is_blank(value: object) -> bool:
    """Indica si un valor proveniente de la fuente está vacío."""

    return _text(value) == ""


def _parse_date_candidates(value: object) -> list[DateCandidate]:
    """
    Genera todas las interpretaciones conocidas de una fecha.

    Para fechas con "/" se intenta primero DD/MM/YYYY, que es la convención
    preferida. Si también es válida MM/DD/YYYY, se conserva como alternativa.

    Las fechas con "-" utilizan el formato MM-DD-YYYY con AM/PM observado
    directamente en el dataset.
    """

    text = _text(value)

    if not text:
        return []

    if "/" in text:
        specifications = (
            ("%d/%m/%Y %H:%M", 0),
            ("%m/%d/%Y %H:%M", 1),
        )
    elif "-" in text:
        specifications = (
            ("%m-%d-%Y %I:%M %p", 0),
        )
    else:
        specifications = ()

    parsed: dict[datetime, int] = {}

    for date_format, preference in specifications:
        try:
            candidate = datetime.strptime(
                text,
                date_format,
            )
        except ValueError:
            continue

        previous_preference = parsed.get(candidate)

        if (
            previous_preference is None
            or preference < previous_preference
        ):
            parsed[candidate] = preference

    return [
        DateCandidate(
            value=date_value,
            preference=preference,
        )
        for date_value, preference in parsed.items()
    ]


def _parse_int(
    value: object,
    field_name: str,
    *,
    nullable: bool = False,
) -> int | None:
    """Convierte un valor entero con validación explícita."""

    text = _text(value)

    if not text:
        if nullable:
            return None

        raise ValueError(
            f"{field_name}: se esperaba un entero y se recibió vacío."
        )

    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(
            f"{field_name}: valor entero inválido: {text!r}"
        ) from exc


def _parse_decimal(
    value: object,
    field_name: str,
) -> Decimal:
    """
    Convierte un precio a Decimal.

    Se homologa coma decimal a punto antes de la conversión.
    """

    text = _text(value).replace(",", ".")

    if not text:
        raise ValueError(
            f"{field_name}: el valor monetario está vacío."
        )

    try:
        decimal_value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(
            f"{field_name}: valor decimal inválido: {text!r}"
        ) from exc

    return decimal_value.quantize(
        Decimal("0.01")
    )


def _normalize_uuid(value: object) -> str:
    """Valida y normaliza un UUID de pasajero."""

    text = _text(value)

    try:
        return str(UUID(text))
    except ValueError as exc:
        raise ValueError(
            f"passenger_id inválido: {text!r}"
        ) from exc


def _normalize_gender(value: object) -> str:
    """Homologa las variantes de género a M, F o X."""

    normalized = _text(value).casefold()

    try:
        return GENDER_MAP[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Género no reconocido: {value!r}"
        ) from exc


def _resolve_temporal_fields(
    row: pd.Series,
) -> TemporalResolution:
    """
    Resuelve salida, llegada y reserva de una fila conjuntamente.

    No se transforman las tres columnas de forma independiente porque hacerlo
    perdería las relaciones temporales que permiten resolver ambigüedades.
    """

    record_id = _text(row["record_id"])

    status = (
        _text(row["status"])
        .upper()
    )

    departure_candidates = _parse_date_candidates(
        row["departure_datetime"]
    )

    booking_candidates = _parse_date_candidates(
        row["booking_datetime"]
    )

    if not departure_candidates:
        raise ValueError(
            f"record_id={record_id}: "
            "departure_datetime no tiene una interpretación válida."
        )

    if not booking_candidates:
        raise ValueError(
            f"record_id={record_id}: "
            "booking_datetime no tiene una interpretación válida."
        )

    valid_combinations: list[tuple] = []


    # -------------------------------------------------------------------------
    # Vuelos cancelados
    # -------------------------------------------------------------------------

    if status == "CANCELLED":

        if not _is_blank(row["arrival_datetime"]):
            raise ValueError(
                f"record_id={record_id}: "
                "un vuelo CANCELLED contiene arrival_datetime."
            )

        if not _is_blank(row["duration_min"]):
            raise ValueError(
                f"record_id={record_id}: "
                "un vuelo CANCELLED contiene duration_min."
            )

        if not _is_blank(row["delay_min"]):
            raise ValueError(
                f"record_id={record_id}: "
                "un vuelo CANCELLED contiene delay_min."
            )

        for departure in departure_candidates:
            for booking in booking_candidates:

                booking_lead_days = (
                    departure.value - booking.value
                ).total_seconds() / 86400

                if not (
                    BOOKING_LEAD_MIN_DAYS
                    <= booking_lead_days
                    <= BOOKING_LEAD_MAX_DAYS
                ):
                    continue

                # Para cancelados no existe llegada con la que comparar.
                # Se prioriza la interpretación convencional de la fuente.
                score = (
                    departure.preference
                    + booking.preference,
                    departure.preference,
                    booking.preference,
                    departure.value,
                    booking.value,
                )

                valid_combinations.append(
                    (
                        score,
                        departure.value,
                        None,
                        booking.value,
                        None,
                        booking_lead_days,
                    )
                )


    # -------------------------------------------------------------------------
    # Vuelos no cancelados
    # -------------------------------------------------------------------------

    else:

        arrival_candidates = _parse_date_candidates(
            row["arrival_datetime"]
        )

        if not arrival_candidates:
            raise ValueError(
                f"record_id={record_id}: "
                "un vuelo no cancelado no tiene llegada válida."
            )

        duration = _parse_int(
            row["duration_min"],
            "duration_min",
        )

        delay = _parse_int(
            row["delay_min"],
            "delay_min",
        )

        for departure in departure_candidates:
            for arrival in arrival_candidates:

                if arrival.value < departure.value:
                    continue

                elapsed_minutes = (
                    arrival.value - departure.value
                ).total_seconds() / 60

                timing_residual = (
                    elapsed_minutes
                    - (duration + delay)
                )

                if not (
                    TIMING_RESIDUAL_MIN_MINUTES
                    <= timing_residual
                    <= TIMING_RESIDUAL_MAX_MINUTES
                ):
                    continue

                for booking in booking_candidates:

                    if booking.value > departure.value:
                        continue

                    booking_lead_days = (
                        departure.value - booking.value
                    ).total_seconds() / 86400

                    if not (
                        BOOKING_LEAD_MIN_DAYS
                        <= booking_lead_days
                        <= BOOKING_LEAD_MAX_DAYS
                    ):
                        continue

                    # Primera prioridad:
                    # menor diferencia respecto a duración + retraso.
                    #
                    # Si persiste el empate:
                    # menor cantidad de interpretaciones alternativas.
                    #
                    # Luego se prioriza específicamente DD/MM para salida.
                    score = (
                        abs(timing_residual),
                        departure.preference
                        + arrival.preference
                        + booking.preference,
                        departure.preference,
                        booking.preference,
                        arrival.preference,
                        departure.value,
                        booking.value,
                        arrival.value,
                    )

                    valid_combinations.append(
                        (
                            score,
                            departure.value,
                            arrival.value,
                            booking.value,
                            timing_residual,
                            booking_lead_days,
                        )
                    )


    if not valid_combinations:
        raise ValueError(
            f"record_id={record_id}: "
            "no existe una combinación temporal consistente."
        )

    valid_combinations.sort(
        key=lambda item: item[0]
    )

    (
        _,
        departure,
        arrival,
        booking,
        timing_residual,
        booking_lead_days,
    ) = valid_combinations[0]

    return TemporalResolution(
        departure=departure,
        arrival=arrival,
        booking=booking,
        candidate_count=len(valid_combinations),
        timing_residual_minutes=timing_residual,
        booking_lead_days=booking_lead_days,
    )


def _transform_record(
    row: pd.Series,
) -> tuple[dict[str, object], TemporalResolution]:
    """Transforma y valida un registro completo."""

    record_id = _parse_int(
        row["record_id"],
        "record_id",
    )

    if record_id <= 0:
        raise ValueError(
            f"record_id inválido: {record_id}"
        )


    # -------------------------------------------------------------------------
    # Aerolínea y vuelo
    # -------------------------------------------------------------------------

    airline_code = (
        _text(row["airline_code"])
        .upper()
    )

    if airline_code not in AIRLINE_NAMES:
        raise ValueError(
            f"record_id={record_id}: "
            f"aerolínea desconocida {airline_code!r}."
        )

    airline_name = AIRLINE_NAMES[
        airline_code
    ]

    source_airline_name = _text(
        row["airline_name"]
    )

    if (
        source_airline_name.casefold()
        != airline_name.casefold()
    ):
        raise ValueError(
            f"record_id={record_id}: "
            "airline_code y airline_name son inconsistentes."
        )

    flight_number = (
        _text(row["flight_number"])
        .upper()
    )

    if not flight_number.startswith(
        airline_code
    ):
        raise ValueError(
            f"record_id={record_id}: "
            "flight_number no corresponde con airline_code."
        )


    # -------------------------------------------------------------------------
    # Aeropuertos
    # -------------------------------------------------------------------------

    origin_airport = (
        _text(row["origin_airport"])
        .upper()
    )

    destination_airport = (
        _text(row["destination_airport"])
        .upper()
    )

    if len(origin_airport) != 3:
        raise ValueError(
            f"record_id={record_id}: "
            "origin_airport debe tener tres caracteres."
        )

    if len(destination_airport) != 3:
        raise ValueError(
            f"record_id={record_id}: "
            "destination_airport debe tener tres caracteres."
        )

    if origin_airport == destination_airport:
        raise ValueError(
            f"record_id={record_id}: "
            "origen y destino no pueden ser iguales."
        )


    # -------------------------------------------------------------------------
    # Estado y fechas
    # -------------------------------------------------------------------------

    status = (
        _text(row["status"])
        .upper()
    )

    if status not in VALID_STATUSES:
        raise ValueError(
            f"record_id={record_id}: "
            f"estado desconocido {status!r}."
        )

    temporal = _resolve_temporal_fields(
        row
    )


    # -------------------------------------------------------------------------
    # Duración, retraso y asiento
    # -------------------------------------------------------------------------

    duration_min = _parse_int(
        row["duration_min"],
        "duration_min",
        nullable=True,
    )

    delay_min = _parse_int(
        row["delay_min"],
        "delay_min",
        nullable=True,
    )

    seat = (
        _text(row["seat"])
        .upper()
        or None
    )

    if status == "CANCELLED":

        if duration_min is not None:
            raise ValueError(
                f"record_id={record_id}: "
                "CANCELLED debe tener duración nula."
            )

        if delay_min is not None:
            raise ValueError(
                f"record_id={record_id}: "
                "CANCELLED debe tener retraso nulo."
            )

    else:

        if duration_min is None or duration_min <= 0:
            raise ValueError(
                f"record_id={record_id}: "
                "la duración debe ser positiva."
            )

        if delay_min is None or delay_min < 0:
            raise ValueError(
                f"record_id={record_id}: "
                "el retraso debe ser no negativo."
            )

        if status == "DELAYED" and delay_min <= 0:
            raise ValueError(
                f"record_id={record_id}: "
                "DELAYED debe tener retraso positivo."
            )

        if (
            status in {"ON_TIME", "DIVERTED"}
            and delay_min != 0
        ):
            raise ValueError(
                f"record_id={record_id}: "
                f"{status} debe tener retraso igual a cero."
            )


    # -------------------------------------------------------------------------
    # Pasajero
    # -------------------------------------------------------------------------

    passenger_id = _normalize_uuid(
        row["passenger_id"]
    )

    passenger_gender = _normalize_gender(
        row["passenger_gender"]
    )

    passenger_age = _parse_int(
        row["passenger_age"],
        "passenger_age",
        nullable=True,
    )

    if (
        passenger_age is not None
        and not 0 <= passenger_age <= 120
    ):
        raise ValueError(
            f"record_id={record_id}: "
            "edad fuera del rango permitido."
        )

    passenger_nationality = (
        _text(
            row["passenger_nationality"]
        ).upper()
        or None
    )

    if (
        passenger_nationality is not None
        and len(passenger_nationality) != 2
    ):
        raise ValueError(
            f"record_id={record_id}: "
            "nacionalidad inválida."
        )


    # -------------------------------------------------------------------------
    # Venta y pago
    # -------------------------------------------------------------------------

    sales_channel = (
        _text(row["sales_channel"])
        .upper()
        or "DESCONOCIDO"
    )

    payment_method = (
        _text(row["payment_method"])
        .upper()
    )

    if not payment_method:
        raise ValueError(
            f"record_id={record_id}: "
            "payment_method está vacío."
        )


    # -------------------------------------------------------------------------
    # Precios
    # -------------------------------------------------------------------------

    ticket_price = _parse_decimal(
        row["ticket_price"],
        "ticket_price",
    )

    ticket_price_usd_est = _parse_decimal(
        row["ticket_price_usd_est"],
        "ticket_price_usd_est",
    )

    if ticket_price < 0:
        raise ValueError(
            f"record_id={record_id}: "
            "ticket_price no puede ser negativo."
        )

    if ticket_price_usd_est < 0:
        raise ValueError(
            f"record_id={record_id}: "
            "ticket_price_usd_est no puede ser negativo."
        )

    currency = (
        _text(row["currency"])
        .upper()
    )

    if len(currency) != 3:
        raise ValueError(
            f"record_id={record_id}: "
            "currency debe tener tres caracteres."
        )


    # -------------------------------------------------------------------------
    # Equipaje
    # -------------------------------------------------------------------------

    bags_total = _parse_int(
        row["bags_total"],
        "bags_total",
    )

    bags_checked = _parse_int(
        row["bags_checked"],
        "bags_checked",
    )

    if bags_total < 0 or bags_checked < 0:
        raise ValueError(
            f"record_id={record_id}: "
            "el equipaje no puede ser negativo."
        )

    if bags_checked > bags_total:
        raise ValueError(
            f"record_id={record_id}: "
            "bags_checked no puede superar bags_total."
        )


    transformed = {
        "record_id": record_id,
        "airline_code": airline_code,
        "airline_name": airline_name,
        "flight_number": flight_number,
        "origin_airport": origin_airport,
        "destination_airport": destination_airport,
        "departure_datetime": temporal.departure,
        "arrival_datetime": temporal.arrival,
        "duration_min": duration_min,
        "status": status,
        "delay_min": delay_min,
        "aircraft_type": (
            _text(row["aircraft_type"])
            .upper()
        ),
        "cabin_class": (
            _text(row["cabin_class"])
            .upper()
        ),
        "seat": seat,
        "passenger_id": passenger_id,
        "passenger_gender": passenger_gender,
        "passenger_age": passenger_age,
        "passenger_nationality": passenger_nationality,
        "booking_datetime": temporal.booking,
        "sales_channel": sales_channel,
        "payment_method": payment_method,
        "ticket_price": ticket_price,
        "currency": currency,
        "ticket_price_usd_est": ticket_price_usd_est,
        "bags_total": bags_total,
        "bags_checked": bags_checked,
    }

    return transformed, temporal


def transform_dataset(
    raw_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, TransformationReport]:
    """
    Transforma el dataset completo.

    La función no modifica el DataFrame recibido.
    """

    transformed_rows: list[
        dict[str, object]
    ] = []

    temporal_unique = 0
    temporal_multiple = 0
    max_temporal_candidates = 0

    for _, row in raw_dataframe.iterrows():

        record_id = _text(
            row.get("record_id", "")
        )

        try:
            transformed, temporal = (
                _transform_record(row)
            )
        except Exception as exc:
            raise ValueError(
                f"Error transformando record_id={record_id}: {exc}"
            ) from exc

        transformed_rows.append(
            transformed
        )

        if temporal.candidate_count == 1:
            temporal_unique += 1
        else:
            temporal_multiple += 1

        max_temporal_candidates = max(
            max_temporal_candidates,
            temporal.candidate_count,
        )

    dataframe = pd.DataFrame(
        transformed_rows
    )

    # Tipos enteros anulables.
    for column in (
        "duration_min",
        "delay_min",
        "passenger_age",
    ):
        dataframe[column] = (
            dataframe[column]
            .astype("Int64")
        )

    # Textos anulables.
    #
    # Pandas 3 puede representar los valores faltantes de columnas de texto
    # mediante NaN aunque durante la transformación se haya utilizado None.
    # Antes de entregar el DataFrame a la fase de carga se fuerza dtype object
    # y se recupera explícitamente None como representación nativa.
    for column in (
        "seat",
        "passenger_nationality",
    ):
        dataframe[column] = (
            dataframe[column]
            .astype(object)
        )

        dataframe.loc[
            dataframe[column].isna(),
            column,
        ] = None

    # Fechas homogéneas.
    for column in (
        "departure_datetime",
        "arrival_datetime",
        "booking_datetime",
    ):
        dataframe[column] = pd.to_datetime(
            dataframe[column]
        )

    report = TransformationReport(
        rows_received=len(
            raw_dataframe
        ),
        rows_transformed=len(
            dataframe
        ),
        temporal_unique=temporal_unique,
        temporal_multiple=temporal_multiple,
        max_temporal_candidates=max_temporal_candidates,
    )

    return dataframe, report
