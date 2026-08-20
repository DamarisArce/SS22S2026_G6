import os
import re
import pandas as pd
import matplotlib.pyplot as plt


ARCHIVO_ENTRADA = "dataset_sucio.csv"
CARPETA_SALIDA = "resultados"
ARCHIVO_LIMPIO = os.path.join(CARPETA_SALIDA, "dataset_limpio.csv")
ARCHIVO_REPORTE = os.path.join(CARPETA_SALIDA, "reporte_limpieza.csv")

os.makedirs(CARPETA_SALIDA, exist_ok=True)

# FUNCIONES DE LIMPIEZA

def limpiar_texto(valor):
    """Elimina espacios sobrantes y convierte textos vacíos en valores nulos."""
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip()
    valor = re.sub(r"\s+", " ", valor)

    if valor == "":
        return pd.NA

    return valor


def estandarizar_genero(valor):
    """Convierte las distintas formas de género a Masculino o Femenino."""
    if pd.isna(valor):
        return "No especificado"

    valor = str(valor).strip().lower()

    equivalencias = {
        "m": "Masculino",
        "masculino": "Masculino",
        "f": "Femenino",
        "femenino": "Femenino"
    }

    return equivalencias.get(valor, "No especificado")


def estandarizar_fecha(serie):
    # Convierte fechas en formato YYYY-MM-DD y DD/MM/YYYY a un formato único de fecha.
  
    fecha = pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce")

    mascara_fechas_pendientes = fecha.isna()
    fecha.loc[mascara_fechas_pendientes] = pd.to_datetime(
        serie.loc[mascara_fechas_pendientes],
        format="%d/%m/%Y",
        errors="coerce"
    )

    return fecha


def convertir_gasto(valor):
    """
    Convierte montos como 373,33 o 371.80 al tipo numérico float.
    Los valores vacíos se convierten en NaN.
    """
    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip()
    valor = valor.replace("Q", "")
    valor = valor.replace(" ", "")
    valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return pd.NA


def estandarizar_ciudad(valor):
    """Corrige mayúsculas, espacios y formatos de ciudades."""
    if pd.isna(valor):
        return "No especificado"

    valor = limpiar_texto(valor)

    ciudades = {
        "antigua": "Antigua",
        "villa nueva": "Villa Nueva",
        "quetzaltenango": "Quetzaltenango",
        "amatitlan": "Amatitlán",
        "amatitlán": "Amatitlán",
        "guatemala": "Guatemala",
        "escuintla": "Escuintla"
    }

    return ciudades.get(valor.lower(), valor.title())


def estandarizar_categoria(valor):
    """Unifica las categorías en un formato consistente."""
    if pd.isna(valor):
        return "No especificado"

    valor = limpiar_texto(valor)

    categorias = {
        "retail": "Retail",
        "services": "Services",
        "education": "Education"
    }

    return categorias.get(valor.lower(), valor.title())


# CARGA DEL DATASET
df = pd.read_csv(ARCHIVO_ENTRADA, encoding="utf-8")

print("\n========== DATASET ORIGINAL ==========")
print(f"Cantidad de registros originales: {len(df)}")
print(f"Cantidad de columnas: {len(df.columns)}")
print("\nPrimeras filas del dataset original:")
print(df.head())

# Se guarda información inicial para el reporte.
registros_iniciales = len(df)
duplicados_completos_iniciales = df.duplicated().sum()
ids_duplicados_iniciales = df["id_cliente"].duplicated().sum()
celdas_vacias_iniciales = df.isna().sum().sum()

# 1. LIMPIEZA GENERAL DE TEXTO
columnas_texto = ["nombre", "genero", "ciudad", "categoria"]

for columna in columnas_texto:
    df[columna] = df[columna].apply(limpiar_texto)

df.replace(r"^\s*$", pd.NA, regex=True, inplace=True)


# 2. ELIMINACIÓN DE DUPLICADOS

df = df.drop_duplicates()

# Si un cliente aparece varias veces, conserva el primer registro.
df = df.drop_duplicates(subset="id_cliente", keep="first")


# 3. ESTANDARIZACIÓN DE VALORES Y FORMATOS

# Nombres: elimina espacios extra y usa formato Título.
df["nombre"] = df["nombre"].fillna("No especificado").str.title()

# Género.
df["genero"] = df["genero"].apply(estandarizar_genero)

# Fechas.
df["fecha_registro"] = estandarizar_fecha(df["fecha_registro"])

# Ciudades y categorías.
df["ciudad"] = df["ciudad"].apply(estandarizar_ciudad)
df["categoria"] = df["categoria"].apply(estandarizar_categoria)

# Gasto: convierte comas decimales a puntos y cambia a número.
df["gasto_q"] = df["gasto_q"].apply(convertir_gasto)
df["gasto_q"] = pd.to_numeric(df["gasto_q"], errors="coerce")

# 4. TRATAMIENTO DE CELDAS VACÍAS

# Si falta la fecha, se usa la fecha más frecuente del dataset.
if df["fecha_registro"].isna().any():
    fecha_moda = df["fecha_registro"].mode()

    if not fecha_moda.empty:
        df["fecha_registro"] = df["fecha_registro"].fillna(fecha_moda.iloc[0])

# Si falta gasto, se reemplaza por la mediana de gasto de su categoría.
mediana_por_categoria = df.groupby("categoria")["gasto_q"].transform("median")
df["gasto_q"] = df["gasto_q"].fillna(mediana_por_categoria)

# Si una categoría no posee suficiente información para calcular la mediana,
# se usa la mediana general del dataset.
df["gasto_q"] = df["gasto_q"].fillna(df["gasto_q"].median())

# Se redondea el gasto a dos decimales.
df["gasto_q"] = df["gasto_q"].round(2)

# Formato uniforme para exportar la fecha.
df["fecha_registro"] = df["fecha_registro"].dt.strftime("%Y-%m-%d")



# 5. REPORTE DE RESULTADOS
registros_finales = len(df)
celdas_vacias_finales = df.isna().sum().sum()

reporte = pd.DataFrame({
    "indicador": [
        "Registros iniciales",
        "Duplicados completos detectados",
        "IDs de cliente repetidos detectados",
        "Celdas vacías iniciales",
        "Registros finales",
        "Celdas vacías finales",
        "Registros eliminados"
    ],
    "valor": [
        registros_iniciales,
        duplicados_completos_iniciales,
        ids_duplicados_iniciales,
        celdas_vacias_iniciales,
        registros_finales,
        celdas_vacias_finales,
        registros_iniciales - registros_finales
    ]
})


# 6. EXPORTACIÓN

df.to_csv(ARCHIVO_LIMPIO, index=False, encoding="utf-8-sig")
reporte.to_csv(ARCHIVO_REPORTE, index=False, encoding="utf-8-sig")

print("\n========== DATASET LIMPIO ==========")
print(df.head())

print("\n========== REPORTE DE LIMPIEZA ==========")
print(reporte)

# Gráfica 1: número de clientes por categoría.
plt.figure(figsize=(8, 5))
df["categoria"].value_counts().plot(
    kind="bar",
    color=["#4E79A7", "#F28E2B", "#59A14F"]
)
plt.title("Cantidad de clientes por categoría")
plt.xlabel("Categoría")
plt.ylabel("Cantidad de clientes")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "clientes_por_categoria.png"),
    dpi=150
)
plt.close()

# Gráfica 2: gasto promedio por ciudad.
gasto_por_ciudad = (
    df.groupby("ciudad")["gasto_q"]
    .mean()
    .sort_values(ascending=False)
)

plt.figure(figsize=(10, 5))
gasto_por_ciudad.plot(kind="bar", color="#76B7B2")
plt.title("Gasto promedio por ciudad")
plt.xlabel("Ciudad")
plt.ylabel("Gasto promedio en quetzales (Q)")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "gasto_promedio_por_ciudad.png"),
    dpi=150
)
plt.close()

# Gráfica 3: distribución por género.
plt.figure(figsize=(7, 5))
df["genero"].value_counts().plot(
    kind="bar",
    color=["#E15759", "#4E79A7", "#BAB0AC"]
)
plt.title("Distribución de clientes por género")
plt.xlabel("Género")
plt.ylabel("Cantidad de clientes")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(
    os.path.join(CARPETA_SALIDA, "clientes_por_genero.png"),
    dpi=150
)
plt.close()

print("\nProceso finalizado correctamente.")
print(f"Archivo limpio generado: {ARCHIVO_LIMPIO}")
print(f"Reporte generado: {ARCHIVO_REPORTE}")
print(f"Gráficas generadas en la carpeta: {CARPETA_SALIDA}")