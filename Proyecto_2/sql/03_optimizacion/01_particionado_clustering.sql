-- Tabla optimizada con mismas filas/columnas que viajes_base.
-- Particion: pickup_date (día UTC). Clustering: zona de inicio y destino.
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.viajes_optimizada`
PARTITION BY pickup_date
CLUSTER BY pickup_location_id, dropoff_location_id
OPTIONS(require_partition_filter=TRUE,description='Mismas filas y columnas que viajes_base; partición por día y clustering por ubicación') AS
SELECT * FROM `__PROJECT_ID__.__DATASET__.viajes_base`;
