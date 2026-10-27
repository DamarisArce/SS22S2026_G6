# Resultados del Rolling Forecast con origen móvil

**Validación:** 27 de octubre de 2026. **Período de prueba:** 8–30 de noviembre de 2022.

## Alcance y consistencia temporal

Evaluamos 23 pronósticos retrospectivos a un día de horizonte mediante ventanas de siete días anteriores al objetivo. La verificación SQL reportó cero ventanas incorrectas y cero tasas fuera de los límites válidos. Los modelos de regresión lineal y logística permanecieron fijos, mientras que el origen del pronóstico se desplazó diariamente.

## Resultados de error

| Método | Días evaluados | MAE (pp) | RMSE (pp) | Sesgo firmado (pp) |
|---|---:|---:|---:|---:|
| Referencia histórica | 23 | **2.2079** | **2.5633** | -0.5161 |
| Regresión logística | 23 | 5.2465 | 5.7875 | -5.2465 |
| Regresión lineal | 23 | 5.9523 | 6.4231 | -5.9523 |

La referencia histórica presentó el menor error absoluto y cuadrático. En cambio, los pronósticos derivados de ML subestimaron la proporción de tarifas elevadas: sus sesgos fueron aproximadamente -5.25 y -5.95 puntos porcentuales para logística y lineal, respectivamente.

## Interpretación de los resultados

La regresión logística había obtenido F1 de 75.15 % al clasificar viajes individuales, pero esta ventaja no se tradujo en el mejor pronóstico de la proporción diaria. La diferencia ilustra que la calidad de clasificación y la calidad de pronóstico temporal agregado son objetivos de evaluación distintos.

El resultado corresponde exclusivamente a la muestra de prueba, no a un pronóstico censal de todo el tráfico de taxis. Los valores del día objetivo no se utilizaron para construir sus propias predicciones; se incorporaron posteriormente para evaluar su error.

## Evidencia técnica

Las series y métricas se obtuvieron mediante `vw_forecast_origen_movil` y `vw_forecast_metricas`. El registro `evidencias/logs/rolling_forecast_20261027.log` conserva los conteos y valores de la evaluación. La tercera página del [dashboard](https://datastudio.google.com/reporting/45e788e9-a2c3-4606-8721-4ba456c08a19) representa gráficamente los tres métodos y la proporción real.

Esta implementación constituye un *backtesting* de origen móvil con modelos fijos; no incluye reentrenamiento en cada fecha ni extrapolación operativa a meses posteriores.
