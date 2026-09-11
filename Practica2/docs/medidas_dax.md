# Medidas DAX - Práctica 2

## Seminario de Sistemas 2

Este documento describe las medidas DAX implementadas en el modelo de Power BI de la Práctica 2.

Las medidas se almacenan en la tabla lógica:

`00 Medidas`

El objetivo de esta tabla es centralizar las métricas del modelo y evitar que las medidas queden distribuidas entre las diferentes dimensiones y la tabla de hechos.

---

# 1. Contexto del modelo

La fuente de datos utilizada es el Data Warehouse construido en la Práctica 1:

`SS2_Practica1_VuelosDW`

La tabla de hechos principal es:

`dw FactVueloPasajero`

El grano de esta tabla corresponde a un registro fuente de un pasajero asociado con una reserva y una ocurrencia de vuelo.

Por esta razón, la medida `Total Registros` representa registros pasajero-vuelo y no debe interpretarse automáticamente como cantidad de vuelos físicos distintos.

---

# 2. Medidas generales

## 2.1 Total Registros

### Fórmula

```DAX
Total Registros =
SUM('dw FactVueloPasajero'[cantidad_registros])
```

### Descripción

Calcula la cantidad total de registros almacenados en la tabla de hechos.

La columna `cantidad_registros` contiene el valor 1 para cada fila válida del modelo dimensional.

### Interpretación

Permite conocer la cantidad de registros pasajero-vuelo que participan en el contexto de filtro actual.

### Valor general validado

`10,000`

### Formato

Número entero.

---

## 2.2 Ingresos USD

### Fórmula

```DAX
Ingresos USD =
SUM('dw FactVueloPasajero'[precio_usd_estimado])
```

### Descripción

Suma el precio estimado en dólares estadounidenses de todos los registros incluidos en el contexto de filtro.

### Interpretación

Representa el valor económico total asociado con los boletos registrados en el Data Warehouse.

Puede analizarse por:

- período;
- aerolínea;
- canal de venta;
- clase de cabina;
- aeropuerto;
- otros filtros del modelo.

### Valor general validado

`$770,024.71`

### Formato

Moneda USD, dos decimales.

---

## 2.3 Ticket Promedio USD

### Fórmula

```DAX
Ticket Promedio USD =
DIVIDE(
    [Ingresos USD],
    [Total Registros],
    0
)
```

### Descripción

Calcula el ingreso promedio en dólares por registro de la tabla de hechos.

Se utiliza `DIVIDE` en lugar del operador `/` para manejar de forma segura contextos en los cuales el denominador pudiera ser cero.

### Interpretación

Permite analizar el valor promedio de los boletos dentro del contexto seleccionado.

### Valor general validado

`$77.00`

### Formato

Moneda USD, dos decimales.

---

## 2.4 Retraso Promedio Min

### Fórmula

```DAX
Retraso Promedio Min =
AVERAGE(
    'dw FactVueloPasajero'[retraso_min]
)
```

### Descripción

Calcula el retraso promedio, expresado en minutos, de los registros que poseen un valor de retraso.

### Consideración

Los vuelos cancelados tienen `retraso_min` nulo. La función `AVERAGE` ignora los valores `BLANK`, por lo que dichos registros no son considerados como retrasos de cero minutos.

### Interpretación

Permite comparar el desempeño operativo entre períodos, aerolíneas y otros segmentos.

### Valor general validado

`26.07 minutos`

### Formato

Número decimal, dos decimales.

---

## 2.5 Pasajeros Únicos

### Fórmula

```DAX
Pasajeros Únicos =
DISTINCTCOUNT(
    'dw FactVueloPasajero'[id_pasajero]
)
```

### Descripción

Cuenta la cantidad de identificadores de pasajeros distintos presentes en el contexto actual.

### Interpretación

Permite conocer cuántos pasajeros únicos están representados en los datos seleccionados.

### Valor general validado

`10,000`

### Formato

Número entero.

---

# 3. Medidas de estado de vuelo

## 3.1 Total Registros Sin Filtro Estado

### Fórmula

```DAX
Total Registros Sin Filtro Estado =
CALCULATE(
    [Total Registros],
    REMOVEFILTERS('dw DimEstadoVuelo')
)
```

### Descripción

Calcula el total de registros eliminando exclusivamente cualquier filtro aplicado sobre la dimensión de estado del vuelo.

### Interpretación

Esta medida se utiliza como denominador para calcular indicadores de participación por estado, como puntualidad y cancelación.

Los filtros de otras dimensiones, como año, aerolínea, origen o destino, continúan aplicándose.

---

## 3.2 Registros Puntuales

### Fórmula

```DAX
Registros Puntuales =
CALCULATE(
    [Total Registros],
    'dw DimEstadoVuelo'[estado_vuelo] = "ON_TIME"
)
```

### Descripción

Calcula la cantidad de registros cuyo estado de vuelo es `ON_TIME`.

### Interpretación

Representa el volumen de registros asociados con operaciones consideradas puntuales.

### Valor general validado

`7,278`

### Formato

Número entero.

---

## 3.3 % Puntualidad

### Fórmula

```DAX
% Puntualidad =
DIVIDE(
    [Registros Puntuales],
    [Total Registros Sin Filtro Estado],
    0
)
```

### Descripción

Calcula la proporción de registros con estado `ON_TIME` respecto del total de registros del contexto actual.

### Interpretación

Es el indicador principal utilizado para evaluar el nivel de puntualidad y constituye la base del KPI con semáforo del dashboard.

### Valor general validado

`72.78 %`

### Formato

Porcentaje, dos decimales.

---

## 3.4 Registros Cancelados

### Fórmula

```DAX
Registros Cancelados =
CALCULATE(
    [Total Registros],
    'dw DimEstadoVuelo'[estado_vuelo] = "CANCELLED"
)
```

### Descripción

Calcula la cantidad de registros asociados con vuelos cuyo estado es `CANCELLED`.

### Valor general validado

`560`

### Formato

Número entero.

---

## 3.5 % Cancelación

### Fórmula

```DAX
% Cancelación =
DIVIDE(
    [Registros Cancelados],
    [Total Registros Sin Filtro Estado],
    0
)
```

### Descripción

Calcula la proporción de registros cancelados respecto del total del contexto actual.

### Interpretación

Permite evaluar la incidencia de cancelaciones y comparar su comportamiento entre períodos, aerolíneas y destinos.

### Valor general validado

`5.60 %`

### Formato

Porcentaje, dos decimales.

---

# 4. KPI de puntualidad

## 4.1 Meta Puntualidad

### Fórmula

```DAX
Meta Puntualidad =
0.80
```

### Descripción

Define una meta interna de puntualidad del 80 % utilizada como referencia para el dashboard.

### Importante

El valor del 80 % se definió como meta analítica interna de esta práctica y no pretende representar un estándar oficial o universal de la industria aeronáutica.

### Formato

Porcentaje, dos decimales.

---

## 4.2 Desviación Puntualidad

### Fórmula

```DAX
Desviación Puntualidad =
[% Puntualidad] - [Meta Puntualidad]
```

### Descripción

Calcula la diferencia entre la puntualidad obtenida y la meta establecida.

### Interpretación

- Valor positivo: la puntualidad supera la meta.
- Valor igual a cero: la puntualidad alcanza exactamente la meta.
- Valor negativo: la puntualidad se encuentra por debajo de la meta.

### Valor general validado

`-7.22 %`

### Formato

Porcentaje, dos decimales.

---

## 4.3 Estado Puntualidad

### Fórmula

```DAX
Estado Puntualidad =
SWITCH(
    TRUE(),
    [% Puntualidad] >= 0.80, "VERDE",
    [% Puntualidad] >= 0.70, "AMARILLO",
    "ROJO"
)
```

### Descripción

Clasifica dinámicamente el nivel de puntualidad utilizando tres rangos.

| Estado | Condición |
|---|---|
| VERDE | Puntualidad mayor o igual al 80 % |
| AMARILLO | Puntualidad mayor o igual al 70 % y menor al 80 % |
| ROJO | Puntualidad menor al 70 % |

### Interpretación

El indicador permite identificar visualmente si el desempeño se encuentra dentro, cerca o por debajo de la meta establecida.

### Estado general validado

`AMARILLO`

---

## 4.4 Color Puntualidad

### Fórmula

```DAX
Color Puntualidad =
SWITCH(
    [Estado Puntualidad],
    "VERDE", "#2E7D32",
    "AMARILLO", "#F9A825",
    "ROJO", "#C62828",
    "#808080"
)
```

### Descripción

Devuelve el código hexadecimal utilizado por el formato condicional del KPI.

### Correspondencia

| Estado | Color |
|---|---|
| VERDE | `#2E7D32` |
| AMARILLO | `#F9A825` |
| ROJO | `#C62828` |
| Otro | `#808080` |

### Uso

Esta medida se utiliza como valor de campo para modificar dinámicamente el color de fondo del KPI de puntualidad.

---

## 4.5 KPI Puntualidad

### Fórmula

```DAX
KPI Puntualidad =
FORMAT(
    [% Puntualidad],
    "0.00 %"
)
    & " - "
    & [Estado Puntualidad]
```

### Descripción

Construye la etiqueta textual utilizada por la tarjeta principal del KPI.

Combina:

- porcentaje de puntualidad;
- estado calculado mediante el semáforo.

### Valor general validado

`72.78 % - AMARILLO`

### Comportamiento dinámico

El valor se recalcula cuando el usuario modifica los filtros del dashboard.

Durante la validación interactiva se utilizó una combinación de filtros que produjo:

`66.67 % - ROJO`

Esto demuestra que el KPI responde al contexto de filtro.

---

# 5. Medidas de equipaje

## 5.1 Equipaje Promedio

### Fórmula

```DAX
Equipaje Promedio =
AVERAGE(
    'dw FactVueloPasajero'[maletas_total]
)
```

### Descripción

Calcula la cantidad promedio de maletas totales asociadas con los registros del contexto actual.

### Interpretación

Se utiliza para analizar el comportamiento de equipaje entre diferentes clases de cabina y otros segmentos.

### Formato

Número decimal, dos decimales.

---

## 5.2 Maletas Facturadas Promedio

### Fórmula

```DAX
Maletas Facturadas Promedio =
AVERAGE(
    'dw FactVueloPasajero'[maletas_facturadas]
)
```

### Descripción

Calcula el promedio de maletas facturadas por registro.

### Interpretación

Permite comparar la cantidad total de equipaje con la cantidad de equipaje efectivamente facturado.

### Formato

Número decimal, dos decimales.

---

# 6. Resumen de medidas

| Medida | Tipo de indicador | Uso principal |
|---|---|---|
| Total Registros | Volumen | Cantidad de registros pasajero-vuelo |
| Ingresos USD | Financiero | Ingreso total estimado |
| Ticket Promedio USD | Financiero | Valor promedio del boleto |
| Retraso Promedio Min | Operativo | Retraso medio |
| Pasajeros Únicos | Volumen | Cantidad de pasajeros distintos |
| Total Registros Sin Filtro Estado | Auxiliar | Denominador para indicadores de estado |
| Registros Puntuales | Operativo | Registros `ON_TIME` |
| % Puntualidad | KPI | Nivel de puntualidad |
| Registros Cancelados | Operativo | Registros `CANCELLED` |
| % Cancelación | KPI | Tasa de cancelación |
| Meta Puntualidad | KPI | Meta interna de referencia |
| Desviación Puntualidad | KPI | Diferencia contra la meta |
| Estado Puntualidad | KPI | Estado del semáforo |
| Color Puntualidad | Auxiliar | Formato condicional |
| KPI Puntualidad | KPI | Etiqueta dinámica del indicador |
| Equipaje Promedio | Operativo | Promedio de equipaje total |
| Maletas Facturadas Promedio | Operativo | Promedio de equipaje facturado |

---

# 7. Validación de las medidas

Con el conjunto completo de datos se comprobaron los siguientes resultados:

| Indicador | Resultado |
|---|---:|
| Total Registros | 10,000 |
| Ingresos USD | $770,024.71 |
| Ticket Promedio USD | $77.00 |
| Retraso Promedio Min | 26.07 |
| Pasajeros Únicos | 10,000 |
| Registros Puntuales | 7,278 |
| % Puntualidad | 72.78 % |
| Registros Cancelados | 560 |
| % Cancelación | 5.60 % |
| Meta Puntualidad | 80.00 % |
| Desviación Puntualidad | -7.22 % |
| Estado Puntualidad | AMARILLO |

Estos resultados se utilizaron como valores de control durante la construcción y validación del dashboard.

La cantidad de 10,000 registros y los 560 registros cancelados son consistentes con las validaciones realizadas sobre el Data Warehouse construido en la Práctica 1.

---

# 8. Uso dentro del dashboard

Las medidas se utilizan principalmente en dos páginas de análisis.

## 8.1 Resumen Ejecutivo

Incluye indicadores y visualizaciones relacionadas con:

- total de registros;
- ingresos;
- puntualidad;
- cancelación;
- retraso promedio;
- evolución temporal;
- puntualidad por aerolínea;
- principales destinos;
- distribución de estados.

Los principales segmentadores de esta página son:

- año;
- aerolínea;
- destino.

---

## 8.2 Análisis Operativo y Comercial

Incluye indicadores y visualizaciones relacionadas con:

- ingresos;
- ticket promedio;
- pasajeros únicos;
- retraso promedio;
- ingresos por aerolínea;
- ingresos por canal de venta;
- ticket promedio por clase de cabina;
- retraso promedio por aerolínea;
- equipaje promedio por clase de cabina.

Los principales segmentadores de esta página son:

- año;
- aerolínea;
- clase de cabina.

---

# 9. Comportamiento frente a filtros

Las medidas DAX se evalúan dentro del contexto de filtro definido por Power BI.

Esto permite que los indicadores cambien dinámicamente al utilizar segmentadores de:

- año;
- aerolínea;
- aeropuerto de origen;
- aeropuerto de destino;
- estado de vuelo;
- clase de cabina;
- canal de venta.

La medida `Total Registros Sin Filtro Estado` constituye una excepción intencional, ya que elimina únicamente los filtros provenientes de `dw DimEstadoVuelo`.

Esto permite calcular correctamente porcentajes como `% Puntualidad` y `% Cancelación` sin eliminar el contexto correspondiente a las demás dimensiones.

---

# 10. Consideraciones de interpretación

## Total Registros

`Total Registros` no representa necesariamente la cantidad de vuelos físicos diferentes.

El grano de `dw FactVueloPasajero` corresponde a registros pasajero-vuelo, por lo que esta medida debe interpretarse como cantidad de registros analizados.

## Retraso Promedio

Los registros cancelados pueden contener `BLANK` en `retraso_min`.

DAX excluye automáticamente estos valores al calcular `AVERAGE`, evitando interpretar una cancelación como un vuelo con cero minutos de retraso.

## Puntualidad

El KPI de puntualidad se basa en los registros cuyo estado es `ON_TIME`.

La meta del 80 % y los rangos del semáforo fueron definidos específicamente como criterio analítico para esta práctica.

## Ingresos

La medida `Ingresos USD` utiliza `precio_usd_estimado`, permitiendo analizar conjuntamente registros que originalmente pudieron estar expresados en diferentes monedas.

---

# 11. Conclusión

Las medidas DAX implementadas permiten transformar el modelo dimensional en indicadores orientados al análisis operativo y comercial.

Las métricas cubren principalmente cuatro áreas:

1. volumen de registros y pasajeros;
2. desempeño económico;
3. puntualidad y cancelaciones;
4. comportamiento operativo y equipaje.

El uso de medidas en lugar de agregaciones manuales permite que todos los indicadores respondan de forma consistente al contexto de filtros, relaciones y segmentadores del modelo de Power BI.