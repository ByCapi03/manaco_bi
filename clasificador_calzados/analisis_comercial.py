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


def obtener_referencia_comercial_excel(codigo_sa6: int, anio: Optional[int] = 2024) -> float:
    """
    Retorna el cociente ponderado SUM(Valor_USD)/SUM(Cantidad_pares) del Excel oficial,
    filtrando importaciones para la categoría SA6 y año seleccionado (default 2024).
    No promedia unitarios para garantizar consistencia volumétrica exacta.
    """
    df = cargar_dataset_excel()
    cond = (df["Flujo_comercial"] == "Importación") & (df["Código_SA6"] == int(codigo_sa6))
    if anio and int(anio) > 0:
        cond = cond & (df["Año"] == int(anio))
    sub = df[cond]
    v = float(sub["Valor_USD"].sum())
    p = float(sub["Cantidad_pares"].sum())
    if p > 0:
        return round(v / p, 2)
    return 0.0


def obtener_referencia_importacion_2024(codigo_sa6: int) -> float:
    """Retorna la referencia comercial ponderada del año 2024 para una categoría SA6."""
    return obtener_referencia_comercial_excel(codigo_sa6, 2024)


def calcular_escenario_make_or_buy(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculadora unificada y diferencial de toma de decisiones: Fabricar vs Importar.
    
    Fórmulas centralizadas:
    - Costo fabricar = volumen × costo variable por par + costos fijos evitables.
    - Costo importar = volumen × (referencia comercial + gastos adicionales por par) + gastos fijos de importación.
    - Costo unitario = costo total / volumen.
    - Diferencia = costo fabricar − costo importar.
      Positiva: importar cuesta menos.
      Negativa: fabricar cuesta menos.
      Dentro de la tolerancia monetaria (±$5.00 USD): "Costos equivalentes".
    - No cuenta costos fijos permanentes comunes como ahorro por importar.
    - Precio propuesto = costo unitario elegido / (1 - margen objetivo / 100).
    """
    tc = float(params.get("tasa_cambio", TASA_CAMBIO_OFICIAL) or TASA_CAMBIO_OFICIAL)
    moneda_in = str(params.get("moneda", "USD")).upper()
    es_bob = (moneda_in == "BOB")
    to_usd = (1.0 / tc) if es_bob else 1.0

    # 1. Validación de volumen
    raw_q = params.get("cantidad_pares")
    if raw_q is None:
        return {
            "exito": False,
            "error": "Completa los parámetros: ingresa la cantidad de pares.",
            "codigo_error": "VOLUMEN_FALTANTE"
        }
    try:
        cantidad_pares = int(float(str(raw_q).replace(",", ".")))
    except (ValueError, TypeError):
        return {
            "exito": False,
            "error": "Completa los parámetros: la cantidad de pares debe ser un número entero mayor que 0.",
            "codigo_error": "VOLUMEN_INVALIDO"
        }

    if cantidad_pares <= 0:
        return {
            "exito": False,
            "error": "Completa los parámetros: la cantidad de pares debe ser mayor que 0.",
            "codigo_error": "VOLUMEN_NO_POSITIVO"
        }

    # 2. Validación de costos
    try:
        cv_fabril = float(str(params.get("costo_variable_unitario_fab", 0.0)).replace(",", ".")) * to_usd
        cf_evitables = float(str(params.get("costos_fijos_evitables", 0.0)).replace(",", ".")) * to_usd
        cf_permanentes = float(str(params.get("costos_fijos_permanentes", 0.0)).replace(",", ".")) * to_usd
        gastos_importacion = float(str(params.get("gastos_importacion", params.get("gastos_adicionales", 0.0))).replace(",", ".")) * to_usd
        gastos_fijos_importacion = float(str(params.get("gastos_fijos_importacion", 0.0)).replace(",", ".")) * to_usd
    except (ValueError, TypeError):
        return {
            "exito": False,
            "error": "Completa los parámetros: formato numérico inválido en costos.",
            "codigo_error": "COSTOS_INVALIDOS"
        }

    if cv_fabril < 0 or cf_evitables < 0 or cf_permanentes < 0 or gastos_importacion < 0 or gastos_fijos_importacion < 0:
        return {
            "exito": False,
            "error": "Completa los parámetros: los costos no pueden ser negativos.",
            "codigo_error": "COSTOS_NEGATIVOS"
        }

    # 3. Validación de margen objetivo
    try:
        margen_objetivo_pct = float(str(params.get("margen_objetivo_pct", 35.0)).replace(",", "."))
    except (ValueError, TypeError):
        margen_objetivo_pct = 35.0

    if margen_objetivo_pct < 0 or margen_objetivo_pct >= 100.0:
        return {
            "exito": False,
            "error": "Completa los parámetros: el margen objetivo debe estar entre 0% y menos de 100%.",
            "codigo_error": "MARGEN_INVALIDO"
        }

    # 4. Referencia comercial de importación
    codigo_sa6 = int(params.get("codigo_sa6", 640399))
    anio_ref = int(params.get("anio_referencia", 2024) or 2024)

    raw_compra = params.get("cotizacion_compra", params.get("referencia_comercial"))
    if raw_compra is not None and float(str(raw_compra).replace(",", ".")) > 0:
        p_compra = float(str(raw_compra).replace(",", ".")) * to_usd
    else:
        p_compra = obtener_referencia_comercial_excel(codigo_sa6, anio_ref)
        if p_compra <= 0:
            p_compra = obtener_referencia_importacion_2024(codigo_sa6)

    # Compatibilidad con escenarios predefinidos antiguos con gastos desglosados
    if gastos_importacion <= 0 and ("flete_transporte" in params or "gastos_internacion" in params):
        flete = float(params.get("flete_transporte", 0.0)) * to_usd
        seguro = float(params.get("seguro_transporte", 0.0)) * to_usd
        arancel = float(params.get("gastos_internacion", 0.0)) * to_usd
        logistica = float(params.get("entrega_local", 0.0)) * to_usd
        otros = float(params.get("otros_gastos", 0.0)) * to_usd
        gastos_importacion = flete + seguro + arancel + logistica + otros

    # --- 5. Fórmulas Centrales ---
    # Costo Fabricar
    costo_total_fabricar = (cv_fabril * cantidad_pares) + cf_evitables
    costo_unitario_fabricar = costo_total_fabricar / cantidad_pares

    # Costo Importar
    costo_total_importar = (cantidad_pares * (p_compra + gastos_importacion)) + gastos_fijos_importacion
    costo_unitario_importar = costo_total_importar / cantidad_pares

    # Diferencia = Costo Fabricar - Costo Importar
    diferencia_costo_total = costo_total_fabricar - costo_total_importar
    diferencia_costo_unitario = costo_unitario_fabricar - costo_unitario_importar

    tolerancia_monetaria = 5.0  # USD

    if diferencia_costo_total > tolerancia_monetaria:
        decision = "IMPORTAR"
        decision_texto = "Conviene importar"
        ahorro_lote = diferencia_costo_total
        ahorro_unit = diferencia_costo_unitario
        conclusion_texto = f"Importar cuesta menos. Se ahorran $ {ahorro_lote:,.2f} USD en el lote."
        mensaje = f"Importar resulta más conveniente económicamente. Se ahorran $us. {ahorro_lote:,.2f} en el lote."
        es_equivalente = False
    elif diferencia_costo_total < -tolerancia_monetaria:
        decision = "FABRICAR"
        decision_texto = "Conviene fabricar"
        ahorro_lote = abs(diferencia_costo_total)
        ahorro_unit = abs(diferencia_costo_unitario)
        conclusion_texto = f"Fabricar cuesta menos. Se ahorran $ {ahorro_lote:,.2f} USD en el lote."
        mensaje = f"Fabricar resulta más conveniente económicamente. Se ahorran $us. {ahorro_lote:,.2f} en el lote."
        es_equivalente = False
    else:
        decision = "EQUIVALENTE"
        decision_texto = "Costos equivalentes"
        ahorro_lote = 0.0
        ahorro_unit = 0.0
        conclusion_texto = f"Costos equivalentes (diferencia dentro de tolerancia de ±${tolerancia_monetaria:.2f} USD)."
        mensaje = "Ambas alternativas tienen costos prácticamente equivalentes dentro de la tolerancia."
        es_equivalente = True

    # --- 6. Punto de Indiferencia ---
    # (cv_fabril * Q) + cf_evitables = Q * (p_compra + gastos_importacion) + gastos_fijos_importacion
    numerador = cf_evitables - gastos_fijos_importacion
    denominador = (p_compra + gastos_importacion) - cv_fabril

    if abs(denominador) > 1e-6:
        q_star_raw = numerador / denominador
        if q_star_raw > 0:
            punto_indiferencia_pares = int(round(q_star_raw))
            costo_indiferencia_usd = round((cv_fabril * punto_indiferencia_pares) + cf_evitables, 2)
        else:
            punto_indiferencia_pares = None
            costo_indiferencia_usd = None
    else:
        punto_indiferencia_pares = None
        costo_indiferencia_usd = None

    # Rango visible de simulación
    q_min = max(100, int(cantidad_pares * 0.1))
    q_max = max(int(cantidad_pares * 2), 6000)

    if punto_indiferencia_pares is not None:
        if punto_indiferencia_pares < q_min or punto_indiferencia_pares > q_max:
            cruce_fuera_rango = True
            mensaje_indiferencia = f"Punto de indiferencia: {punto_indiferencia_pares:,} pares (cruce fuera del rango mostrado de {q_min:,} a {q_max:,} pares)."
        else:
            cruce_fuera_rango = False
            mensaje_indiferencia = f"Punto de indiferencia: {punto_indiferencia_pares:,} pares (costos iguales en $ {costo_indiferencia_usd:,.2f} USD)."
    else:
        cruce_fuera_rango = False
        mensaje_indiferencia = "No existe cruce para volúmenes positivos (una alternativa domina en todo el rango)."

    # Generación de puntos de curva {x, y}
    puntos_x = {q_min, cantidad_pares, q_max}
    pasos = 8
    step = max(100, (q_max - q_min) // pasos)
    for i in range(1, pasos):
        puntos_x.add(q_min + i * step)
    if punto_indiferencia_pares is not None and not cruce_fuera_rango:
        puntos_x.add(punto_indiferencia_pares)

    lista_x = sorted(list(puntos_x))
    curva_volumen = []
    for x in lista_x:
        cfab_x = (cv_fabril * x) + cf_evitables
        cimp_x = (x * (p_compra + gastos_importacion)) + gastos_fijos_importacion
        curva_volumen.append({
            "x": x,
            "costo_fabricar_usd": round(cfab_x, 2),
            "costo_fabricar_bob": round(cfab_x * tc, 2),
            "costo_importar_usd": round(cimp_x, 2),
            "costo_importar_bob": round(cimp_x * tc, 2)
        })

    # --- 7. Fijación de Precios ---
    alternativa_precio = str(params.get("alternativa_precio", "recomendada")).lower()
    if alternativa_precio == "fabricar":
        costo_unitario_elegido = costo_unitario_fabricar
        alternativa_label = "Fabricar"
    elif alternativa_precio == "importar":
        costo_unitario_elegido = costo_unitario_importar
        alternativa_label = "Importar"
    else:  # recomendada
        if decision == "IMPORTAR":
            costo_unitario_elegido = costo_unitario_importar
            alternativa_label = "Importar (menor costo)"
        elif decision == "FABRICAR":
            costo_unitario_elegido = costo_unitario_fabricar
            alternativa_label = "Fabricar (menor costo)"
        else:
            costo_unitario_elegido = costo_unitario_fabricar
            alternativa_label = "Fabricar (costos equivalentes)"

    margen_dec = min(0.999, max(0.0, margen_objetivo_pct / 100.0))
    divisor = max(0.001, 1.0 - margen_dec)
    precio_propuesto_fabricar = round(costo_unitario_fabricar / divisor, 2)
    precio_propuesto_importar = round(costo_unitario_importar / divisor, 2)
    precio_propuesto_elegido = round(costo_unitario_elegido / divisor, 2)

    return {
        "exito": True,
        "configuracion": {
            "moneda_salida": moneda_in,
            "tasa_cambio": tc,
            "cantidad_pares": cantidad_pares,
            "codigo_sa6": str(codigo_sa6),
            "margen_objetivo_pct": margen_objetivo_pct,
            "alternativa_precio": alternativa_precio
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
            "precio_propuesto_usd": precio_propuesto_fabricar,
            "precio_propuesto_bob": round(precio_propuesto_fabricar * tc, 2)
        },
        "importacion": {
            "referencia_comercial_usd": round(p_compra, 2),
            "referencia_comercial_bob": round(p_compra * tc, 2),
            "cotizacion_base_usd": round(p_compra, 2),
            "cotizacion_base_bob": round(p_compra * tc, 2),
            "gastos_adicionales_usd": round(gastos_importacion, 2),
            "gastos_adicionales_bob": round(gastos_importacion * tc, 2),
            "gastos_fijos_importacion_usd": round(gastos_fijos_importacion, 2),
            "gastos_fijos_importacion_bob": round(gastos_fijos_importacion * tc, 2),
            "costo_unitario_total_usd": round(costo_unitario_importar, 2),
            "costo_unitario_total_bob": round(costo_unitario_importar * tc, 2),
            "costo_total_lote_usd": round(costo_total_importar, 2),
            "costo_total_lote_bob": round(costo_total_importar * tc, 2),
            "precio_propuesto_usd": precio_propuesto_importar,
            "precio_propuesto_bob": round(precio_propuesto_importar * tc, 2)
        },
        "analisis_diferencial": {
            "diferencia_costo_usd": round(diferencia_costo_total, 2),
            "diferencia_costo_bob": round(diferencia_costo_total * tc, 2),
            "diferencia_costo_unitario_usd": round(diferencia_costo_unitario, 2),
            "diferencia_costo_unitario_bob": round(diferencia_costo_unitario * tc, 2),
            "decision_recomendada": decision,
            "decision_texto": decision_texto,
            "conclusion_texto": conclusion_texto,
            "mensaje": mensaje,
            "ahorro_lote_usd": round(ahorro_lote, 2),
            "ahorro_lote_bob": round(ahorro_lote * tc, 2),
            "ahorro_unitario_usd": round(ahorro_unit, 2),
            "ahorro_unitario_bob": round(ahorro_unit * tc, 2),
            "es_equivalente": es_equivalente,
            "tolerancia_monetaria_usd": tolerancia_monetaria,
            "punto_indiferencia_pares": punto_indiferencia_pares,
            "punto_indiferencia_costo_usd": costo_indiferencia_usd,
            "cruce_fuera_rango": cruce_fuera_rango,
            "mensaje_indiferencia": mensaje_indiferencia
        },
        "precio_propuesto": {
            "alternativa_utilizada": alternativa_precio,
            "alternativa_label": alternativa_label,
            "costo_unitario_usd": round(costo_unitario_elegido, 2),
            "costo_unitario_bob": round(costo_unitario_elegido * tc, 2),
            "margen_objetivo_pct": margen_objetivo_pct,
            "precio_sugerido_usd": precio_propuesto_elegido,
            "precio_sugerido_bob": round(precio_propuesto_elegido * tc, 2)
        },
        "curva_volumen": curva_volumen,
        "advertencia_legal": "Estimación con parámetros de simulación. La cotización de compra referenciada del Excel refleja comercio exterior de España y no constituye una cotización contractual para Bolivia."
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


def calcular_metricas_dashboard_resumen(
    anio: Optional[int] = None,
    socio: Optional[str] = None,
    codigo_sa6: Optional[int] = None,
    medida: str = "USD"
) -> Dict[str, Any]:
    """
    Calcula las agregaciones oficiales para el Dashboard Resumen a partir de BDatos_MANACO.xlsx.
    Aplica filtros de Año, País Socio y Categoría, y genera series para:
      1. Importaciones vs Exportaciones por año (ordenados, sin ceros ficticios).
      2. Top 10 socios comerciales (ranking calculado DESPUÉS de aplicar filtros).
      3. Comparación por categoría y flujo.
    """
    df = cargar_dataset_excel()

    sub = df.copy()
    if anio is not None and int(anio) > 0:
        sub = sub[sub["Año"] == int(anio)]
    if socio and socio.strip() and socio.strip().upper() not in ["TODOS", "ALL", ""]:
        sub = sub[sub["Socio_comercial"] == socio.strip()]
    if codigo_sa6 is not None and int(codigo_sa6) > 0:
        sub = sub[sub["Código_SA6"] == int(codigo_sa6)]

    total_registros = len(sub)
    if total_registros == 0:
        return {
            "exito": True,
            "hay_datos": False,
            "total_registros": 0,
            "medida": medida.upper(),
            "kpis": {
                "valor_importado_usd": None,
                "valor_exportado_usd": None,
                "pares_registrados": None,
                "pares_importados": None,
                "pares_exportados": None
            },
            "grafico_anios": {"anios": [], "importacion": [], "exportacion": []},
            "grafico_socios": {"socios": [], "importacion": [], "exportacion": []},
            "grafico_categorias": {"categorias": [], "importacion": [], "exportacion": []},
            "mensaje": "Sin datos"
        }

    sub_imp = sub[sub["Flujo_comercial"].str.startswith("Import")]
    sub_exp = sub[sub["Flujo_comercial"].str.startswith("Export")]

    v_imp = float(sub_imp["Valor_USD"].sum()) if not sub_imp.empty else 0.0
    v_exp = float(sub_exp["Valor_USD"].sum()) if not sub_exp.empty else 0.0
    p_imp = int(sub_imp["Cantidad_pares"].sum()) if not sub_imp.empty else 0
    p_exp = int(sub_exp["Cantidad_pares"].sum()) if not sub_exp.empty else 0
    p_tot = int(sub["Cantidad_pares"].sum())

    # 1. Gráfico: Importaciones vs Exportaciones por año
    anios_presentes = sorted(sub["Año"].unique().tolist())
    anios_labels = [str(a) for a in anios_presentes]
    imp_anios_usd = []
    exp_anios_usd = []
    imp_anios_pares = []
    exp_anios_pares = []

    for a in anios_presentes:
        val_i = float(sub_imp[sub_imp["Año"] == a]["Valor_USD"].sum()) if not sub_imp.empty else 0.0
        val_e = float(sub_exp[sub_exp["Año"] == a]["Valor_USD"].sum()) if not sub_exp.empty else 0.0
        par_i = int(sub_imp[sub_imp["Año"] == a]["Cantidad_pares"].sum()) if not sub_imp.empty else 0
        par_e = int(sub_exp[sub_exp["Año"] == a]["Cantidad_pares"].sum()) if not sub_exp.empty else 0

        imp_anios_usd.append(round(val_i, 2))
        exp_anios_usd.append(round(val_e, 2))
        imp_anios_pares.append(par_i)
        exp_anios_pares.append(par_e)

    # 2. Gráfico: Top 10 Socios (ranking calculado tras aplicar filtros)
    es_pares = (medida.upper() == "PARES")
    grp_socios = sub.groupby("Socio_comercial").agg({
        "Valor_USD": "sum",
        "Cantidad_pares": "sum"
    }).reset_index()

    criterio_orden = "Cantidad_pares" if es_pares else "Valor_USD"
    grp_top10 = grp_socios.sort_values(criterio_orden, ascending=False).head(10)

    socios_labels = []
    imp_socios_usd = []
    exp_socios_usd = []
    imp_socios_pares = []
    exp_socios_pares = []

    for _, row in grp_top10.iterrows():
        s = row["Socio_comercial"]
        socios_labels.append(str(s))
        s_imp = sub_imp[sub_imp["Socio_comercial"] == s]
        s_exp = sub_exp[sub_exp["Socio_comercial"] == s]

        val_i = float(s_imp["Valor_USD"].sum()) if not s_imp.empty else 0.0
        val_e = float(s_exp["Valor_USD"].sum()) if not s_exp.empty else 0.0
        par_i = int(s_imp["Cantidad_pares"].sum()) if not s_imp.empty else 0
        par_e = int(s_exp["Cantidad_pares"].sum()) if not s_exp.empty else 0

        imp_socios_usd.append(round(val_i, 2))
        exp_socios_usd.append(round(val_e, 2))
        imp_socios_pares.append(par_i)
        exp_socios_pares.append(par_e)

    # 3. Gráfico: Comparación por categoría
    nombres_cats = {
        640411: "Deportivo (640411)",
        640399: "Casual Cuero (640399)",
        640420: "Formal Vestir (640420)"
    }
    sa6_presentes = [sa for sa in [640411, 640399, 640420] if sa in sub["Código_SA6"].unique()]
    cats_labels = [nombres_cats.get(sa, str(sa)) for sa in sa6_presentes]
    imp_cats_usd = []
    exp_cats_usd = []
    imp_cats_pares = []
    exp_cats_pares = []

    for sa in sa6_presentes:
        c_imp = sub_imp[sub_imp["Código_SA6"] == sa]
        c_exp = sub_exp[sub_exp["Código_SA6"] == sa]

        val_i = float(c_imp["Valor_USD"].sum()) if not c_imp.empty else 0.0
        val_e = float(c_exp["Valor_USD"].sum()) if not c_exp.empty else 0.0
        par_i = int(c_imp["Cantidad_pares"].sum()) if not c_imp.empty else 0
        par_e = int(c_exp["Cantidad_pares"].sum()) if not c_exp.empty else 0

        imp_cats_usd.append(round(val_i, 2))
        exp_cats_usd.append(round(val_e, 2))
        imp_cats_pares.append(par_i)
        exp_cats_pares.append(par_e)

    return {
        "exito": True,
        "hay_datos": True,
        "total_registros": total_registros,
        "medida": medida.upper(),
        "kpis": {
            "valor_importado_usd": round(v_imp, 2),
            "valor_exportado_usd": round(v_exp, 2),
            "pares_registrados": p_tot,
            "pares_importados": p_imp,
            "pares_exportados": p_exp
        },
        "grafico_anios": {
            "anios": anios_labels,
            "importacion_usd": imp_anios_usd,
            "exportacion_usd": exp_anios_usd,
            "importacion_pares": imp_anios_pares,
            "exportacion_pares": exp_anios_pares
        },
        "grafico_socios": {
            "socios": socios_labels,
            "importacion_usd": imp_socios_usd,
            "exportacion_usd": exp_socios_usd,
            "importacion_pares": imp_socios_pares,
            "exportacion_pares": exp_socios_pares
        },
        "grafico_categorias": {
            "categorias": cats_labels,
            "importacion_usd": imp_cats_usd,
            "exportacion_usd": exp_cats_usd,
            "importacion_pares": imp_cats_pares,
            "exportacion_pares": exp_cats_pares
        },
        "fuente": "Comercio exterior de España, 2020–2024"
    }


def obtener_participacion_categorias_excel(
    anio: Optional[int] = None,
    flujo: Optional[str] = None,
    medida: str = "USD"
) -> Dict[str, Any]:
    """
    Calcula porcentajes de participación por categoría SA6 directamente del Excel BDatos_MANACO.xlsx.
    Soporta filtros de Año (2020-2024 o Todos), Flujo (Importación, Exportación o Todos) y Medida (USD o Pares).
    """
    df = cargar_dataset_excel()
    sub = df.copy()

    if anio is not None and str(anio).isdigit() and int(anio) > 0:
        sub = sub[sub["Año"] == int(anio)]

    if flujo and str(flujo).strip().upper() not in ["TODOS", "ALL", ""]:
        sub = sub[sub["Flujo_comercial"].str.startswith(str(flujo).strip()[:4])]

    total_registros = len(sub)
    if total_registros == 0:
        return {
            "exito": True,
            "hay_datos": False,
            "total": 0,
            "medida": medida.upper(),
            "categorias": [],
            "mayor_participacion": "Sin datos",
            "mayor_porcentaje": 0.0
        }

    col = "Valor_USD" if medida.upper() == "USD" else "Cantidad_pares"
    total = float(sub[col].sum())

    nombres = {
        640411: "Calzado Deportivo (640411)",
        640399: "Calzado Casual Cuero (640399)",
        640420: "Calzado Formal Vestir (640420)"
    }

    categorias = []
    for sa in [640411, 640399, 640420]:
        sub_c = sub[sub["Código_SA6"] == sa]
        val = float(sub_c[col].sum()) if not sub_c.empty else 0.0
        pct = round((val / max(1.0, total)) * 100, 1) if total > 0 else 0.0
        categorias.append({
            "codigo_sa6": sa,
            "nombre": nombres.get(sa, str(sa)),
            "valor": round(val, 2) if medida.upper() == "USD" else int(val),
            "porcentaje": pct
        })

    mayor = max(categorias, key=lambda x: x["valor"]) if categorias else None

    return {
        "exito": True,
        "hay_datos": True,
        "total": round(total, 2) if medida.upper() == "USD" else int(total),
        "medida": medida.upper(),
        "categorias": categorias,
        "mayor_participacion": mayor["nombre"] if mayor else "N/D",
        "mayor_porcentaje": mayor["porcentaje"] if mayor else 0.0
    }


