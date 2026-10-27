# Decisión de arquitectura predictiva: regresión lineal y logística

## Contexto de la decisión

Inicialmente consideramos dos regresores: un modelo lineal y un árbol con boosting. La regresión lineal concluyó su entrenamiento. El intento de entrenar `BOOSTED_TREE_REGRESSOR` no permitió obtener un modelo válido: tres trabajos fueron rechazados por `bytesBilledLimitExceeded`, con límites establecidos en 500 MB, 1 GB y 10 GB. Esos intentos se conservan como historial técnico, no como modelos adicionales evaluados.

## Solución implementada

Para mantener dos algoritmos diferentes y controlar la complejidad de ejecución, seleccionamos `LINEAR_REG` y `LOGISTIC_REG` dentro de BigQuery ML. El primero estima la tarifa en USD. El segundo calcula la clase y probabilidad de una tarifa de al menos USD 20. Ambos se basan en el mismo esquema de características y la misma división temporal, con noviembre reservado como conjunto externo de prueba.

La comparación directa entre MAE y ROC-AUC sería metodológicamente inválida. Por ello añadimos una segunda comparación en una tarea común: clasificamos también la predicción monetaria de la regresión lineal utilizando el umbral de USD 20 y calculamos Accuracy, Precision, Recall y F1 para ambos algoritmos.

## Resultado de la decisión

La regresión logística mostró F1 de 75.15 % y recall de 66.43 %, frente a F1 de 73.07 % y recall de 63.40 % de la lineal discretizada. Para estimar importes exactos, el modelo lineal alcanzó MAE de USD 4.95. El modelo Boosted Tree no se incorpora a estas comparaciones porque no fue creado correctamente.

## Alcance experimental

Las configuraciones utilizadas establecieron máximos de iteraciones, regularización L2 y parada temprana en logística. Estas decisiones son explícitas y reproducibles, pero no equivalen a una búsqueda experimental de hiperparámetros de múltiples configuraciones exitosas. Del mismo modo, la opción `DATA_SPLIT_EVAL_FRACTION` aparece únicamente en el diseño del entrenamiento Boosted Tree que no concluyó; los modelos finales utilizaron `CUSTOM`.
