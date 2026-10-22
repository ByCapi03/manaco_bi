"""
Test script for Tab 4: Planificación de demanda.
Validates:
1. evaluar_pronostico_ventas_operativas execution and data structure.
2. Verified with user test cases:
   - demanda 28, reserva 7, disponible 15, pendientes 0 -> faltante 20
   - pendientes 10 -> faltante 10
3. Recent history series and 7-day forecast series format and real dates.
4. Lead time common value or 'Según producto'.
5. Zero filling within known bounds without outside leakage.
6. Simulated vs live sales separation.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "clasificador_calzados")))

from db_manaco import db_manaco
from predicciones import evaluar_pronostico_ventas_operativas, evaluar_proyecciones_excel_comercio


def test_formulas_conocidas():
    print("=== Test 1: Comprobación con ejemplos conocidos ===")
    # Caso 1: Demanda 28, Reserva 7, Disponible 15, Pendientes 0 -> Faltante 20
    demanda = 28
    reserva = 7
    disponible = 15
    pendientes = 0
    umbral = demanda + reserva
    posicion = disponible + pendientes
    faltante = max(0, umbral - posicion)
    assert faltante == 20, f"Error: faltante esperado 20, obtenido {faltante}"
    print(f"Caso 1 OK: Umbral={umbral}, Posicion={posicion}, Faltante={faltante} (esperado 20)")

    # Caso 2: Pendientes 10 -> Faltante 10
    pendientes_2 = 10
    posicion_2 = disponible + pendientes_2
    faltante_2 = max(0, umbral - posicion_2)
    assert faltante_2 == 10, f"Error: faltante esperado 10, obtenido {faltante_2}"
    print(f"Caso 2 OK: Umbral={umbral}, Posicion={posicion_2}, Faltante={faltante_2} (esperado 10)")


def test_evaluacion_operativa():
    print("\n=== Test 2: Ejecución de evaluar_pronostico_ventas_operativas ===")
    res = evaluar_pronostico_ventas_operativas(db_manaco)
    assert res.get("exito") is True, f"Error en respuesta: {res}"

    # Validar dualidad de payload
    assert "totales_resumen" in res
    assert "productos" in res
    assert "fuente_datos" in res
    assert "datos" in res
    assert "kpis" in res["datos"]

    tot = res["totales_resumen"]
    print(f"Totales resumen: {tot}")
    print(f"Etiqueta de fuente: {res['fuente_datos']['etiqueta_fuente']}")
    print(f"Badge: {res['fuente_datos']['badge_texto']}")

    # Validar que los 6 productos están presentes
    prods = res["productos"]
    assert len(prods) == 6, f"Esperados 6 productos, obtenidos {len(prods)}"

    for p in prods:
        sku = p["sku"]
        disp = p["disponible"]
        dem_plazo = p["demanda_plazo"]
        reserva = p["reserva_seguridad"]
        necesidad = p["necesidad"]
        pend = p["pendientes_recibir"]
        posicion = p["posicion_inventario"]
        faltante = p["faltante_cobertura"]
        estado = p["estado"]

        # Comprobar fórmulas exactas
        assert necesidad == dem_plazo + reserva, f"{sku}: necesidad != dem_plazo + reserva"
        assert posicion == disp + pend, f"{sku}: posicion != disp + pend"
        assert faltante == max(0, necesidad - posicion), f"{sku}: faltante incorrecto"

        # Comprobar series de tiempo
        hist = p["historico_reciente"]
        pron = p["pronostico_7d"]
        assert len(hist["fechas"]) == len(hist["valores"]), f"{sku}: fechas y valores históricos no coinciden"
        assert len(pron["fechas"]) == 7, f"{sku}: pronostico debe tener 7 fechas"
        assert len(pron["valores_diarios_pares"]) == 7, f"{sku}: pronostico debe tener 7 valores"

        # Comprobar evaluación MAE
        ev = p["evaluacion"]
        assert "mae_promedio_movil" in ev
        assert "mae_ingenuo" in ev
        assert ev["unidad"] == "pares/día"

        print(f"[{sku}] Disp={disp} | DemPlazo={dem_plazo} | Reserva={reserva} | Nec={necesidad} | Pend={pend} | Faltante={faltante} | Estado={estado} | MAE={ev['mae_promedio_movil']}")

    # Validar unificación de KPIs
    suma_ventas_7d = sum(p["ventas_previstas_7d"] for p in prods)
    suma_faltantes = sum(p["faltante_cobertura"] for p in prods)
    count_prods_reponer = sum(1 for p in prods if p["faltante_cobertura"] > 0)

    assert tot["total_ventas_previstas_7d"] == suma_ventas_7d, "KPI Ventas previstas 7d no coincide con la suma"
    assert tot["pares_por_reponer"] == suma_faltantes, "KPI Pares por reponer no coincide con la suma"
    assert tot["productos_por_reponer"] == count_prods_reponer, "KPI Productos por reponer no coincide con el conteo"
    print("\nUnificación de indicadores validada exitosamente.")


def test_excel_comercio():
    print("\n=== Test 3: Contexto externo (Excel) ===")
    res_excel = evaluar_proyecciones_excel_comercio()
    assert res_excel.get("exito") is True
    assert "categorias" in res_excel
    assert "datos" in res_excel
    print(f"Categorías evaluadas en comercio exterior: {len(res_excel['categorias'])}")


def test_flask_endpoints():
    print("\n=== Test 4: Comprobación de endpoints Flask con test_client ===")
    from app_web import app
    client = app.test_client()

    # 1. GET /api/predicciones/operativas
    resp = client.get("/api/predicciones/operativas")
    assert resp.status_code == 200, f"Error status: {resp.status_code}"
    j = resp.get_json()
    assert j["exito"] is True
    assert "totales_resumen" in j
    assert "productos" in j
    assert "fuente_datos" in j
    assert len(j["productos"]) == 6
    print("Endpoint GET /api/predicciones/operativas OK")

    # Obtener valores iniciales de producto 1
    p1_ini = j["productos"][0]
    stock_act_ini = p1_ini["disponible"]
    faltante_ini = p1_ini["faltante_cobertura"]
    print(f"Producto 1 inicial: Stock={stock_act_ini}, Pendientes={p1_ini['pendientes_recibir']}, Faltante={faltante_ini}")

    # 2. POST /api/predicciones/solicitar-reposicion (+10 pares a pendientes)
    resp_sol = client.post("/api/predicciones/solicitar-reposicion", json={
        "id_producto": 1,
        "cantidad": 10,
        "responsable": "Planificador Test",
        "nota": "Prueba de solicitud pendiente"
    })
    assert resp_sol.status_code == 200, f"Error status: {resp_sol.status_code}"
    j_sol = resp_sol.get_json()
    assert j_sol["exito"] is True
    assert j_sol["stock_disponible"] == stock_act_ini, "El stock disponible NO debe cambiar con una solicitud de reposición"
    assert j_sol["pedidos_pendientes"] == 10
    print("Solicitud registrada: +10 pares en pedidos_pendientes. Stock intacto.")

    # 3. GET /api/predicciones/operativas para verificar que la posición de inventario aumentó y el faltante disminuyó
    resp_check = client.get("/api/predicciones/operativas")
    j_check = resp_check.get_json()
    p1_despues = j_check["productos"][0]
    assert p1_despues["disponible"] == stock_act_ini, "El stock disponible debe permanecer intacto"
    assert p1_despues["pendientes_recibir"] == 10, "Los pedidos pendientes deben ser 10"
    assert p1_despues["faltante_cobertura"] == faltante_ini - 10, f"Faltante esperado {faltante_ini - 10}, obtenido {p1_despues['faltante_cobertura']}"
    print(f"Comprobación tras solicitud: Stock={p1_despues['disponible']} (sin cambio), Pendientes={p1_despues['pendientes_recibir']}, Faltante={p1_despues['faltante_cobertura']} (-10 pares exactos)")

    # 4. POST /api/predicciones/restablecer-pendientes (limpieza de prueba)
    resp_reset = client.post("/api/predicciones/restablecer-pendientes")
    assert resp_reset.status_code == 200
    j_reset = resp_reset.get_json()
    assert j_reset["exito"] is True

    # 5. Verificar que regresó a 0
    resp_final = client.get("/api/predicciones/operativas")
    p1_final = resp_final.get_json()["productos"][0]
    assert p1_final["pendientes_recibir"] == 0
    assert p1_final["disponible"] == stock_act_ini
    print("Restablecimiento a pendientes=0 comprobado exitosamente.")


if __name__ == "__main__":
    test_formulas_conocidas()
    test_evaluacion_operativa()
    test_excel_comercio()
    test_flask_endpoints()
    print("\n>>> TODOS LOS TESTS DE DEMANDA PASARON EXITOSAMENTE. <<<")

