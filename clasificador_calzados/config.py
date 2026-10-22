"""
config.py
Configuración central del Clasificador de Calzados Manaco y Control de Inventario BI.
Define las categorías de calzado, hiperparámetros de visión, rutas de modelos y base de datos.
"""

import os
from pathlib import Path

# =====================================================================
# 1. Definición de Categorías de Calzado Manaco
# =====================================================================
# La primera clase siempre debe ser "sin_calzado" (fondo vacío, manos, objetos ajenos).
# Las 3 categorías corresponden al catálogo y Data Warehouse de Manaco:
# - calzado_deportivo: Calzado deportivo con suela de caucho/plástico (SA6: 640411)
# - calzado_casual:    Calzado con suela de caucho/plástico y capellada de cuero (SA6: 640399)
# - calzado_formal:    Calzado con suela de cuero y capellada de cuero (SA6: 640420)

CLASES = [
    "sin_calzado",
    "calzado_deportivo",
    "calzado_casual",
    "calzado_formal"
]

NOMBRES_CLASES = {
    "sin_calzado": "Sin Calzado (Fondo / Manos)",
    "calzado_deportivo": "Calzado Deportivo (Sneakers/Tenis)",
    "calzado_casual": "Calzado Casual Cuero (Mocasines/Botines)",
    "calzado_formal": "Calzado Formal de Vestir (Cuero)"
}

# Mapeo a dim_producto en la base de datos PostgreSQL/SQLite
MAPEO_DB = {
    "calzado_deportivo": {"id_producto": 1, "codigo_sa6": "640411", "precio_bs": 240.00, "precio_usd": 34.50},
    "calzado_casual":    {"id_producto": 2, "codigo_sa6": "640399", "precio_bs": 290.00, "precio_usd": 41.60},
    "calzado_formal":    {"id_producto": 3, "codigo_sa6": "640420", "precio_bs": 350.00, "precio_usd": 50.30}
}

# Colores característicos en formato BGR para OpenCV y HEX para CSS
COLORES_BGR = {
    "sin_calzado": (120, 120, 130),       # Gris
    "calzado_deportivo": (245, 160, 30),   # Cyan/Celeste
    "calzado_casual": (50, 180, 240),      # Ámbar/Dorado
    "calzado_formal": (80, 50, 220)        # Carmesí Manaco
}

COLORES_HEX = {
    "sin_calzado": "#64748b",
    "calzado_deportivo": "#06b6d4",
    "calzado_casual": "#f59e0b",
    "calzado_formal": "#e11d48"
}

# =====================================================================
# 2. Rutas del Sistema
# =====================================================================
CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
CARPETA_DATASET = os.path.join(CARPETA_PROYECTO, "dataset")
ARCHIVO_MODELO = os.path.join(CARPETA_PROYECTO, "modelo_calzados.keras")
ARCHIVO_CLASES = os.path.join(CARPETA_PROYECTO, "clases.json")
ARCHIVO_INVENTARIO_JSON = os.path.join(CARPETA_PROYECTO, "inventario.json")
ARCHIVO_REGISTROS_CSV = os.path.join(CARPETA_PROYECTO, "registros_vision.csv")
ARCHIVO_SQLITE = os.path.join(CARPETA_PROYECTO, "manaco_inventario.db")
TASA_CAMBIO_OFICIAL = 6.96     # Tasa de cambio oficial referencial (BOB / USD)

# Ruta configurable al archivo Excel BDatos_MANACO.xlsx
RUTA_EXCEL_ENV = os.getenv("RUTA_EXCEL", "")
RUTA_EXCEL_CANDIDATOS = [
    RUTA_EXCEL_ENV,
    os.path.join(CARPETA_PROYECTO, "..", "data", "raw", "BDatos_MANACO.xlsx"),
    os.path.join(CARPETA_PROYECTO, "..", "..", "BDatos_MANACO.xlsx"),
    os.path.join(CARPETA_PROYECTO, "BDatos_MANACO.xlsx")
]

def obtener_ruta_excel():
    """Retorna la primera ruta existente al archivo de Excel comercial BDatos_MANACO.xlsx."""
    for r in RUTA_EXCEL_CANDIDATOS:
        if r and os.path.exists(r):
            return os.path.abspath(r)
    return os.path.abspath(os.path.join(CARPETA_PROYECTO, "..", "data", "raw", "BDatos_MANACO.xlsx"))

# =====================================================================
# 3. Parámetros de la Red Neuronal y Visión Artificial
# =====================================================================
TAMANO_IMG = 100               # Imágenes cuadradas 100x100 en color (3 canales RGB)
CAMARA = 0                     # Índice de cámara predeterminada (0 = integrada, 1 = USB)
CONFIANZA_MINIMA = 0.75        # Umbral mínimo de confianza para aceptar la predicción (75%)
FRAMES_PARA_REGISTRAR = 5      # Cantidad de frames continuos detectando el mismo zapato
FRAMES_PARA_LIBERAR = 4        # Frames requeridos "sin_calzado" antes de poder contar el siguiente


def recortar_cuadrado(frame):
    """Recorta la región central de la imagen en un cuadrado (zona de escaneo)."""
    alto, ancho = frame.shape[:2]
    lado = min(alto, ancho)
    y0 = (alto - lado) // 2
    x0 = (ancho - lado) // 2
    return frame[y0:y0 + lado, x0:x0 + lado]


def preprocesar(imagen_bgr):
    """Convierte un frame BGR de OpenCV al tensor esperado por la CNN:
    RGB, TAMANO_IMG x TAMANO_IMG, normalizado a [0, 1]."""
    import cv2
    import numpy as np

    imagen = cv2.resize(imagen_bgr, (TAMANO_IMG, TAMANO_IMG))
    imagen = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
    return imagen.astype(np.float32) / 255.0
