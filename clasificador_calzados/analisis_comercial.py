"""
analisis_comercial.py
Motor de Analisis Comercial y Calculadora de Escenarios para MANACO BI.
Lee directamente el archivo oficial BDatos_MANACO.xlsx usando pandas,
sin intermediacion ni dependencia del Data Warehouse (DW).
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from config import obtener_ruta_excel, TASA_CAMBIO_OFICIAL

# Cache en memoria del DataFrame para rendimiento
_DATAFRAME_CACHE: Optional[pd.DataFrame] = None
_RUTA_CARGADA: Optional[str] = None


def cargar_dataset_excel(forzar_recarga: bool = False) -> pd.DataFrame:
    """
    Carga y valida el archivo BDatos_MANACO.xlsx preservando sus 240 registros
    y sus combinaciones repetidas originales.
    """
    global _DATAFRAME_CACHE, _RUTA_CARGADA
    ruta = obtener_ruta_excel()

    if _DATAFRAME_CACHE is not None and not forzar_recarga and _RUTA_CARGADA == ruta:
        return _DATAFRAME_CACHE

    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontro el archivo de datos Excel en: {ruta}")

    # Leer hoja 'Base de Datos'
    xl = pd.ExcelFile(ruta)
    hoja_nombre = "Base de Datos" if "Base de Datos" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(ruta, sheet_name=hoja_nombre)

    # Validacion estricta de estructura esperada
    columnas_esperadas = [
        "País_reportante", "Flujo_comercial", "Año", "Código_SA6",
        "Categoría_calzado", "Socio_comercial", "Valor_miles_USD",
        "Cantidad_pares", "Valor_USD", "Valor_USD_por_par"
    ]
    # Comprobar si estan presentes o mapear nombres con normalizacion
    mapeo = {}
    for col in df.columns:
        c_limpio = col.strip()
        for exp in columnas_esperadas:
            if c_limpio.lower() == exp.lower() or c_limpio.replace("í", "i").replace("ñ", "n").lower() == exp.replace("í", "i").replace("ñ", "n").lower():
                mapeo[col] = exp
                break

    df = df.rename(columns=mapeo)

    # Validar tipos
    df["Código_SA6"] = df["Código_SA6"].astype(int)
    df["Año"] = df["Año"].astype(int)
    df["Cantidad_pares"] = df["Cantidad_pares"].astype(float)
    df["Valor_USD"] = df["Valor_USD"].astype(float)
    df["Valor_miles_USD"] = df["Valor_miles_USD"].astype(float)

    _DATAFRAME_CACHE = df
    _RUTA_CARGADA = ruta
    return df


def obtener_opciones_filtros() -> Dict[str, Any]:
    """Retorna los valores unicos disponibles para poblar los selectores en el frontend."""
    df = cargar_dataset_excel()

    flujos = sorted(list(df["Flujo_comercial"].unique()))
    anios = sorted([int(a) for a in df["Año"].unique()])
    socios = sorted([str(s) for s in df["Socio_comercial"].unique()])

    cats_df = df[["Código_SA6", "Categoría_calzado"]].drop_duplicates().sort_values("Código_SA6")
    categorias = []
    for _, r in cats_df.iterrows():
        categorias.append({
            "codigo_sa6": str(r["Código_SA6"]),
            "nombre": str(r["Categoría_calzado"])
        })

    return {
        "exito": True,
        "flujos": flujos,
        "anios": anios,
        "categorias": categorias,
        "socios": socios,
        "total_registros": len(df),
        "fuente": "Registros de comercio exterior reportados por España (BDatos_MANACO.xlsx)",
        "advertencia": "Fuente externa de España. No constituye una cotizacion de importacion ni costo para Bolivia."
    }


def calcular_metricas_comerciales(
    flujo: str = "Importación",
    anio: Optional[int] = 2024,
    codigo_sa6: Optional[int] = None,
    socio: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calcula metricas agregadas con cociente ponderado SUM(valor_usd)/SUM(cantidad_pares),
    desglose por categorias y ranking de socios comerciales.
    """
    df = cargar_dataset_excel()

    # Base para calculo de participacion global del flujo
    df_flujo = df[df["Flujo_comercial"] == flujo]
    total_valor_flujo = df_flujo["Valor_USD"].sum()
    total_pares_flujo = df_flujo["Cantidad_pares"].sum()

    # Aplicar filtros
    sub = df_flujo.copy()
    if anio is not None and anio > 0:
        sub = sub[sub["Año"] == int(anio)]
    if codigo_sa6 is not None and codigo_sa6 > 0:
        sub = sub[sub["Código_SA6"] == int(codigo_sa6)]
    if socio and socio != "TODOS" and socio.strip():
        sub = sub[sub["Socio_comercial"] == socio.strip()]

    total_registros_filtro = len(sub)
    suma_valor_usd = float(sub["Valor_USD"].sum())
    suma_cantidad_pares = float(sub["Cantidad_pares"].sum())

    # Cociente de sumas ponderado (NUNCA promedio simple de Valor_USD_por_par)
    if suma_cantidad_pares > 0:
        referencia_usd_por_par = round(suma_valor_usd / suma_cantidad_pares, 2)
    else:
        referencia_usd_por_par = 0.0

    participacion_valor_pct = round((suma_valor_usd / max(1.0, total_valor_flujo)) * 100, 2)
    participacion_pares_pct = round((suma_cantidad_pares / max(1.0, total_pares_flujo)) * 100, 2)

    # 1. Desglose por las 3 Categorias SA6
    desglose_cats = []
    cats_orden = [640399, 640411, 640420]
    for sa in cats_orden:
        df_cat = sub[sub["Código_SA6"] == sa] if (codigo_sa6 is None or codigo_sa6 == 0) else df_flujo[(df_flujo["Código_SA6"] == sa) & (df_flujo["Año"] == (anio if anio else 2024))]
        v_c = float(df_cat["Valor_USD"].sum())
        p_c = float(df_cat["Cantidad_pares"].sum())
        r_c = round(v_c / p_c, 2) if p_c > 0 else 0.0
        nom_c = df[df["Código_SA6"] == sa]["Categoría_calzado"].iloc[0] if not df[df["Código_SA6"] == sa].empty else str(sa)
        desglose_cats.append({
            "codigo_sa6": str(sa),
            "categoria": nom_c,
            "valor_usd": round(v_c, 2),
            "cantidad_pares": int(p_c),
            "usd_por_par": r_c,
            "registros": len(df_cat)
        })

    # 2. Ranking de Socios Comerciales (Top 10)
    grp_socios = sub.groupby("Socio_comercial").agg({
        "Valor_USD": "sum",
        "Cantidad_pares": "sum"
    }).reset_index()

    grp_socios["usd_por_par"] = np.where(
        grp_socios["Cantidad_pares"] > 0,
        grp_socios["Valor_USD"] / grp_socios["Cantidad_pares"],
        0.0
    )
    grp_socios = grp_socios.sort_values("Valor_USD", ascending=False).head(10)

    ranking_socios = []
    for _, r in grp_socios.iterrows():
        ranking_socios.append({
            "socio": str(r["Socio_comercial"]),
            "valor_usd": round(float(r["Valor_USD"]), 2),
            "cantidad_pares": int(r["Cantidad_pares"]),
            "usd_por_par": round(float(r["usd_por_par"]), 2)
        })

    # 3. Serie Temporal Anual (2020 a 2024) para el flujo y categoria seleccionada
    sub_tiempo = df_flujo.copy()
    if codigo_sa6 is not None and codigo_sa6 > 0:
        sub_tiempo = sub_tiempo[sub_tiempo["Código_SA6"] == int(codigo_sa6)]
    if socio and socio != "TODOS" and socio.strip():
        sub_tiempo = sub_tiempo[sub_tiempo["Socio_comercial"] == socio.strip()]

    grp_tiempo = sub_tiempo.groupby("Año").agg({
        "Valor_USD": "sum",
        "Cantidad_pares": "sum"
    }).reset_index().sort_values("Año")

    serie_anios = []
    serie_valor = []
    serie_pares = []
    serie_ratio = []
    for _, r in grp_tiempo.iterrows():
        v = float(r["Valor_USD"])
        p = float(r["Cantidad_pares"])
        rat = round(v / p, 2) if p > 0 else 0.0
        serie_anios.append(str(int(r["Año"])))
        serie_valor.append(round(v, 2))
        serie_pares.append(int(p))
        serie_ratio.append(rat)

    return {
        "exito": True,
        "filtros_aplicados": {
            "flujo": flujo,
            "anio": anio,
            "codigo_sa6": codigo_sa6,
            "socio": socio
        },
        "resumen": {
            "total_registros": total_registros_filtro,
            "suma_valor_usd": round(suma_valor_usd, 2),
            "suma_cantidad_pares": int(suma_cantidad_pares),
            "referencia_usd_por_par": referencia_usd_por_par,
            "participacion_valor_pct": participacion_valor_pct,
            "participacion_pares_pct": participacion_pares_pct
        },
        "desglose_categorias": desglose_cats,
        "ranking_socios": ranking_socios,
        "serie_temporal": {
            "anios": serie_anios,
            "valores_usd": serie_valor,
            "cantidades_pares": serie_pares,
            "ratios_usd_par": serie_ratio
        },
        "fuente": "Registros de comercio exterior reportados por España (BDatos_MANACO.xlsx)",
        "nota_metodologica": "Referencia aduanera de España calculada como SUM(Valor_USD)/SUM(Cantidad_pares). No equivale a precio minorista ni cotización para Bolivia."
    }


def obtener_referencia_importacion_2024(codigo_sa6: int) -> float:
    """
    Retorna el cociente oficial ponderado de importaciones 2024 para una categoria SA6.
    640399: 26.15 USD/par
    640411: 27.80 USD/par
    640420: 45.53 USD/par
    """
    df = cargar_dataset_excel()
    sub = df[(df["Año"] == 2024) & (df["Flujo_comercial"] == "Importación") & (df["Código_SA6"] == int(codigo_sa6))]
    v = sub["Valor_USD"].sum()
    p = sub["Cantidad_pares"].sum()
    if p > 0:
        return round(float(v / p), 2)
    return 0.0


def calcular_escenario_make_or_buy(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculadora diferencial de toma de decisiones: Fabricar vs Importar.
    Separa costos variables, costos fijos evitables y costos fijos que permanecen.
    Calcula precio propuesto = costo_estimado / (1 - margen_objetivo).
    """
    tc = float(params.get("tasa_cambio", TASA_CAMBIO_OFICIAL) or TASA_CAMBIO_OFICIAL)
    moneda_in = params.get("moneda", "USD").upper()
    es_bob = (moneda_in == "BOB")

    # Factor para convertir entradas a USD si vinieran en BOB
    to_usd = (1.0 / tc) if es_bob else 1.0

    cantidad_pares = max(0, int(params.get("cantidad_pares", 1000)))
    precio_venta = float(params.get("precio_venta", 0.0)) * to_usd
    margen_objetivo_pct = float(params.get("margen_objetivo_pct", 35.0))
    margen_dec = min(0.99, max(0.0, margen_objetivo_pct / 100.0))

    codigo_sa6 = int(params.get("codigo_sa6", 640399))

    # --- 1. Parámetros de Fabricación Interna ---
    cv_fabril = float(params.get("costo_variable_unitario_fab", 16.0)) * to_usd
    cf_evitables = float(params.get("costos_fijos_evitables", 15000.0)) * to_usd
    cf_permanentes = float(params.get("costos_fijos_permanentes", 20000.0)) * to_usd

    costo_total_fabricar = (cv_fabril * cantidad_pares) + cf_evitables
    costo_unitario_fabricar = cv_fabril + (cf_evitables / cantidad_pares if cantidad_pares > 0 else 0.0)

    # --- 2. Parámetros de Importación Externa ---
    # Cotización base de compra
    p_compra = float(params.get("cotizacion_compra", 0.0)) * to_usd
    if params.get("usar_referencia_excel", False) or p_compra <= 0:
        p_compra = obtener_referencia_importacion_2024(codigo_sa6)

    # Gastos adicionales de importación discriminados
    flete = float(params.get("flete_transporte", 2.50)) * to_usd
    seguro = float(params.get("seguro_transporte", 0.30)) * to_usd
    arancel = float(params.get("gastos_internacion", 3.00)) * to_usd
    logistica = float(params.get("entrega_local", 1.00)) * to_usd
    otros = float(params.get("otros_gastos", 0.50)) * to_usd

    gastos_adicionales_totales = flete + seguro + arancel + logistica + otros
    costo_unitario_importar = p_compra + gastos_adicionales_totales
    costo_total_importar = costo_unitario_importar * cantidad_pares

    # --- 3. Precios Propuestos con Margen Objetivo sobre Venta ---
    # Formula: Precio = Costo / (1 - Margen)
    divisor_margen = max(0.01, 1.0 - margen_dec)
    precio_propuesto_fabricar = round(costo_unitario_fabricar / divisor_margen, 2)
    precio_propuesto_importar = round(costo_unitario_importar / divisor_margen, 2)

    # --- 4. Comparación y Decisión Económica ---
    diferencial_costo = round(costo_total_importar - costo_total_fabricar, 2)

    if diferencial_costo > 5.0:
        decision = "FABRICAR"
        mensaje_decision = f"Fabricar resulta más conveniente económicamente. Se ahorran $us. {diferencial_costo:,.2f} en el lote."
    elif diferencial_costo < -5.0:
        decision = "IMPORTAR"
        ahorro = abs(diferencial_costo)
        mensaje_decision = f"Importar resulta más conveniente económicamente. Se ahorran $us. {ahorro:,.2f} en el lote."
    else:
        decision = "EQUIVALENTE"
        mensaje_decision = "Ambas alternativas tienen costos prácticamente equivalentes. La decisión debe basarse en calidad, tiempos de entrega y preservación de mano de obra."

    # Punto de indiferencia en volumen (Q*)
    # (cv_f * Q) + cf_ev = cu_imp * Q  ==> Q*(cu_imp - cv_f) = cf_ev
    if costo_unitario_importar > cv_fabril and cf_evitables > 0:
        punto_indiferencia_pares = int(round(cf_evitables / (costo_unitario_importar - cv_fabril)))
    else:
        punto_indiferencia_pares = None

    # Margen e ingresos de cada alternativa si se vendieran al precio proyectado
    ingreso_total = round(precio_venta * cantidad_pares, 2)
    mb_fabricar = round(ingreso_total - costo_total_fabricar, 2)
    mb_importar = round(ingreso_total - costo_total_importar, 2)

    pct_mb_fabricar = round((mb_fabricar / max(1.0, ingreso_total)) * 100, 1) if ingreso_total > 0 else 0.0
    pct_mb_importar = round((mb_importar / max(1.0, ingreso_total)) * 100, 1) if ingreso_total > 0 else 0.0

    return {
        "exito": True,
        "configuracion": {
            "moneda_salida": moneda_in,
            "tasa_cambio": tc,
            "cantidad_pares": cantidad_pares,
            "precio_venta_unitario_usd": round(precio_venta, 2),
            "precio_venta_unitario_bob": round(precio_venta * tc, 2),
            "margen_objetivo_pct": margen_objetivo_pct,
            "codigo_sa6": str(codigo_sa6)
        },
        "fabricacion": {
            "costo_variable_unitario_usd": round(cv_fabril, 2),
            "costo_variable_unitario_bob": round(cv_fabril * tc, 2),
            "costos_fijos_evitables_usd": round(cf_evitables, 2),
            "costos_fijos_evitables_bob": round(cf_evitables * tc, 2),
            "costos_fijos_permanentes_usd": round(cf_permanentes, 2),
            "costos_fijos_permanentes_bob": round(cf_permanentes * tc, 2),
            "costo_unitario_total_usd": round(costo_unitario_fabricar, 2),
            "costo_unitario_total_bob": round(costo_unitario_fabricar * tc, 2),
            "costo_total_lote_usd": round(costo_total_fabricar, 2),
            "costo_total_lote_bob": round(costo_total_fabricar * tc, 2),
            "precio_propuesto_usd": round(precio_propuesto_fabricar, 2),
            "precio_propuesto_bob": round(precio_propuesto_fabricar * tc, 2),
            "margen_bruto_lote_usd": mb_fabricar,
            "margen_bruto_pct": pct_mb_fabricar
        },
        "importacion": {
            "cotizacion_base_usd": round(p_compra, 2),
            "cotizacion_base_bob": round(p_compra * tc, 2),
            "gastos_adicionales_usd": round(gastos_adicionales_totales, 2),
            "gastos_adicionales_bob": round(gastos_adicionales_totales * tc, 2),
            "desglose_gastos_usd": {
                "flete": round(flete, 2),
                "seguro": round(seguro, 2),
                "arancel_internacion": round(arancel, 2),
                "entrega_local": round(logistica, 2),
                "otros": round(otros, 2)
            },
            "costo_unitario_total_usd": round(costo_unitario_importar, 2),
            "costo_unitario_total_bob": round(costo_unitario_importar * tc, 2),
            "costo_total_lote_usd": round(costo_total_importar, 2),
            "costo_total_lote_bob": round(costo_total_importar * tc, 2),
            "precio_propuesto_usd": round(precio_propuesto_importar, 2),
            "precio_propuesto_bob": round(precio_propuesto_importar * tc, 2),
            "margen_bruto_lote_usd": mb_importar,
            "margen_bruto_pct": pct_mb_importar
        },
        "analisis_diferencial": {
            "diferencia_costo_usd": diferencial_costo,
            "diferencia_costo_bob": round(diferencial_costo * tc, 2),
            "decision_recomendada": decision,
            "mensaje": mensaje_decision,
            "punto_indiferencia_pares": punto_indiferencia_pares
        },
        "advertencia_legal": "Los costos fabriles, gastos de importacion y márgenes son parámetros de simulación. La cotización de compra referenciada del Excel refleja aduanas españolas y no constituye una oferta contractual para Bolivia."
    }


def obtener_escenario_predefinido(tipo: str) -> Dict[str, Any]:
    """Retorna los parametros de uno de los tres escenarios estandarizados y equilibrados."""
    if tipo == "importar_mas_conveniente":
        # Calzado deportivo masivo
        return {
            "nombre": "Escenario 1: Importar más conveniente (Calzado Deportivo Masivo)",
            "codigo_sa6": 640411,
            "cantidad_pares": 15000,
            "precio_venta": 25.00,
            "margen_objetivo_pct": 35.0,
            "costo_variable_unitario_fab": 16.50,
            "costos_fijos_evitables": 18000.0,
            "costos_fijos_permanentes": 12000.0,
            "usar_referencia_excel": False,
            "cotizacion_compra": 9.50,
            "flete_transporte": 1.80,
            "seguro_transporte": 0.20,
            "gastos_internacion": 1.50,
            "entrega_local": 0.70,
            "otros_gastos": 0.30
        }
    elif tipo == "fabricar_mas_conveniente":
        # Calzado formal de cuero de alta gama
        return {
            "nombre": "Escenario 2: Fabricar más conveniente (Calzado de Cuero Especializado)",
            "codigo_sa6": 640399,
            "cantidad_pares": 5000,
            "precio_venta": 45.00,
            "margen_objetivo_pct": 40.0,
            "costo_variable_unitario_fab": 18.00,
            "costos_fijos_evitables": 15000.0,
            "costos_fijos_permanentes": 14000.0,
            "usar_referencia_excel": False,
            "cotizacion_compra": 24.00,
            "flete_transporte": 2.50,
            "seguro_transporte": 0.30,
            "gastos_internacion": 3.60,
            "entrega_local": 1.00,
            "otros_gastos": 0.40
        }
    else:
        # Condiciones equivalentes / Punto de equilibrio
        return {
            "nombre": "Escenario 3: Condiciones equivalentes (Punto de Equilibrio)",
            "codigo_sa6": 640411,
            "cantidad_pares": 2000,
            "precio_venta": 28.00,
            "margen_objetivo_pct": 25.0,
            "costo_variable_unitario_fab": 14.00,
            "costos_fijos_evitables": 16000.0,
            "costos_fijos_permanentes": 10000.0,
            "usar_referencia_excel": False,
            "cotizacion_compra": 13.50,
            "flete_transporte": 3.00,
            "seguro_transporte": 0.50,
            "gastos_internacion": 3.50,
            "entrega_local": 1.00,
            "otros_gastos": 0.50
        }
