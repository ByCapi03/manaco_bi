"""
scripts/test_http_endpoints.py
Verifica que el servidor web Flask en localhost:5000 responde correctamente
en todos sus endpoints con la nueva arquitectura desacoplada de Excel.
"""

import sys
import json
import urllib.request
import urllib.parse
import numpy as np
import cv2
import base64

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

def post(endpoint, data):
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

def test_endpoints():
    print("=" * 70)
    print("PROBANDO ENDPOINTS HTTP FLASK EN TIEMPO REAL")
    print("=" * 70)

    # 1. API Estado
    st, data = get("/api/estado")
    print(f"1. GET /api/estado -> Status: {st}")
    print(f"   Motor DB: {data.get('motor_db')}")
    print(f"   Total pares: {data['kpis']['total_pares']} pares")
    print(f"   Confianza prom IA: {data['kpis']['confianza_promedio_ia']}")
    assert data["exito"] is True

    # 2. API Gráficos
    st, data = get("/api/graficos")
    print(f"\n2. GET /api/graficos -> Status: {st}")
    print(f"   Categorías inventario: {data['datos']['categorias']}")
    print(f"   Comercio exterior Excel disponible: {data['datos']['dw_comercio']['disponible']}")
    print(f"   Años comercio Excel: {data['datos']['dw_comercio']['anios']}")
    assert data["datos"]["dw_comercio"]["disponible"] is True

    # 3. API Opciones Comercio
    st, data = get("/api/comercio/opciones")
    print(f"\n3. GET /api/comercio/opciones -> Status: {st}")
    print(f"   Flujos: {data['flujos']}")
    print(f"   Años: {data['anios']}")
    print(f"   Total socios comerciales en Excel: {len(data['socios'])}")
    assert len(data['socios']) == 30

    # 4. API Métricas Comercio (Filtro 2024 Importación Deportivo 640411)
    st, data = get("/api/comercio/metricas?flujo=Importaci%C3%B3n&anio=2024&codigo_sa6=640411")
    print(f"\n4. GET /api/comercio/metricas (Deportivo 2024) -> Status: {st}")
    print(f"   Valor USD: ${data['resumen']['suma_valor_usd']:,.2f}")
    print(f"   Pares: {data['resumen']['suma_cantidad_pares']:,}")
    print(f"   Cociente ponderado: ${data['resumen']['referencia_usd_por_par']:.2f} USD/par")
    assert abs(data['resumen']['referencia_usd_por_par'] - 27.80) <= 0.01

    # 5. API Escenarios Predefinidos
    for preset in ["importar_mas_conveniente", "fabricar_mas_conveniente", "condiciones_equivalentes"]:
        st, data = get(f"/api/escenarios/predefinido/{preset}")
        p = data["parametros"]
        print(f"\n5. GET /api/escenarios/predefinido/{preset} -> Status: {st}")
        print(f"   Categoría: {p['codigo_sa6']} | Pares: {p['cantidad_pares']} | Venta: ${p['precio_venta']}")

    # 6. API Calcular Escenario
    st, data = post("/api/escenarios/calcular", {
        "codigo_sa6": 640411,
        "cantidad_pares": 5000,
        "precio_venta": 28.0,
        "margen_objetivo_pct": 35.0,
        "costo_variable_unitario_fab": 16.5,
        "costos_fijos_evitables": 15000.0,
        "costos_fijos_permanentes": 12000.0,
        "cotizacion_compra": 12.0,
        "flete_transporte": 2.0,
        "seguro_transporte": 0.3,
        "gastos_internacion": 2.5,
        "entrega_local": 0.8,
        "otros_gastos": 0.4,
        "moneda": "USD",
        "tasa_cambio": 6.96
    })
    print(f"\n6. POST /api/escenarios/calcular -> Status: {st}")
    print(f"   Decisión recomendada: {data['analisis_diferencial']['decision_recomendada']}")
    print(f"   Mensaje: {data['analisis_diferencial']['mensaje']}")
    print(f"   Precio propuesto fabricar: ${data['fabricacion']['precio_propuesto_usd']} USD")
    print(f"   Precio propuesto importar: ${data['importacion']['precio_propuesto_usd']} USD")
    print(f"   Precio activo en tienda: Bs. {data['precio_activo_inventario']['precio_unitario_bs']}")
    assert data["exito"] is True

    # 7. Simulación NO mueve existencias
    st_antes, data_antes = get("/api/estado")
    pares_antes = data_antes["kpis"]["total_pares"]
    assert pares_antes == 90, f"Existencias deben mantenerse intactas: {pares_antes}"
    print(f"\n7. Verificación: La simulación del escenario NO alteró las existencias en almacén ({pares_antes} pares intactos).")

    # 8. API Clasificar Imagen Sintética (Verificar cámara / visión)
    img_vacia = np.zeros((200, 200, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img_vacia)
    b64_img = base64.b64encode(buffer).decode('utf-8')
    st, data = post("/api/clasificar", {"imagen": f"data:image/jpeg;base64,{b64_img}"})
    print(f"\n8. POST /api/clasificar (Frame de prueba) -> Status: {st}")
    print(f"   Clase detectada: {data.get('clase')} ({data.get('nombre')})")
    print(f"   Es calzado: {data.get('es_calzado')} | Confianza: {data.get('confianza')}")
    assert data["exito"] is True

    print("\n" + "=" * 70)
    print("✓ TODOS LOS ENDPOINTS HTTP RESPONDIERON CON ÉXITO.")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_endpoints()
    except Exception as e:
        print(f"Error en prueba HTTP: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
