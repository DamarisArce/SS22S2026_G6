# Proyecto 1 — SG-Food ELT

## Descripción

Proyecto académico de Seminario de Sistemas 2 para diseñar un flujo ELT con
Python, Apache Airflow, PostgreSQL y dbt Core sobre las fuentes de SG-Food.
Esta entrega implementa únicamente el Bloque 1A: infraestructura PostgreSQL
reproducible con Docker Compose.

## Integrantes

- Dámaris Magali Arce Guzmán — 202006636
- Nelson Emanuel Cún Bálan — 201222010

## Componentes previstos

- PostgreSQL OLTP para la fuente transaccional.
- PostgreSQL DW con `raw`, `staging`, `intermediate` y `marts`.
- PostgreSQL para metadatos de Airflow.
- Python, Airflow y dbt Core en fases posteriores.

Los servicios de Airflow, Python y dbt aún no están implementados. Los tres
contenedores definidos en Compose tampoco se han iniciado en esta fase.

## Estructura inicial

```text
Proyecto1/
├── compose.yaml
├── .env.example
├── data/                         # Copias íntegras de seis fuentes operativas
├── docker/postgres/
│   └── dw/init/                  # DDL inicial no destructivo del DW
├── docs/
│   ├── 00-matriz-requisitos.md
│   ├── 01-catalogo-fuentes.md
│   ├── 02-arquitectura-y-decisiones.md
│   └── 03-infraestructura.md
└── insumos/                      # ZIP y PDF originales, sin modificar
```

`casos_calidad_opcionales.csv` y `catalogo_insumos_sgfood.xlsx` permanecen
únicamente dentro del ZIP original; no son datos operativos de `data/`.

## Estado real

Comprobado estáticamente: Compose, la plantilla de variables, los scripts de
inicialización y las copias de fuentes están preparados. PENDIENTE: ejecutar
Compose, inicializar PostgreSQL, cargar datos, implementar Airflow/Python/dbt y
probar el flujo completo.

## Documentación relacionada

- [Matriz de requisitos](docs/00-matriz-requisitos.md)
- [Catálogo de fuentes](docs/01-catalogo-fuentes.md)
- [Arquitectura y decisiones](docs/02-arquitectura-y-decisiones.md)
- [Infraestructura PostgreSQL](docs/03-infraestructura.md)
