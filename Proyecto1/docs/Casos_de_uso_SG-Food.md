# Casos de uso principales — SG-Food

## Propósito

Agrupar la solución en cinco casos de uso de alto nivel. Los documentos técnicos y modelos dbt especifican o evidencian estos casos; no se consideran casos separados.

## Actores

- **Operador del pipeline:** configura y ejecuta el proceso, revisa su estado y atiende incidencias.
- **Analista de datos:** consulta el modelo analítico publicado.

Estos roles representan las responsabilidades reflejadas en la arquitectura y el manual; no presuponen automatizaciones ni herramientas BI no documentadas.

## Casos de uso

### UC-01 · Integrar fuentes de datos
**Actor principal:** Operador del pipeline.

**Objetivo:** incorporar al almacén de datos los datos operativos de PostgreSQL y los archivos CSV.

**Flujo resumido:** validar entorno, fuentes, formatos y contratos; extraer las siete tablas OLTP y leer cinco CSV; cargar las doce entidades en `raw` con control transaccional y metadatos de trazabilidad.

**Documentación asociada:** catálogo de fuentes, permisos, infraestructura, contrato de carga raw.

### UC-02 · Transformar y preparar datos
**Actor principal:** Operador del pipeline (ejecución); el procesamiento es realizado por dbt.

**Objetivo:** transformar datos raw en modelos analíticos consistentes, preservando las reglas y granos documentados.

**Flujo resumido:** construir 12 modelos de `staging`, 4 de `intermediate` y 5 de `marts`; tipar y normalizar datos; aplicar reglas de negocio documentadas sin mezclar hechos de distinto grano.

**Documentación asociada:** arquitectura y decisiones, staging, intermediate, inventario snapshot, devoluciones y ventas mensuales.

### UC-03 · Publicar modelo para análisis
**Actor principal:** Analista de datos.

**Objetivo:** disponer de un modelo dimensional consultable para analizar ventas.

**Flujo resumido:** publicar el hecho `fct_ventas_detalle` y las dimensiones `dim_cliente`, `dim_fecha`, `dim_producto` y `dim_sucursal`; conservar el grano del hecho (una fila por `id_detalle`) y las relaciones lógicas documentadas.

**Nota:** las entidades dimensionales son vistas dbt; no tienen PK/FK físicas. Las relaciones se verifican mediante pruebas y reconciliación.

**Documentación asociada:** ventas al detalle y documentos de las cuatro dimensiones.

### UC-04 · Orquestar y validar el pipeline
**Actor principal:** Operador del pipeline.

**Objetivo:** ejecutar las etapas en orden y comprobar la integridad del resultado antes de declarar éxito.

**Flujo resumido:** ejecutar el DAG manual; validar configuración; cargar raw; correr `dbt build` y sus pruebas; realizar reconciliación; marcar éxito solo si las tareas anteriores finalizan correctamente. La ejecución es secuencial, sin reintentos automáticos y con `max_active_runs=1`.

**Documentación asociada:** arquitectura, DAG de Airflow, matriz de requisitos, infraestructura de Airflow.

### UC-05 · Operar la solución
**Actor principal:** Operador del pipeline.

**Objetivo:** preparar y mantener la ejecución local de forma controlada.

**Flujo resumido:** configurar variables y secretos localmente, iniciar servicios, aprovisionar roles, ejecutar y verificar el DAG, diagnosticar fallos y detener los servicios sin eliminar volúmenes.

**Documentación asociada:** manual de implementación e infraestructura.

## Relación entre casos

La operación inicia la ejecución orquestada (UC-05 → UC-04). El flujo orquestado coordina la integración, las transformaciones y la validación (UC-04 incluye UC-01 y UC-02; la validación comprueba el resultado publicado en UC-03). El analista consume el modelo publicado (UC-03).

## Fuera del alcance representado

No se presentan como capacidades implementadas la programación automática del DAG, un dashboard BI, historización SCD tipo 2 ni atribución de promociones a ventas, pues la documentación los identifica como no implementados o fuera del alcance validado.
