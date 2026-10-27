# Informe técnico del Proyecto 2

**Procesamiento y análisis exploratorio de datos masivos en BigQuery**

**Seminario de Sistemas 2 · Grupo 6 · Segundo semestre de 2026**

**Integrantes:** Nelson Emanuel Cún Bálan — 201222010; Dámaris Magali Arce Guzmán — 202006636.

## 1. Introducción

En este proyecto analizamos los registros de taxis amarillos de Nueva York correspondientes a 2022 mediante Google BigQuery. El trabajo integra exploración estadística, depuración, optimización física de tablas, aprendizaje automático y representación visual. Nuestro objetivo fue obtener evidencia cuantitativa de la eficiencia de las consultas y estudiar la capacidad de distintos algoritmos para estimar tarifas e identificar viajes de importe elevado.

Trabajamos con la tabla pública `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`, un proyecto de Google Cloud independiente y el conjunto de datos `ss2_proyecto2_g6`, en región `US`.

## 2. Comprensión y depuración de los datos

El conteo realizado sobre la fuente arrojó 36,256,539 registros. La inspección detectó observaciones con distancias no positivas (511,442), tarifas no positivas (241,621), duraciones inválidas (30,368), marcas temporales fuera de 2022 (556) y pasajeros nulos (1,241,840). Esas categorías se superponen y, por tanto, sus valores no deben sumarse como recuento de filas excluidas.

Aplicamos reglas de consistencia que generaron dos tablas comparables de 35,526,984 viajes cada una. Los agregados de conteos e importes de ambas tablas coincidieron en las comprobaciones ejecutadas. Las distribuciones mensuales, las zonas de origen y las horas UTC permitieron identificar diferencias de demanda y anomalías de cobertura. Diciembre mostró apenas 57 registros en la exploración filtrada, por lo que evitamos utilizarlo como período representativo.

## 3. Transformación y optimización en BigQuery

Construimos una tabla estándar y otra organizada por particiones de fecha (`pickup_date`) y clustering por zonas de origen y destino (`pickup_location_id`, `dropoff_location_id`). Ejecutamos la misma consulta analítica sobre ambas variantes, con la caché deshabilitada.

| Métrica | Estándar | Optimizada |
|---|---:|---:|
| Bytes procesados | 1,024,262,123 | 93,941,224 |
| Bytes facturables reportados | 1,024,458,752 | 94,371,840 |
| Latencia registrada | 321 ms | 305 ms |
| Slot-ms | 5,166 | 257 |

Los resultados arrojaron 138,162 viajes y suma tarifaria de 1,722,680.9 en ambas consultas. La disminución de bytes procesados fue de 90.83 %; en cambio, la diferencia de latencia fue menor. Interpretamos la optimización como una mejora significativa de eficiencia de lectura, no como una aceleración del mismo porcentaje.

## 4. Ingeniería de características y modelos

Materializamos 70,753 observaciones mediante muestreo determinista aproximado de 0.2 %. Dividimos cronológicamente los datos: 51,204 filas de entrenamiento inicial (enero-agosto), 13,100 de validación (septiembre-octubre) y 6,449 de prueba externa (noviembre). Después de aplicar al entrenamiento y validación el rango tarifario de USD 2 a 250, quedaron 51,199 y 13,096 filas respectivamente. No aplicamos ese filtro al conjunto de prueba.

La regresión lineal utiliza `tarifa` como variable objetivo; la regresión logística modela una etiqueta binaria de tarifa igual o superior a USD 20. En ambos casos, los predictores comprenden distancia, pasajeros, hora, día de semana, mes, proveedor, origen y destino. Excluimos las variables monetarias directamente derivadas de la tarifa para no introducir respuestas dentro de las entradas.

Empleamos división temporal interna `CUSTOM` para separar entrenamiento y validación, y mantuvimos noviembre totalmente fuera de la creación de los modelos. Reconocemos que distancia y destino realizados son datos disponibles al finalizar el trayecto; las predicciones por viaje se interpretan retrospectivamente.

| Modelo | Configuración | Resultado externo principal |
|---|---|---|
| Regresión lineal | 30 iteraciones máximas; L2 = 0.1 | MAE USD 4.9459; RMSE USD 7.3220; R² = 0.6920 |
| Regresión logística | 20 iteraciones máximas; L2 = 0.1; parada temprana | Accuracy 91.25 %; F1 75.15 %; ROC-AUC 0.9062 |

Para comparar los modelos bajo el mismo objetivo de detección de tarifas elevadas, discretizamos la estimación monetaria de la regresión lineal. La logística alcanzó F1 de 75.15 %, frente a 73.07 % de la variante lineal. Por otra parte, la regresión lineal continúa siendo necesaria cuando interesa estimar un importe en dólares.

La parametrización de ambos modelos fue explícita y basada en un compromiso entre complejidad y costo. No se ejecutó una búsqueda comparativa exhaustiva ni una segunda configuración exitosa de cada modelo. Un ensayo con Boosted Tree no concluyó por límites de bytes facturables y no forma parte de los dos modelos evaluados.

## 5. Pronóstico temporal con origen móvil

Construimos un análisis retrospectivo de la proporción diaria de tarifas de al menos USD 20. Cada predicción utiliza siete días anteriores al objetivo y un horizonte de un día. El período evaluado comprende 23 fechas del 8 al 30 de noviembre de 2022. La validación reportó cero ventanas temporales incorrectas y cero tasas fuera del rango válido.

Contrastamos la proyección de tasas históricas de clases predichas por los dos modelos con una referencia basada en tasas reales históricas. El método de referencia logró MAE de 2.2079 puntos porcentuales; los derivados de regresión logística y lineal obtuvieron 5.2465 y 5.9523, respectivamente.

El resultado muestra la persistencia de un sesgo de subestimación en las proporciones estimadas por los métodos derivados de ML. La estrategia evalúa pronósticos retrospectivos de un agregado temporal, sin reentrenamiento sucesivo de los modelos ni disponibilidad anticipada de los atributos de viajes futuros.

## 6. Visualización

El [informe interactivo](https://datastudio.google.com/reporting/45e788e9-a2c3-4606-8721-4ba456c08a19) consta de tres páginas: análisis exploratorio de meses, zonas y horas; evaluación de modelos con métricas y predicciones diarias; y Rolling Forecast con resultados a un día y comparación frente a la referencia histórica.

Las fuentes exploratorias se apoyan en una tabla agregada de 297 registros. Las demás visualizaciones consultan vistas de resultados predictivos ya materializados, lo que reduce la necesidad de procesar repetidamente la tabla original de gran volumen.

## 7. Conclusiones

1. El particionamiento y clustering disminuyeron significativamente el volumen de lectura con conservación de resultados analíticos equivalentes.
2. La clasificación logística mostró mejor F1 y recall que la regresión lineal discretizada, aunque ambos métodos subestimaron la proporción de viajes de tarifa elevada.
3. La referencia histórica superó a los pronósticos diarios derivados de ML, por lo que no interpretamos un buen desempeño por viaje como prueba de capacidad superior de pronóstico agregado.
4. La escasa cobertura de diciembre, el tamaño de la muestra para ML y la disponibilidad temporal de las características condicionan la interpretación de los resultados.
5. La evaluación de hiperparámetros se limitó a configuraciones definidas explícitamente, sin búsqueda experimental amplia; el Rolling Forecast corresponde a backtesting de modelos fijos.

## 8. Evidencia y trazabilidad

Las consultas SQL, los resultados de ejecución y las capturas disponibles acompañan el informe dentro del repositorio. Los documentos [Validación de benchmark](VALIDACION_BENCHMARK_20261026.md), [Modelado](MODELADO.md), [Rolling Forecast](RESULTADOS_ROLLING_FORECAST_20261027.md) y [Matriz de trazabilidad](MATRIZ_RUBRICA.md) amplían los métodos y permiten relacionar cada componente con sus evidencias observadas.
