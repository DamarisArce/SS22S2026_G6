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


def etiqueta_original(valor):
    """
    Convierte los valores originales a etiquetas visibles únicamente
    para mostrar la tabla pivote antes de la limpieza.
    No modifica el dataset original.
    """
    if pd.isna(valor):
        return "<VACÍO>"

    texto = str(valor)

    if texto.strip() == "":
        return "<ESPACIO EN BLANCO>"

    texto_limpio = texto.strip()

    if texto != texto_limpio:
        return f"{texto_limpio} [con espacios]"

    return texto


def guardar_tabla_como_imagen(tabla, titulo, ruta):
    """Guarda un DataFrame como imagen para documentarlo en el README."""
    tabla_mostrar = tabla.reset_index()

    ancho = max(10, len(tabla_mostrar.columns) * 1.5)
    alto = max(4, len(tabla_mostrar) * 0.4)

    fig, ax = plt.subplots(figsize=(ancho, alto))
    ax.axis("off")
    ax.set_title(titulo, pad=20, fontsize=14)

    tabla_grafica = ax.table(
        cellText=tabla_mostrar.values,
        colLabels=tabla_mostrar.columns,
        loc="center",
        cellLoc="center"
    )

    tabla_grafica.auto_set_font_size(False)
    tabla_grafica.set_fontsize(8)
    tabla_grafica.scale(1, 1.3)

    plt.tight_layout()
    plt.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close()


# CARGA DEL DATASET
df = pd.read_csv(ARCHIVO_ENTRADA, encoding="utf-8")

# Se conserva una copia exacta del dataset antes de realizar cualquier limpieza.
df_original = df.copy()

print("\n========== DATASET ORIGINAL ==========")
print(f"Cantidad de registros originales: {len(df)}")
print(f"Cantidad de columnas: {len(df.columns)}")
print("\nPrimeras filas del dataset original:")
print(df.head())


# TABLA PIVOTE ANTES DE LA LIMPIEZA

# Se utiliza una copia exclusivamente para visualizar de forma clara
# los valores inconsistentes del dataset original.
vista_pivote_antes = df_original.copy()

vista_pivote_antes["categoria"] = (
    vista_pivote_antes["categoria"].apply(etiqueta_original)
)

vista_pivote_antes["genero"] = (
    vista_pivote_antes["genero"].apply(etiqueta_original)
)

tabla_pivote_antes = pd.pivot_table(
    vista_pivote_antes,
    index="categoria",
    columns="genero",
    values="id_cliente",
    aggfunc="count",
    fill_value=0,
    margins=True,
    margins_name="Total"
)

print("\n========== TABLA PIVOTE ANTES DE LA LIMPIEZA ==========")
print(tabla_pivote_antes)

tabla_pivote_antes.to_csv(
    os.path.join(CARPETA_SALIDA, "tabla_pivote_antes.csv"),
    encoding="utf-8-sig"
)

guardar_tabla_como_imagen(
    tabla_pivote_antes,
    "Tabla pivote antes de la limpieza",
    os.path.join(CARPETA_SALIDA, "tabla_pivote_antes.png")
)


# Se guarda información inicial para el reporte.
registros_iniciales = len(df)
duplicados_completos_iniciales = df.duplicated().sum()
ids_duplicados_iniciales = df["id_cliente"].duplicated().sum()
celdas_vacias_iniciales = df.isna().sum().sum()

categorias_originales = df_original["categoria"].nunique(dropna=False)
generos_originales = df_original["genero"].nunique(dropna=False)

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


# TABLA PIVOTE DESPUÉS DE LA LIMPIEZA

tabla_pivote_despues = pd.pivot_table(
    df,
    index="categoria",
    columns="genero",
    values="id_cliente",
    aggfunc="count",
    fill_value=0,
    margins=True,
    margins_name="Total"
)

print("\n========== TABLA PIVOTE DESPUÉS DE LA LIMPIEZA ==========")
print(tabla_pivote_despues)

tabla_pivote_despues.to_csv(
    os.path.join(CARPETA_SALIDA, "tabla_pivote_despues.csv"),
    encoding="utf-8-sig"
)

guardar_tabla_como_imagen(
    tabla_pivote_despues,
    "Tabla pivote después de la limpieza",
    os.path.join(CARPETA_SALIDA, "tabla_pivote_despues.png")
)


# 5. REPORTE DE RESULTADOS
registros_finales = len(df)
celdas_vacias_finales = df.isna().sum().sum()

duplicados_completos_finales = df.duplicated().sum()
ids_duplicados_finales = df["id_cliente"].duplicated().sum()

categorias_finales = df["categoria"].nunique(dropna=False)
generos_finales = df["genero"].nunique(dropna=False)

reporte = pd.DataFrame({
    "indicador": [
        "Registros iniciales",
        "Duplicados completos detectados inicialmente",
        "IDs de cliente repetidos detectados inicialmente",
        "Celdas vacías iniciales",
        "Categorías distintas antes de la limpieza",
        "Valores de género distintos antes de la limpieza",
        "Registros finales",
        "Duplicados completos finales",
        "IDs de cliente repetidos finales",
        "Celdas vacías finales",
        "Categorías distintas después de la limpieza",
        "Valores de género distintos después de la limpieza",
        "Registros eliminados"
    ],
    "valor": [
        registros_iniciales,
        duplicados_completos_iniciales,
        ids_duplicados_iniciales,
        celdas_vacias_iniciales,
        categorias_originales,
        generos_originales,
        registros_finales,
        duplicados_completos_finales,
        ids_duplicados_finales,
        celdas_vacias_finales,
        categorias_finales,
        generos_finales,
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

print("\n========== INTERPRETACIÓN DE LA LIMPIEZA ==========")

print(
    f"El dataset pasó de {registros_iniciales} a {registros_finales} registros "
    f"debido a la eliminación de {registros_iniciales - registros_finales} "
    "registros duplicados."
)

print(
    f"Las celdas vacías pasaron de {celdas_vacias_iniciales} a "
    f"{celdas_vacias_finales}, por lo que no quedaron valores nulos "
    "después del tratamiento."
)

print(
    f"Las diferentes representaciones de categoría se redujeron de "
    f"{categorias_originales} a {categorias_finales} valores consistentes."
)

print(
    f"Las diferentes representaciones de género se redujeron de "
    f"{generos_originales} a {generos_finales} valores estandarizados."
)

print(
    "Las tablas pivote permiten observar que valores que originalmente "
    "se encontraban separados por diferencias de mayúsculas, minúsculas "
    "y espacios fueron consolidados correctamente después de la limpieza."
)

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