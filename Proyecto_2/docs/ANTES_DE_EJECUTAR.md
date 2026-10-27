# Entorno de procesamiento, seguridad y control de costos

## Plataforma utilizada

Desarrollamos la solución en Google Cloud mediante BigQuery y BigQuery ML. Las operaciones se realizaron en el proyecto `ss2-p2-g6-2026-nc-1026`, dataset `ss2_proyecto2_g6`, ubicado en `US`. La fuente pública, con la que comparte región, fue `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`.

La separación del proyecto de trabajo permitió aislar los recursos utilizados en el análisis. La facturación estaba habilitada y se establecieron alertas presupuestarias. Estas alertas permiten supervisar gastos, pero no representan un límite de costo obligatorio.

## Estrategia de eficiencia

En la fase analítica utilizamos límites de bytes facturables por consulta y consultas de validación previas a la materialización. Se comprobaron conteos, sumas y resultados antes de ampliar el análisis a los modelos. Para el aprendizaje automático seleccionamos una muestra determinista aproximada de 0.2 %, preservando las tablas principales con más de 35 millones de registros para la experimentación de optimización.

Tres ensayos de entrenamiento Boosted Tree se interrumpieron con `bytesBilledLimitExceeded`. Los límites de consulta empleados no garantizaron un costo monetario máximo para el componente externo del entrenamiento, por lo que utilizamos finalmente regresión lineal y regresión logística dentro de BigQuery ML.

## Reproducibilidad y resguardo

La organización `sql/` conserva las consultas con la parametrización del proyecto y el dataset. `evidencias/logs/` contiene resultados obtenidos durante las ejecuciones y `evidencias/capturas/` las vistas del informe disponibles. La comparación de benchmark registra identificadores de trabajos, bytes procesados y la ausencia de caché; el análisis de modelos conserva tanto métricas independientes como los resultados del pronóstico con origen móvil.

Los archivos de autenticación, claves privadas y variables de entorno locales quedan fuera de la documentación y de los entregables. El acceso efectivo al informe visual depende de los permisos asociados al recurso compartido.
