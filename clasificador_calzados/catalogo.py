"""
clasificador_calzados/catalogo.py
Catálogo oficial de productos ficticios para demostración MANACO BI.
Define seis productos (dos por categoría arancelaria SA6):
- 640411: Deportivo Básico y Deportivo Confort
- 640399: Casual Básico y Casual Confort
- 640420: Vestir Básico y Vestir Confort

Aviso metodológico: El mapeo es de demostración académica/técnica y no
constituye una certificación arancelaria oficial ni precios contractualmente vinculantes.
"""

from typing import Dict, Any, List
import pandas as pd
from config import TASA_CAMBIO_OFICIAL

# Definición base de los 6 productos
CATALOGO_PRODUCTOS: List[Dict[str, Any]] = [
    {
        "id_producto": 1,
        "codigo_sku": "DEP-BAS",
        "codigo_sa6": "640411",
        "categoria_padre": "calzado_deportivo",
        "categoria_arancelaria": "Calzado deportivo con suela de caucho/plástico",
        "categoria_corta": "Calzado Deportivo",
        "linea": "Básico",
        "nombre_producto": "Deportivo Básico",
        "descripcion": "Sneakers de entrenamiento para uso diario con soporte estándar.",
        "gastos_adicionales_usd": 4.00,
        "margen_objetivo_pct": 25.0,
        "stock_minimo": 15,
        "capacidad_maxima": 150,
        "lead_time_dias": 7,
        "stock_seguridad": 10,
        "icono": "👟"
    },
    {
        "id_producto": 2,
        "codigo_sku": "DEP-CNF",
        "codigo_sa6": "640411",
        "categoria_padre": "calzado_deportivo",
        "categoria_arancelaria": "Calzado deportivo con suela de caucho/plástico",
        "categoria_corta": "Calzado Deportivo",
        "linea": "Confort",
        "nombre_producto": "Deportivo Confort",
        "descripcion": "Sneakers ergonómicos con plantilla de gel memory foam y amortiguación reforzada.",
        "gastos_adicionales_usd": 6.00,
        "margen_objetivo_pct": 30.0,
        "stock_minimo": 15,
        "capacidad_maxima": 150,
        "lead_time_dias": 7,
        "stock_seguridad": 10,
        "icono": "👟"
    },
    {
        "id_producto": 3,
        "codigo_sku": "CAS-BAS",
        "codigo_sa6": "640399",
        "categoria_padre": "calzado_casual",
        "categoria_arancelaria": "Calzado con suela de caucho/plástico y capellada de cuero",
        "categoria_corta": "Calzado Casual Cuero",
        "linea": "Básico",
        "nombre_producto": "Casual Básico",
        "descripcion": "Mocasines ligeros de cuero curtido con suela flexible para ciudad.",
        "gastos_adicionales_usd": 4.00,
        "margen_objetivo_pct": 25.0,
        "stock_minimo": 15,
        "capacidad_maxima": 120,
        "lead_time_dias": 8,
        "stock_seguridad": 10,
        "icono": "👞"
    },
    {
        "id_producto": 4,
        "codigo_sku": "CAS-CNF",
        "codigo_sa6": "640399",
        "categoria_padre": "calzado_casual",
        "categoria_arancelaria": "Calzado con suela de caucho/plástico y capellada de cuero",
        "categoria_corta": "Calzado Casual Cuero",
        "linea": "Confort",
        "nombre_producto": "Casual Confort",
        "descripcion": "Botines casuales de cuero graso con tecnología anti-impacto.",
        "gastos_adicionales_usd": 6.00,
        "margen_objetivo_pct": 30.0,
        "stock_minimo": 15,
        "capacidad_maxima": 120,
        "lead_time_dias": 8,
        "stock_seguridad": 10,
        "icono": "👞"
    },
    {
        "id_producto": 5,
        "codigo_sku": "VES-BAS",
        "codigo_sa6": "640420",
        "categoria_padre": "calzado_formal",
        "categoria_arancelaria": "Calzado con suela de cuero y capellada de cuero",
        "categoria_corta": "Calzado Formal Vestir",
        "linea": "Básico",
        "nombre_producto": "Vestir Básico",
        "descripcion": "Zapatos Oxford clásicos de cuero vacuno para oficina y eventos formales.",
        "gastos_adicionales_usd": 5.00,
        "margen_objetivo_pct": 25.0,
        "stock_minimo": 10,
        "capacidad_maxima": 100,
        "lead_time_dias": 10,
        "stock_seguridad": 8,
        "icono": "👞"
    },
    {
        "id_producto": 6,
        "codigo_sku": "VES-CNF",
        "codigo_sa6": "640420",
        "categoria_padre": "calzado_formal",
        "categoria_arancelaria": "Calzado con suela de cuero y capellada de cuero",
        "categoria_corta": "Calzado Formal Vestir",
        "linea": "Confort",
        "nombre_producto": "Vestir Confort",
        "descripcion": "Derby ejecutivo de cuero de flor premium con forro respirable y plantilla ortopédica.",
        "gastos_adicionales_usd": 7.00,
        "margen_objetivo_pct": 30.0,
        "stock_minimo": 10,
        "capacidad_maxima": 100,
        "lead_time_dias": 10,
        "stock_seguridad": 8,
        "icono": "👞"
    }
]


def calcular_referencias_importacion_2024(df_excel: pd.DataFrame) -> Dict[str, float]:
    """
    Recalcula las referencias oficiales de importación 2024 desde el Excel usando:
    SUM(Valor_USD) / SUM(Cantidad_pares), agrupando por Código_SA6 con precisión completa.
    """
    sub = df_excel[(df_excel["Año"] == 2024) & (df_excel["Flujo_comercial"] == "Importación")]
    grp = sub.groupby("Código_SA6").agg({
        "Valor_USD": "sum",
        "Cantidad_pares": "sum"
    }).reset_index()

    referencias = {}
    for _, fila in grp.iterrows():
        sa6 = str(int(fila["Código_SA6"]))
        v = float(fila["Valor_USD"])
        p = float(fila["Cantidad_pares"])
        referencias[sa6] = (v / p) if p > 0 else 0.0
    return referencias


def calcular_precio_escenario(referencia_usd: float, gastos_adicionales_usd: float, margen_pct: float, tasa_cambio: float = TASA_CAMBIO_OFICIAL) -> Dict[str, float]:
    """
    Fórmula oficial solicitada:
    Costo estimado = referencia_usd + gastos_adicionales_usd
    Precio = Costo estimado / (1 - margen)
    """
    margen_dec = min(0.99, max(0.0, margen_pct / 100.0))
    costo_estimado_usd = referencia_usd + gastos_adicionales_usd
    divisor = max(0.01, 1.0 - margen_dec)
    precio_usd = costo_estimado_usd / divisor
    precio_bob = precio_usd * tasa_cambio

    return {
        "referencia_usd": round(referencia_usd, 4),
        "gastos_usd": round(gastos_adicionales_usd, 2),
        "costo_estimado_usd": round(costo_estimado_usd, 4),
        "costo_estimado_bob": round(costo_estimado_usd * tasa_cambio, 2),
        "margen_pct": round(margen_pct, 2),
        "precio_usd": round(precio_usd, 2),
        "precio_bob": round(precio_bob, 2)
    }


def obtener_catalogo_completo(df_excel: pd.DataFrame = None, tasa_cambio: float = TASA_CAMBIO_OFICIAL) -> List[Dict[str, Any]]:
    """
    Retorna los 6 productos con sus referencias exactas de 2024, costos estimados y precios propuestos iniciales.
    """
    if df_excel is None:
        import analisis_comercial as ac
        df_excel = ac.cargar_dataset_excel()

    referencias = calcular_referencias_importacion_2024(df_excel)

    resultado = []
    for item in CATALOGO_PRODUCTOS:
        prod = dict(item)
        sa6 = prod["codigo_sa6"]
        ref_usd = referencias.get(sa6, 25.0)

        precios = calcular_precio_escenario(
            referencia_usd=ref_usd,
            gastos_adicionales_usd=prod["gastos_adicionales_usd"],
            margen_pct=prod["margen_objetivo_pct"],
            tasa_cambio=tasa_cambio
        )

        prod["referencia_importacion_2024_usd"] = precios["referencia_usd"]
        prod["costo_estimado_usd"] = precios["costo_estimado_usd"]
        prod["costo_estimado_bob"] = precios["costo_estimado_bob"]
        prod["precio_propuesto_usd"] = precios["precio_usd"]
        prod["precio_propuesto_bob"] = precios["precio_bob"]

        resultado.append(prod)

    return resultado
