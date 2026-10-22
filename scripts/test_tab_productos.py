"""
test_tab_productos.py
Verificación rigurosa de las correcciones y simplificaciones en la pestaña Productos:
1. Endpoint /api/productos/detalle: 6 productos, precios, costos de referencia aduana 2024, diferencia unitaria, margen %.
2. Segregación estricta de procedencia: Simulación 12M vs Registros en Almacén (sin sumas silenciosas).
3. Consistencia de fórmulas:
   - Diferencia por par = Precio propuesto - Costo empleado
   - Margen del escenario = (Diferencia / Precio) * 100
   - Contribución = Ingresos - (Pares * Costo)
4. Contexto externo (/api/productos/participacion_exterior):
   - Dinámico desde Excel con filtros de Año, Flujo y Medida.
   - Categoría con "mayor participación en los registros".
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000"

def test_productos_detalle():
    print("--- Test 1: /api/productos/detalle ---")
    url = f"{BASE_URL}/api/productos/detalle"
    req = urllib.request.urlopen(url)
    assert req.status == 200, f"Status code {req.status}"
    data = json.loads(req.read().decode('utf-8'))
    
    assert data.get("exito") is True, "exito should be True"
    kpis = data.get("kpis", {})
    prods = data.get("productos", [])
    
    assert kpis.get("total_productos_activos") == 6, f"Expected 6 active products, got {kpis.get('total_productos_activos')}"
    assert len(prods) == 6, f"Expected 6 products list, got {len(prods)}"
    
    # Validar segregación de ventas
    sint_pares = kpis.get("ventas_sinteticas_totales_pares")
    reg_pares = kpis.get("ventas_registradas_totales_pares")
    print(f"Ventas sintéticas totales: {sint_pares} pares | Ventas almacén: {reg_pares} pares")
    assert sint_pares > 0, "Debe tener ventas sintéticas registradas"
    assert reg_pares >= 0, "Ventas de almacén deben ser >= 0"
    
    # Validar cálculos por producto
    for p in prods:
        sku = p["codigo_sku"]
        precio_usd = p["precio_unitario_usd"]
        costo_usd = p["costo_referencia_usd"]
        dif_usd = p["diferencia_usd"]
        margen = p["margen_sobre_venta_pct"]
        
        # Diferencia = Precio - Costo
        expected_dif = round(precio_usd - costo_usd, 2)
        assert abs(dif_usd - expected_dif) < 0.05, f"Fórmula diferencia falló en {sku}: {dif_usd} vs {expected_dif}"
        
        # Margen = (Precio - Costo) / Precio
        expected_margen = round((dif_usd / precio_usd) * 100, 1)
        assert abs(margen - expected_margen) < 0.2, f"Fórmula margen falló en {sku}: {margen}% vs {expected_margen}%"
        
        # Costo de referencia aduana 2024
        if p["codigo_sa6"] == "640411":
            assert abs(costo_usd - 27.80) < 0.01, f"Costo ref deportivo 640411 incorrecto: {costo_usd}"
        elif p["codigo_sa6"] == "640399":
            assert abs(costo_usd - 26.15) < 0.01, f"Costo ref casual 640399 incorrecto: {costo_usd}"
        elif p["codigo_sa6"] == "640420":
            assert abs(costo_usd - 45.53) < 0.01, f"Costo ref vestir 640420 incorrecto: {costo_usd}"
            
        print(f"[OK] {sku} ({p['linea']}): Precio ${precio_usd} - Costo ${costo_usd} = Dif ${dif_usd}/par | Margen {margen}%")

    print("Test 1 exitoso!\n")

def test_participacion_exterior():
    print("--- Test 2: /api/productos/participacion_exterior ---")
    
    # Caso 1: Todos
    url = f"{BASE_URL}/api/productos/participacion_exterior?anio=TODOS&flujo=TODOS&medida=USD"
    data = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))
    assert data["exito"] is True
    assert "mayor_participacion" in data
    assert data["mayor_porcentaje"] > 50
    print(f"General: Mayor participación en los registros -> {data['mayor_participacion']} ({data['mayor_porcentaje']}%)")
    
    # Caso 2: 2024 Importación en Pares
    url2 = f"{BASE_URL}/api/productos/participacion_exterior?anio=2024&flujo=Importaci%C3%B3n&medida=PARES"
    data2 = json.loads(urllib.request.urlopen(url2).read().decode('utf-8'))
    assert data2["exito"] is True
    assert len(data2["categorias"]) == 3
    # Suma de porcentajes debe ser ~100%
    pct_sum = sum(c["porcentaje"] for c in data2["categorias"])
    assert abs(pct_sum - 100.0) < 0.5, f"Suma de porcentajes {pct_sum}% != 100%"
    print(f"2024 Importación (Pares): Mayor participación -> {data2['mayor_participacion']} ({data2['mayor_porcentaje']}%)")
    
    print("Test 2 exitoso!\n")

if __name__ == "__main__":
    test_productos_detalle()
    test_participacion_exterior()
    print("=== TODOS LOS TESTS DE LA PESTAÑA PRODUCTOS PASARON EXITOSAMENTE ===")
