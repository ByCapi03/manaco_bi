"""
limpiar_datos.py
Módulo ETL para el Caso Manaco BI.
Carga el archivo Excel desde data/raw, aplica validaciones y reglas de negocio,
y exporta las tablas dimensionales y de hechos a data/processed/.
"""

from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def encontrar_archivo_raw() -> Path:
    """Busca el archivo de Excel en data/raw con el nombre esperado."""
    posibles_nombres = [
        "Bae de Datos MANACO - INTERMEDIO (1).xlsx",
        "BDatos_MANACO.xlsx",
        "Base de Datos MANACO.xlsx"
    ]
    for nombre in posibles_nombres:
        ruta = RAW_DIR / nombre
        if ruta.exists():
            return ruta
    # Si no, buscar cualquier .xlsx en data/raw
    archivos = list(RAW_DIR.glob("*.xlsx"))
    if archivos:
        return archivos[0]
    raise FileNotFoundError(f"No se encontró ningún archivo Excel en {RAW_DIR}")


def cargar_y_validar() -> pd.DataFrame:
    """Carga el dataset y estandariza los nombres de columnas."""
    ruta = encontrar_archivo_raw()
    print(f"[1/4] Leyendo dataset desde: {ruta.name}")
    df = pd.read_excel(ruta, sheet_name="Base de Datos")
    
    # Estandarizar nombres de columnas eliminando tildes y caracteres extraños
    mapeo_columnas = {
        "País_reportante": "pais_reportante",
        "Pas_reportante": "pais_reportante",
        "Flujo_comercial": "flujo_comercial",
        "Año": "anio",
        "Ao": "anio",
        "Código_SA6": "codigo_sa6",
        "Cdigo_SA6": "codigo_sa6",
        "Categoría_calzado": "categoria_calzado",
        "Categora_calzado": "categoria_calzado",
        "Socio_comercial": "socio_comercial",
        "Valor_miles_USD": "valor_miles_usd",
        "Cantidad_pares": "cantidad_pares",
        "Valor_USD": "valor_usd",
        "Valor_USD_por_par": "valor_usd_por_par"
    }
    df = df.rename(columns=mapeo_columnas)
    
    # Regla 2: Mantener cantidades faltantes como desconocidas (no rellenar con 0)
    # Reemplazar valores <= 0 en cantidad_pares con NaN si aplican como faltantes
    df["cantidad_pares"] = df["cantidad_pares"].replace({0: np.nan})
    
    # Recalcular valor_usd_por_par fila a fila solo donde cantidad_pares no sea nula ni cero
    df["valor_usd_por_par"] = np.where(
        df["cantidad_pares"].notna() & (df["cantidad_pares"] > 0),
        df["valor_usd"] / df["cantidad_pares"],
        np.nan
    )
    
    return df


def construir_modelo_dimensional(df: pd.DataFrame):
    """Genera las tablas dimensionales y la tabla de hechos con sus claves foráneas."""
    print("[2/4] Generando dimensiones y modelo estrella...")
    
    # 1. Dimensión Período
    dim_periodo = pd.DataFrame({"anio": sorted(df["anio"].unique())})
    dim_periodo["id_periodo"] = dim_periodo["anio"] # El año sirve como clave directa o índice
    
    # 2. Dimensión Producto
    dim_producto = df[["codigo_sa6", "categoria_calzado"]].drop_duplicates().reset_index(drop=True)
    dim_producto["id_producto"] = dim_producto.index + 1
    
    # 3. Dimensión Reportante
    dim_reportante = pd.DataFrame({"pais_reportante": sorted(df["pais_reportante"].unique())})
    dim_reportante["id_reportante"] = dim_reportante.index + 1
    
    # 4. Dimensión Socio Comercial
    # Regla 1: Identificar y clasificar el agregado 'Mundo' para evitar doble conteo
    dim_socio = pd.DataFrame({"socio_comercial": sorted(df["socio_comercial"].unique())})
    dim_socio["id_socio"] = dim_socio.index + 1
    dim_socio["tipo_socio"] = dim_socio["socio_comercial"].apply(
        lambda s: "Mundo" if str(s).strip().lower() in ["mundo", "world", "total mundo"] else "País"
    )
    
    # 5. Dimensión Flujo
    dim_flujo = pd.DataFrame({"flujo_comercial": sorted(df["flujo_comercial"].unique())})
    dim_flujo["id_flujo"] = dim_flujo.index + 1
    
    # 6. Tabla de Hechos: fact_comercio
    print("[3/4] Mapeando claves foráneas en la tabla fact_comercio...")
    fact = df.copy()
    
    fact = fact.merge(dim_periodo, on="anio", how="left")
    fact = fact.merge(dim_producto, on=["codigo_sa6", "categoria_calzado"], how="left")
    fact = fact.merge(dim_reportante, on="pais_reportante", how="left")
    fact = fact.merge(dim_socio[["socio_comercial", "id_socio"]], on="socio_comercial", how="left")
    fact = fact.merge(dim_flujo, on="flujo_comercial", how="left")
    
    fact["id_hecho"] = fact.index + 1
    
    columnas_hecho = [
        "id_hecho", "id_periodo", "id_producto", "id_reportante", "id_socio", "id_flujo",
        "valor_usd", "cantidad_pares", "valor_usd_por_par", "valor_miles_usd"
    ]
    fact_comercio = fact[columnas_hecho]
    
    return dim_periodo, dim_producto, dim_reportante, dim_socio, dim_flujo, fact_comercio, df


def exportar_datos(dim_periodo, dim_producto, dim_reportante, dim_socio, dim_flujo, fact_comercio, df_limpio):
    """Guarda todas las tablas en formato CSV en data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[4/4] Guardando archivos procesados en: {PROCESSED_DIR}")
    
    dim_periodo.to_csv(PROCESSED_DIR / "dim_periodo.csv", index=False)
    dim_producto.to_csv(PROCESSED_DIR / "dim_producto.csv", index=False)
    dim_reportante.to_csv(PROCESSED_DIR / "dim_reportante.csv", index=False)
    dim_socio.to_csv(PROCESSED_DIR / "dim_socio.csv", index=False)
    dim_flujo.to_csv(PROCESSED_DIR / "dim_flujo.csv", index=False)
    fact_comercio.to_csv(PROCESSED_DIR / "fact_comercio.csv", index=False)
    df_limpio.to_csv(PROCESSED_DIR / "datos_comercio_limpios.csv", index=False)
    
    print("Exportación finalizada con éxito.")


def main():
    df = cargar_y_validar()
    p, pr, rep, s, f, fact, df_l = construir_modelo_dimensional(df)
    exportar_datos(p, pr, rep, s, f, fact, df_l)


if __name__ == "__main__":
    main()
