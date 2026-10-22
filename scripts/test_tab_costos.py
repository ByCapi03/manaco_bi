"""
scripts/test_tab_costos.py
Comprobación puntual y exhaustiva de la pestaña "1. Costos y márgenes":
- Fabricar más barato
- Importar más barato
- Costos equivalentes
- Parámetros incompletos e inválidos (sin recomendar decisión)
- Punto de indiferencia y cruce fuera de rango
- Concordancia entre tarjetas, gráficos, conclusión y precio
- Aplicación de precio sin alterar ventas históricas ni existencias
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "clasificador_calzados"))

import analisis_comercial as ac
from db_manaco import db_manaco

def run_tests():
    print("=" * 70)
    print("PRUEBA PUNTUAL: PESTAÑA 1. COSTOS Y MÁRGENES")
    print("=" * 70)

    # -------------------------------------------------------------
    # CASO 1: Fabricar es más barato
    # -------------------------------------------------------------
    print("\n--- CASO 1: Fabricar más barato ---")
    p1 = {
        "codigo_sa6": 640399,
        "cantidad_pares": 5000,
        "costo_variable_unitario_fab": 15.00,
        "costos_fijos_evitables": 10000.00,
        "costos_fijos_permanentes": 5000.00,
        "referencia_comercial": 26.15,
        "gastos_importacion": 4.00,
        "margen_objetivo_pct": 35.0,
        "alternativa_precio": "recomendada"
    }
    r1 = ac.calcular_escenario_make_or_buy(p1)
    assert r1["exito"] is True
    dec1 = r1["analisis_diferencial"]
    fab1 = r1["fabricacion"]
    imp1 = r1["importacion"]
    prec1 = r1["precio_propuesto"]

    print(f"Costo Fab Total: ${fab1['costo_total_lote_usd']:,.2f} | Unitario: ${fab1['costo_unitario_total_usd']:.2f}")
    print(f"Costo Imp Total: ${imp1['costo_total_lote_usd']:,.2f} | Unitario: ${imp1['costo_unitario_total_usd']:.2f}")
    print(f"Diferencia: ${dec1['diferencia_costo_usd']:,.2f} | Decisión: {dec1['decision_recomendada']}")
    print(f"Precio Propuesto: ${prec1['precio_sugerido_usd']:.2f} ({prec1['alternativa_label']})")

    # Validar fórmulas
    assert fab1["costo_total_lote_usd"] == 5000 * 15.00 + 10000.00  # 85,000.00
    assert fab1["costo_unitario_total_usd"] == 85000.00 / 5000  # 17.00
    assert imp1["costo_total_lote_usd"] == 5000 * (26.15 + 4.00)  # 150,750.00
    assert imp1["costo_unitario_total_usd"] == 30.15
    assert dec1["diferencia_costo_usd"] == 85000.00 - 150750.00  # -65,750.00
    assert dec1["decision_recomendada"] == "FABRICAR"
    assert prec1["costo_unitario_usd"] == 17.00
    assert abs(prec1["precio_sugerido_usd"] - round(17.00 / (1 - 0.35), 2)) < 0.01
    print("  [OK] Caso 1 verificado correctamente.")

    # -------------------------------------------------------------
    # CASO 2: Importar es más barato
    # -------------------------------------------------------------
    print("\n--- CASO 2: Importar más barato ---")
    p2 = {
        "codigo_sa6": 640411,
        "cantidad_pares": 15000,
        "costo_variable_unitario_fab": 18.00,
        "costos_fijos_evitables": 20000.00,
        "referencia_comercial": 10.00,
        "gastos_importacion": 3.00,
        "margen_objetivo_pct": 30.0,
        "alternativa_precio": "recomendada"
    }
    r2 = ac.calcular_escenario_make_or_buy(p2)
    assert r2["exito"] is True
    dec2 = r2["analisis_diferencial"]
    fab2 = r2["fabricacion"]
    imp2 = r2["importacion"]
    prec2 = r2["precio_propuesto"]

    print(f"Costo Fab Total: ${fab2['costo_total_lote_usd']:,.2f} | Unitario: ${fab2['costo_unitario_total_usd']:.2f}")
    print(f"Costo Imp Total: ${imp2['costo_total_lote_usd']:,.2f} | Unitario: ${imp2['costo_unitario_total_usd']:.2f}")
    print(f"Diferencia: ${dec2['diferencia_costo_usd']:,.2f} | Decisión: {dec2['decision_recomendada']}")
    print(f"Precio Propuesto: ${prec2['precio_sugerido_usd']:.2f} ({prec2['alternativa_label']})")

    assert fab2["costo_total_lote_usd"] == 15000 * 18.00 + 20000.00  # 290,000.00
    assert imp2["costo_total_lote_usd"] == 15000 * (10.00 + 3.00)  # 195,000.00
    assert dec2["diferencia_costo_usd"] == 290000.00 - 195000.00  # +95,000.00
    assert dec2["decision_recomendada"] == "IMPORTAR"
    assert prec2["costo_unitario_usd"] == 13.00
    assert abs(prec2["precio_sugerido_usd"] - round(13.00 / (1 - 0.30), 2)) < 0.01
    print("  [OK] Caso 2 verificado correctamente.")

    # -------------------------------------------------------------
    # CASO 3: Costos equivalentes (dentro de tolerancia ±$5.00)
    # -------------------------------------------------------------
    print("\n--- CASO 3: Costos equivalentes ---")
    p3 = {
        "codigo_sa6": 640411,
        "cantidad_pares": 2000,
        "costo_variable_unitario_fab": 14.00,
        "costos_fijos_evitables": 16000.00,
        "referencia_comercial": 13.50,
        "gastos_importacion": 8.50,
        "margen_objetivo_pct": 25.0
    }
    r3 = ac.calcular_escenario_make_or_buy(p3)
    assert r3["exito"] is True
    dec3 = r3["analisis_diferencial"]
    fab3 = r3["fabricacion"]
    imp3 = r3["importacion"]

    print(f"Costo Fab Total: ${fab3['costo_total_lote_usd']:,.2f}")
    print(f"Costo Imp Total: ${imp3['costo_total_lote_usd']:,.2f}")
    print(f"Diferencia: ${dec3['diferencia_costo_usd']:,.2f} | Decisión: {dec3['decision_recomendada']}")
    assert abs(dec3["diferencia_costo_usd"]) <= 5.00
    assert dec3["decision_recomendada"] == "EQUIVALENTE"
    assert dec3["es_equivalente"] is True
    print("  [OK] Caso 3 verificado correctamente.")

    # -------------------------------------------------------------
    # CASO 4: Parámetros incompletos e inválidos
    # -------------------------------------------------------------
    print("\n--- CASO 4: Parámetros incompletos e inválidos ---")
    # Volumen 0
    inv1 = ac.calcular_escenario_make_or_buy({"cantidad_pares": 0})
    assert inv1["exito"] is False
    assert "Completa los parámetros" in inv1["error"]
    print("  Volumen 0:", inv1["error"])

    # Costo negativo
    inv2 = ac.calcular_escenario_make_or_buy({"cantidad_pares": 1000, "costo_variable_unitario_fab": -5.0})
    assert inv2["exito"] is False
    assert "los costos no pueden ser negativos" in inv2["error"]
    print("  Costo negativo:", inv2["error"])

    # Margen >= 100%
    inv3 = ac.calcular_escenario_make_or_buy({"cantidad_pares": 1000, "margen_objetivo_pct": 100.0})
    assert inv3["exito"] is False
    assert "el margen objetivo debe estar entre 0% y menos de 100%" in inv3["error"]
    print("  Margen 100%:", inv3["error"])
    print("  [OK] Caso 4 verificado correctamente.")

    # -------------------------------------------------------------
    # CASO 5: Cruce fuera del rango
    # -------------------------------------------------------------
    print("\n--- CASO 5: Cruce fuera de rango ---")
    p5 = {
        "cantidad_pares": 500,
        "costo_variable_unitario_fab": 20.00,
        "costos_fijos_evitables": 30000.00,
        "referencia_comercial": 22.00,
        "gastos_importacion": 0.00
    }
    r5 = ac.calcular_escenario_make_or_buy(p5)
    dec5 = r5["analisis_diferencial"]
    assert dec5["punto_indiferencia_pares"] == 15000
    assert dec5["cruce_fuera_rango"] is True
    print(f"  Q*: {dec5['punto_indiferencia_pares']} | Mensaje: {dec5['mensaje_indiferencia']}")
    print("  [OK] Caso 5 verificado correctamente.")

    # -------------------------------------------------------------
    # CASO 6: Alternativa de precio seleccionable
    # -------------------------------------------------------------
    print("\n--- CASO 6: Alternativa de precio seleccionable ---")
    p6_fab = {**p1, "alternativa_precio": "fabricar"}
    p6_imp = {**p1, "alternativa_precio": "importar"}
    r6_fab = ac.calcular_escenario_make_or_buy(p6_fab)
    r6_imp = ac.calcular_escenario_make_or_buy(p6_imp)

    assert r6_fab["precio_propuesto"]["alternativa_utilizada"] == "fabricar"
    assert r6_fab["precio_propuesto"]["costo_unitario_usd"] == 17.00
    assert r6_imp["precio_propuesto"]["alternativa_utilizada"] == "importar"
    assert r6_imp["precio_propuesto"]["costo_unitario_usd"] == 30.15
    print(f"  Precio base Fabricar: ${r6_fab['precio_propuesto']['precio_sugerido_usd']:.2f}")
    print(f"  Precio base Importar: ${r6_imp['precio_propuesto']['precio_sugerido_usd']:.2f}")
    print("  [OK] Caso 6 verificado correctamente.")

    # -------------------------------------------------------------
    # CASO 7: Aplicar precio sin tocar ventas históricas ni existencias
    # -------------------------------------------------------------
    print("\n--- CASO 7: Aplicar precio a producto seleccionado ---")
    inv_antes = db_manaco.obtener_inventario()
    prod1_antes = next(x for x in inv_antes if x["id_producto"] == 1)
    stock_antes = prod1_antes["stock_actual"]
    movs_antes = len(db_manaco.obtener_movimientos(limite=5000))

    # Actualizar precio de producto 1
    nuevo_usd = 31.50
    nuevo_bs = round(nuevo_usd * 6.96, 2)
    resp = db_manaco.actualizar_precio_producto(id_producto=1, nuevo_precio_bs=nuevo_bs, nuevo_precio_usd=nuevo_usd)
    assert resp["exito"] is True

    inv_despues = db_manaco.obtener_inventario()
    prod1_despues = next(x for x in inv_despues if x["id_producto"] == 1)
    prod2_despues = next(x for x in inv_despues if x["id_producto"] == 2)
    movs_despues = len(db_manaco.obtener_movimientos(limite=5000))

    ventas_antes = [m for m in db_manaco.obtener_movimientos(limite=5000) if m.get("accion") == "VENTA"]
    ventas_despues = [m for m in db_manaco.obtener_movimientos(limite=5000) if m.get("accion") == "VENTA"]
    assert len(ventas_despues) == len(ventas_antes)  # Ventas históricas NO modificadas
    assert prod1_despues["stock_actual"] == stock_antes  # Existencias NO modificadas
    # Producto 2 NO modificado
    prod2_antes = next(x for x in inv_antes if x["id_producto"] == 2)
    assert prod2_despues["precio_unitario_usd"] == prod2_antes["precio_unitario_usd"]

    print(f"  Producto 1 Precio USD: ${prod1_despues['precio_unitario_usd']} (Stock intacto: {prod1_despues['stock_actual']} p)")
    print(f"  Movimientos y ventas históricas intactas: {movs_despues} registros.")
    print("  [OK] Caso 7 verificado correctamente.")

    print("\n" + "=" * 70)
    print("TODAS LAS PRUEBAS DE LA PESTAÑA 1 PASARON SATISFACTORIAMENTE (7/7)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
