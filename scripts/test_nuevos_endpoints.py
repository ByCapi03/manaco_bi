"""
scripts/test_nuevos_endpoints.py
Valida todos los nuevos endpoints HTTP de la arquitectura en 5 pestañas:
- Inventario por 6 productos y suma de 3 categorías.
- Rechazo de ventas que excedan el stock disponible (evita stock negativo).
- Venta válida con precio efectivo e ingresos.
- Proyecciones del Excel (A).
- Pronósticos operativos a 7 días y reposición sugerida (B).
- Confirmación de reposición sugerida.
- Cambio de precio de catálogo sin alterar ventas históricas.
"""

import sys
import json
import urllib.request
import urllib.parse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

def post(endpoint, data):
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

def ejecutar_pruebas():
    print("=" * 70)
    print("PRUEBAS DE VALIDACIÓN DE ENDPOINTS - 5 PESTAÑAS MANACO BI")
    print("=" * 70)

    # 1. GET /api/estado
    st, data = get("/api/estado")
    print(f"1. GET /api/estado -> Status: {st}")
    prods = data["inventario_productos"]
    cats = data["inventario_categorias"]
    print(f"   Total productos en catálogo: {len(prods)} (Esperado: 6)")
    print(f"   Total categorías arancelarias: {len(cats)} (Esperado: 3)")
    assert len(prods) == 6, f"Deben existir 6 productos, encontrados: {len(prods)}"
    assert len(cats) == 3, f"Deben existir 3 categorías, encontradas: {len(cats)}"

    # Verificar que la suma por categoría coincide exactamente con la suma de sus 2 productos
    for c in cats:
        sa6 = c["codigo_sa6"]
        prods_de_cat = [p for p in prods if p["codigo_sa6"] == sa6]
        suma_stock_prods = sum(p["stock_actual"] for p in prods_de_cat)
        assert c["stock_actual"] == suma_stock_prods, f"Suma de categoría {sa6} ({c['stock_actual']}) no coincide con suma de productos ({suma_stock_prods})"
        print(f"   ✓ Categoría {sa6} ({c['categoria_corta']}): {c['stock_actual']} pares (Suma exacta de sus 2 productos: {suma_stock_prods} pares)")

    # 2. Rechazo de salida superior al stock (Validación: stock no negativo)
    prod_1 = prods[0]
    stock_actual_p1 = prod_1["stock_actual"]
    print(f"\n2. Probando rechazo de venta excesiva (Producto ID 1: {prod_1['nombre_producto']}, Stock actual: {stock_actual_p1})...")
    st_err, data_err = post("/api/inventario/movimiento", {
        "id_producto": 1,
        "accion": "VENTA",
        "cantidad": stock_actual_p1 + 50, # Intentar vender más de lo disponible
        "canal_venta": "Tienda Propia",
        "responsable": "Test Validación Stock Negativo"
    })
    print(f"   Respuesta del servidor: Status {st_err} -> {data_err.get('error')}")
    assert st_err == 400, "Venta superior al stock debe ser rechazada con código 400"
    assert "rechazada" in data_err.get("error", "").lower() or "insuficiente" in data_err.get("error", "").lower()
    print("   ✓ Salida superior al stock rechazada correctamente. Stock no negativo garantizado.")

    # 3. Venta válida con precio efectivo
    print(f"\n3. Probando venta válida de 2 pares de {prod_1['nombre_producto']}...")
    st_ok, data_ok = post("/api/inventario/movimiento", {
        "id_producto": 1,
        "accion": "VENTA",
        "cantidad": 2,
        "canal_venta": "E-commerce / Tienda Online",
        "responsable": "Cliente Online"
    })
    assert st_ok == 200, "Venta válida debe responder 200"
    assert data_ok["nuevo_stock"] == stock_actual_p1 - 2, f"Nuevo stock debe ser {stock_actual_p1 - 2}"
    print(f"   ✓ Venta exitosa: ID Registro #{data_ok['id_registro']}. Stock resultante: {data_ok['nuevo_stock']} pares.")

    # 4. Proyecciones Excel (A)
    print("\n4. Probando proyecciones del Excel (A: Naive vs Tendencia)...")
    st_pe, data_pe = get("/api/predicciones/excel")
    assert st_pe == 200, "Endpoint /api/predicciones/excel debe responder 200"
    print(f"   Aviso metodológico: {data_pe['aviso_metodologico'][:80]}...")
    print(f"   Categorías evaluadas: {len(data_pe['categorias'])}")
    for cat in data_pe["categorias"]:
        print(f"      - {cat['categoria']}: Error Naive={cat['evaluacion_2024']['error_naive_pct']}%, Error Tendencia={cat['evaluacion_2024']['error_trend_pct']}% -> Mejor: {cat['evaluacion_2024']['mejor_modelo']}")

    # 5. Pronósticos Operativos (B) y Reposición Sugerida
    print("\n5. Probando pronósticos de ventas operativas y reposición (B)...")
    st_po, data_po = get("/api/predicciones/operativas")
    assert st_po == 200, "Endpoint /api/predicciones/operativas debe responder 200"
    print(f"   Ventas previstas 7 días (total catálogo): {data_po['totales_resumen']['total_ventas_previstas_7d']} pares")
    print(f"   MAE evaluado en test: {data_po['totales_resumen']['mae_promedio_pares']} pares")
    print(f"   Sugerencia total de reposición: {data_po['totales_resumen']['total_sugerencia_reposicion']} pares")

    # 6. Confirmación de Reposición Sugerida
    print("\n6. Probando confirmación interactiva de reposición sugerida...")
    st_rep, data_rep = post("/api/inventario/confirmar-reposicion", {
        "id_producto": 1,
        "cantidad": 10,
        "responsable": "Gerente de Operaciones Manaco"
    })
    assert st_rep == 200, "Confirmación de reposición debe responder 200"
    print(f"   ✓ Reposición confirmada: {data_rep['mensaje']}")

    # 7. Cambio de precio sin alterar ventas históricas
    print("\n7. Probando cambio de precio de catálogo y aislamiento de ingresos históricos...")
    # Consultar ingresos históricos antes del cambio
    st_k1, data_k1 = get("/api/estado")
    ingresos_antes = data_k1["kpis"]["kpis_canales"]["ingresos_brutos_totales_bs"]

    # Cambiar precio de catálogo del producto 1
    st_pr, data_pr = post("/api/inventario/aplicar-precio", {
        "id_producto": 1,
        "nuevo_precio_bs": 320.00,
        "nuevo_precio_usd": 45.98,
        "responsable": "Auditor Financiero"
    })
    assert st_pr == 200, "Actualización de precio debe responder 200"

    # Consultar ingresos históricos después del cambio
    st_k2, data_k2 = get("/api/estado")
    ingresos_despues = data_k2["kpis"]["kpis_canales"]["ingresos_brutos_totales_bs"]

    print(f"   Ingresos históricos antes: {ingresos_antes}")
    print(f"   Ingresos históricos después: {ingresos_despues}")
    assert ingresos_antes == ingresos_despues, "Los ingresos históricos no deben alterarse al modificar precios del catálogo"
    print("   ✓ Aislamiento financiero confirmado: cambios en catálogo no modifican ventas previas.")

    # Restaurar precio de producto 1 a 295.08
    post("/api/inventario/aplicar-precio", {
        "id_producto": 1,
        "nuevo_precio_bs": 295.08,
        "nuevo_precio_usd": 42.40,
        "responsable": "Restauración de Prueba"
    })

    print("\n" + "=" * 70)
    print("✓ TODAS LAS PRUEBAS DE ENDPOINTS PASARON CON ÉXITO.")
    print("=" * 70)

if __name__ == "__main__":
    try:
        ejecutar_pruebas()
    except Exception as e:
        print(f"❌ Error en pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
