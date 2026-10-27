# Metodología de pronóstico retrospectivo con origen móvil

## Variable pronosticada y fuentes

Definimos como objetivo la proporción diaria de viajes observados con tarifa de **USD 20 o más**. La población evaluada es la muestra de noviembre de 2022 compuesta por 6,449 viajes, cuyas predicciones individuales fueron obtenidas mediante `LINEAR_REG` y `LOGISTIC_REG` entrenados con datos previos a noviembre.

El ejercicio no predice un precio individual ni la cantidad de taxis que circulará al día siguiente. Pronostica una **tasa diaria agregada** a partir de información histórica disponible al momento del origen.

## Ventana temporal y horizonte

Para cada fecha objetivo utilizamos exclusivamente las **siete fechas calendario anteriores**. El horizonte es de **un día**: por ejemplo, el 7 de noviembre es el origen del pronóstico del 8 de noviembre, calculado con la actividad del 1 al 7. Después desplazamos el origen al 8 para pronosticar el 9 y repetimos hasta el pronóstico del 30.

En BigQuery, el encuadre temporal se implementó mediante `ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING`. La consulta también verifica continuidad diaria, inicio y fin del historial y el número de fechas por ventana.

## Métodos comparados

**Pronóstico derivado de regresión lineal:** proporción de viajes de los siete días previos cuya tarifa fue estimada por `modelo_lineal` por encima del umbral. **Pronóstico derivado de regresión logística:** proporción de viajes históricos clasificados como positivos por `modelo_logistico`. **Referencia histórica:** proporción real observada en los siete días anteriores, utilizada como método ingenuo de persistencia.

Las tres proporciones se ponderan por cantidad de viajes de la ventana. La etiqueta verdadera del día pronosticado interviene solamente para calcular el error, después de obtenido el pronóstico.

## Control temporal y validación

En la ejecución obtuvimos 23 objetivos, del 8 al 30 de noviembre, con **cero ventanas incorrectas** y **cero tasas inválidas**. La construcción excluye la fecha objetivo de la ventana, y los modelos subyacentes no utilizan registros de noviembre en su entrenamiento.

Los modelos permanecen fijos. No ejecutamos reentrenamiento en cada origen ni desarrollamos modelos específicos de series temporales; los pronósticos agregados derivan de sus predicciones históricas. La muestra determinista aproximada de 0.2 % y las variables retrospectivas de las predicciones individuales limitan la extrapolación a toda la población de taxis.

## Evaluación cuantitativa

La comparación utiliza MAE, RMSE y sesgo firmado de las tasas diarias, expresados en puntos porcentuales. Las tres series se evalúan sobre las mismas 23 fechas. Las consultas que definen la metodología son `sql/05_dashboard/03_rolling_forecast_origen_movil.sql` y `04_rolling_forecast_metricas.sql`; sus resultados se desarrollan en [Resultados del Rolling Forecast](RESULTADOS_ROLLING_FORECAST_20261027.md).
