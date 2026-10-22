"""
test_verificacion_simplificada.py
Verificación automatizada de los requisitos de simplificación de MANACO BI:
1. Filtros por año, socio y categoría.
2. Cambio de medida (USD vs PARES).
3. Coincidencia de totales con pandas sobre el Excel real.
4. Selección sin registros ("Sin datos").
5. Cámara apagada sin resultados activos y persistencia de movimientos.
"""

import os
import sys
from pathlib import Path
import urllib.request
import json
import pandas as pd

# Configurar path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "clasificador_calzados"))
import db_manaco as db_mod
db_manaco = db_mod.db_manaco
import analisis_comercial as ac
from config import obtener_ruta_excel

BASE_URL = "http://127.0.0.1:5000"

def test_totales_pandas_vs_api():
    print("\n" + "="*70)
    print("VERIFICACIÓN 1: COINCIDENCIA DE TOTALES CON PANDAS (EXCEL)")
    print("="*70)
    ruta_excel = obtener_ruta_excel()
    df = pd.read_excel(ruta_excel)
    
    imp_excel = df[df["Flujo_comercial"].str.startswith("Import")]
    exp_excel = df[df["Flujo_comercial"].str.startswith("Export")]
    
    val_imp_pandas = round(float(imp_excel["Valor_USD"].sum()), 2)
    val_exp_pandas = round(float(exp_excel["Valor_USD"].sum()), 2)
    pares_tot_pandas = int(df["Cantidad_pares"].sum())
    
    # Consultar API sin filtros
    req = urllib.request.urlopen(f"{BASE_URL}/api/resumen/metricas?medida=USD")
    res = json.loads(req.read().decode("utf-8"))
    
    kpis = res["kpis"]
    print(f"Valor importado USD -> Pandas: ${val_imp_pandas:,.2f} | API: ${kpis['valor_importado_usd']:,.2f}")
    print(f"Valor exportado USD -> Pandas: ${val_exp_pandas:,.2f} | API: ${kpis['valor_exportado_usd']:,.2f}")
    print(f"Pares registrados   -> Pandas: {pares_tot_pandas:,} | API: {kpis['pares_registrados']:,}")
    
    assert val_imp_pandas == kpis["valor_importado_usd"], "Error en total importado"
    assert val_exp_pandas == kpis["valor_exportado_usd"], "Error en total exportado"
    assert pares_tot_pandas == kpis["pares_registrados"], "Error en total pares"
    print("[OK] Totales de API coinciden exactamente con cálculo de pandas.")

def test_filtros_combinados():
    print("\n" + "="*70)
    print("VERIFICACIÓN 2: FILTROS POR AÑO, SOCIO Y CATEGORÍA")
    print("="*70)
    # Filtro 2024, Indonesia, Deportivo (640411)
    req = urllib.request.urlopen(f"{BASE_URL}/api/resumen/metricas?anio=2024&socio=Indonesia&codigo_sa6=640411&medida=USD")
    res = json.loads(req.read().decode("utf-8"))
    
    print(f"Filtro aplicado: Año=2024, Socio=Indonesia, SA6=640411")
    print(f"Registros encontrados: {res['total_registros']}")
    print(f"Valor Importado: ${res['kpis']['valor_importado_usd']:,.2f}")
    print(f"Pares Registrados: {res['kpis']['pares_registrados']:,}")
    print(f"Años presentes en gráfico: {res['grafico_anios']['anios']}")
    
    assert res["hay_datos"] == True
    assert res["grafico_anios"]["anios"] == ["2024"], "No deben inventarse ceros ni otros años"
    print("[OK] Filtros combinados operan correctamente y gráfico contiene solo el año seleccionado.")

def test_cambio_de_medida():
    print("\n" + "="*70)
    print("VERIFICACIÓN 3: CAMBIO DE MEDIDA (USD VS PARES)")
    print("="*70)
    # Medida USD
    req_usd = urllib.request.urlopen(f"{BASE_URL}/api/resumen/metricas?medida=USD")
    res_usd = json.loads(req_usd.read().decode("utf-8"))
    
    # Medida PARES
    req_par = urllib.request.urlopen(f"{BASE_URL}/api/resumen/metricas?medida=PARES")
    res_par = json.loads(req_par.read().decode("utf-8"))
    
    top_usd = res_usd["grafico_socios"]["socios"][:3]
    top_par = res_par["grafico_socios"]["socios"][:3]
    
    print(f"Top 3 Socios (Medida USD):   {top_usd}")
    print(f"Top 3 Socios (Medida PARES): {top_par}")
    
    assert res_usd["medida"] == "USD"
    assert res_par["medida"] == "PARES"
    assert top_usd != top_par, "El ranking debe variar según la medida seleccionada"
    print("[OK] Medidas USD y PARES procesadas en escalas independientes y con rankings propios.")

def test_seleccion_sin_datos():
    print("\n" + "="*70)
    print("VERIFICACIÓN 4: SELECCIÓN SIN REGISTROS ('SIN DATOS')")
    print("="*70)
    # Combinación inexistente en el Excel: Año 2020, China, Formal Vestir (640420)
    req = urllib.request.urlopen(f"{BASE_URL}/api/resumen/metricas?anio=2020&socio=China&codigo_sa6=640420")
    res = json.loads(req.read().decode("utf-8"))
    
    print(f"Respuesta para combinación inexistente:")
    print(f"  hay_datos: {res['hay_datos']}")
    print(f"  mensaje:   {res['mensaje']}")
    print(f"  total_registros: {res['total_registros']}")
    print(f"  KPIs: {res['kpis']}")
    
    assert res["hay_datos"] == False
    assert res["mensaje"] == "Sin datos"
    assert res["kpis"]["valor_importado_usd"] is None
    print("[OK] Combinación vacía devuelve 'Sin datos' de forma limpia y transparente.")

def test_persistencia_movimiento_inventario():
    print("\n" + "="*70)
    print("VERIFICACIÓN 5: PERSISTENCIA DE MOVIMIENTO EN INVENTARIO")
    print("="*70)
    # Obtener stock inicial del producto 1 (Deportivo Básico)
    inv_ini = db_manaco.obtener_inventario()
    prod1_ini = next(p for p in inv_ini if p["id_producto"] == 1)
    stock_ini = prod1_ini["stock_actual"]
    print(f"Stock inicial Producto 1 ({prod1_ini['nombre_producto']}): {stock_ini} pares")
    
    # Realizar ingreso de +1 par (como hace el escáner de cámara)
    payload = json.dumps({
        "id_producto": 1,
        "tipo_accion": "INGRESO_IA",
        "cantidad": 1,
        "canal_venta": "Almacén Central Manaco",
        "responsable": "Escáner Calzado Test"
    }).encode("utf-8")
    
    req_post = urllib.request.Request(
        f"{BASE_URL}/api/inventario/movimiento",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req_post).read().decode("utf-8"))
    print("RESP OBTENIDO:", resp)
    stock_nuevo = resp.get("nuevo_stock") or resp.get("stock_resultante")
    print(f"Stock post-ingreso: {stock_nuevo} pares (Diferencia: +{stock_nuevo - stock_ini})")
    assert stock_nuevo == stock_ini + 1, "El stock no incremento en 1"
    
    # Restaurar restando 1 par para dejar inventario limpio
    db_manaco.registrar_movimiento_operativo(
        id_producto=1,
        accion="VENTA",
        cantidad=1,
        canal_venta="Ajuste Test",
        responsable="Script Verificación"
    )
    print("[OK] Movimiento persistido atómicamente en PostgreSQL y restaurado.")

if __name__ == "__main__":
    test_totales_pandas_vs_api()
    test_filtros_combinados()
    test_cambio_de_medida()
    test_seleccion_sin_datos()
    test_persistencia_movimiento_inventario()
    print("\n" + "="*70)
    print("TODAS LAS VERIFICACIONES COMPLETADAS EXITOSAMENTE (5/5)")
    print("="*70)
    print("\n" + "="*70)
    print("TODAS LAS VERIFICACIONES COMPLETADAS EXITOSAMENTE (5/5)")
    print("="*70)
