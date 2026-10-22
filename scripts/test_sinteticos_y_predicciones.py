"""
scripts/test_sinteticos_y_predicciones.py
Prueba y valida la generación de datos sintéticos idempotentes y los módulos
predictivos (Excel Naive vs Tendencia, y Ventas Operativas Naive vs MA7).
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "clasificador_calzados"))

try:
    from clasificador_calzados.db_manaco import db_manaco
    from clasificador_calzados.datos_sinteticos import generar_historial_sintetico_12m
    from clasificador_calzados.predicciones import evaluar_proyecciones_excel_comercio, evaluar_pronostico_ventas_operativas
except ImportError:
    from db_manaco import db_manaco  # type: ignore
    from datos_sinteticos import generar_historial_sintetico_12m  # type: ignore
    from predicciones import evaluar_proyecciones_excel_comercio, evaluar_pronostico_ventas_operativas  # type: ignore

def probar():
    print("=" * 70)
    print("PROBANDO GENERACIÓN SINTÉTICA (12 MESES)")
    print("=" * 70)

    # 1. Generación sintética inicial
    res_sim = generar_historial_sintetico_12m(db_manaco, forzar_regeneracion=False)
    print(f"Resultado simulación: {res_sim['mensaje']}")
    print(f"Pares vendidos: {res_sim.get('total_pares_vendidos', 'N/D')}")
    print(f"Ingresos totales Bs: {res_sim.get('total_ingresos_bs', 'N/D')}")

    # 2. Prueba de idempotencia (segunda llamada no debe duplicar)
    print("\nProbando idempotencia...")
    res_idem = generar_historial_sintetico_12m(db_manaco, forzar_regeneracion=False)
    print(f"Resultado idempotente: {res_idem['mensaje']}")
    assert res_idem.get("idempotente") is True, "La generación repetida debe ser idempotente"

    # 3. Comprobar que ningún stock en inventario_calzado sea negativo
    inv = db_manaco.obtener_inventario()
    print("\nEstado de existencias en bodega:")
    for p in inv:
        print(f"   [{p['id_producto']}] {p['codigo_sku']} - {p['nombre_producto']}: {p['stock_actual']} pares (Min: {p['stock_minimo']})")
        assert p["stock_actual"] >= 0, f"Stock no puede ser negativo: {p['stock_actual']}"

    # 4. Prueba de Proyecciones Excel
    print("\n" + "=" * 70)
    print("PROBANDO PREDICCIONES A (EXCEL: NAIVE VS TENDENCIA)")
    print("=" * 70)
    res_excel = evaluar_proyecciones_excel_comercio()
    print(f"Años con cobertura analizada: {len(res_excel['cobertura_por_anio'])}")
    for cat in res_excel["categorias"]:
        ev = cat["evaluacion_2024"]
        print(f"\nCategoría: {cat['categoria']}")
        print(f"   Real 2024: {ev['real_2024_pares']:,} pares")
        print(f"   Predicción Naive: {ev['pred_naive_pares']:,} pares | Error: {ev['error_naive_pct']}%")
        print(f"   Predicción Tendencia: {ev['pred_trend_pares']:,} pares | Error: {ev['error_trend_pct']}%")
        print(f"   Mejor modelo para 2024: {ev['mejor_modelo']}")
        print(f"   Proyección 2025 (Tendencia): {cat['proyeccion_2025_exploratoria']['trend_2025_pares']:,} pares")

    # 5. Prueba de Pronóstico de Ventas Operativas
    print("\n" + "=" * 70)
    print("PROBANDO PREDICCIONES B (VENTAS OPERATIVAS: NAIVE VS MA7)")
    print("=" * 70)
    res_oper = evaluar_pronostico_ventas_operativas(db_manaco)
    assert res_oper["exito"] is True, "Evaluación operativa debe ser exitosa con datos de 12M"
    print(f"Total ventas previstas 7 días (todos los productos): {res_oper['totales_resumen']['total_ventas_previstas_7d']} pares")
    print(f"MAE promedio evaluado en test: {res_oper['totales_resumen']['mae_promedio_pares']} pares")
    print(f"Sugerencia total de reposición: {res_oper['totales_resumen']['total_sugerencia_reposicion']} pares")

    for p in res_oper["productos"][:3]:
        print(f"\nProducto: {p['nombre_producto']} ({p['sku']}):")
        print(f"   Período evaluado test: {p['evaluacion']['periodo_evaluado_dias']} días")
        print(f"   MAE Promedio Móvil: {p['evaluacion']['mae_promedio_movil']} pares | MAE Ingenuo: {p['evaluacion']['mae_ingenuo']} pares")
        print(f"   Mejor modelo: {p['evaluacion']['mejor_modelo']}")
        print(f"   Pronóstico 7 días: {p['pronostico_proximos_7d']['total_semana_pares']} pares")
        print(f"   Sugerencia de reposición calculada: {p['planificacion_inventario']['sugerencia_reposicion_pares']} pares")

    print("\n" + "=" * 70)
    print("✓ TODAS LAS PRUEBAS DE SINTÉTICOS Y PREDICCIONES PASARON.")
    print("=" * 70)

if __name__ == "__main__":
    probar()
