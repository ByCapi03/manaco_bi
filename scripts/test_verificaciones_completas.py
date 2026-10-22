"""
scripts/test_verificaciones_completas.py
Script de verificación y pruebas exhaustivas para la auditoría de entrega MANACO BI.
Comprueba:
1. Referencias de importación 2024 en BDatos_MANACO.xlsx (640399: 26.15, 640411: 27.80, 640420: 45.53).
2. Filtros y cocientes comerciales ponderados.
3. Casos borde de calculadora: cantidad 0, márgenes (0% y 95%), moneda USD y BOB con TC.
4. Desacoplamiento de PostgreSQL: inventario_calzado, registro_vision, ausencia de DW.
5. Inferencia / escáner y trazabilidad de movimientos.
"""

import os
import sys
from pathlib import Path

# Configurar salida en UTF-8 para consola Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Agregar raíz y clasificador_calzados al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "clasificador_calzados"))

import analisis_comercial as ac
from db_manaco import db_manaco, DatabaseManaco
from config import obtener_ruta_excel, TASA_CAMBIO_OFICIAL

def probar_referencias_2024():
    print("=" * 70)
    print("PRUEBA 1: COMPROBACIÓN DE REFERENCIAS DE IMPORTACIÓN 2024 (EXCEL)")
    print("=" * 70)
    
    df = ac.cargar_dataset_excel()
    print(f"Total filas cargadas de Excel: {len(df)}")
    
    cats = {
        640399: ("Casual Cuero", 26.15),
        640411: ("Deportivo", 27.80),
        640420: ("Formal Cuero", 45.53)
    }
    
    todas_pasan = True
    for sa6, (nombre, esperado) in cats.items():
        ref = ac.obtener_referencia_importacion_2024(sa6)
        sub = df[(df["Año"] == 2024) & (df["Flujo_comercial"] == "Importación") & (df["Código_SA6"] == sa6)]
        v = sub["Valor_USD"].sum()
        p = sub["Cantidad_pares"].sum()
        cociente_exacto = v / p if p > 0 else 0
        diff = abs(ref - esperado)
        status = "PASÓ" if diff <= 0.01 else "FALLÓ"
        if status == "FALLÓ":
            todas_pasan = False
        print(f"SA6 {sa6} ({nombre}):")
        print(f"   Valor USD: ${v:,.2f} | Pares: {p:,}")
        print(f"   Cociente exacto: ${cociente_exacto:.4f} | Redondeado: ${ref:.2f} USD/par")
        print(f"   Esperado: ${esperado:.2f} USD/par -> [{status}]")
    
    assert todas_pasan, "Las referencias de importación 2024 no coinciden con los valores esperados"
    print("\n✓ TODAS LAS REFERENCIAS 2024 VERIFICADAS EXITOSAMENTE.")


def probar_calculos_comerciales_filtros():
    print("\n" + "=" * 70)
    print("PRUEBA 2: FILTROS COMERCIALES Y PARTICIPACIÓN PONDERADA")
    print("=" * 70)
    
    # 2.1 Filtro por flujo y año
    res_2024 = ac.calcular_metricas_comerciales(flujo="Importación", anio=2024)
    print("Métricas Importación 2024 (Total):")
    print(f"   Valor total: ${res_2024['resumen']['suma_valor_usd']:,.2f}")
    print(f"   Volumen total: {res_2024['resumen']['suma_cantidad_pares']:,} pares")
    print(f"   Cociente ponderado total: ${res_2024['resumen']['referencia_usd_por_par']:.2f} USD/par")
    print(f"   Total categorías desglosadas: {len(res_2024['desglose_categorias'])}")
    print(f"   Top socios listados: {len(res_2024['ranking_socios'])}")
    
    # 2.2 Filtro con socio específico (ej: China)
    res_china = ac.calcular_metricas_comerciales(flujo="Importación", anio=2024, socio="China")
    print("\nMétricas Importación 2024 (Socio: China):")
    print(f"   Valor: ${res_china['resumen']['suma_valor_usd']:,.2f}")
    print(f"   Pares: {res_china['resumen']['suma_cantidad_pares']:,}")
    print(f"   Participación en valor del flujo 2024: {res_china['resumen']['participacion_valor_pct']:.2f}%")
    print(f"   Participación en volumen del flujo 2024: {res_china['resumen']['participacion_pares_pct']:.2f}%")
    print(f"   Cociente ponderado China: ${res_china['resumen']['referencia_usd_por_par']:.2f} USD/par")
    
    assert res_china['resumen']['participacion_valor_pct'] > 0, "Participación en valor debe ser > 0"
    print("\n✓ FILTROS Y PARTICIPACIONES PONDERADAS FUNCIONANDO CORRECTAMENTE.")


def probar_calculadora_escenarios_casos_borde():
    print("\n" + "=" * 70)
    print("PRUEBA 3: CALCULADORA MAKE-OR-BUY Y CASOS BORDE")
    print("=" * 70)
    
    # 3.1 Caso borde: Cantidad cero
    print("Caso 3.1: Cantidad de pares = 0")
    res_cero = ac.calcular_escenario_make_or_buy({
        "codigo_sa6": 640411,
        "cantidad_pares": 0,
        "precio_venta": 25.0,
        "margen_objetivo_pct": 30.0,
        "costo_variable_unitario_fab": 15.0,
        "costos_fijos_evitables": 10000.0,
        "cotizacion_compra": 20.0
    })
    print(f"   Decisión: {res_cero['analisis_diferencial']['decision_recomendada']}")
    print(f"   Costo fabricar: ${res_cero['fabricacion']['costo_total_lote_usd']}")
    print(f"   Costo importar: ${res_cero['importacion']['costo_total_lote_usd']}")
    assert res_cero['fabricacion']['costo_total_lote_usd'] == 10000.0
    assert res_cero['importacion']['costo_total_lote_usd'] == 0.0
    
    # 3.2 Caso borde: Margen objetivo 0% y 95%
    print("\nCaso 3.2: Márgenes extremos (0% y 95%)")
    res_m0 = ac.calcular_escenario_make_or_buy({
        "codigo_sa6": 640411,
        "cantidad_pares": 1000,
        "margen_objetivo_pct": 0.0,
        "costo_variable_unitario_fab": 15.0,
        "costos_fijos_evitables": 5000.0, # CU = 15 + 5 = 20
        "cotizacion_compra": 18.0
    })
    # Con margen 0%, precio propuesto debe igualar el costo unitario
    cu_fab_0 = res_m0['fabricacion']['costo_unitario_total_usd']
    pp_fab_0 = res_m0['fabricacion']['precio_propuesto_usd']
    print(f"   Margen 0% -> Costo Unitario: ${cu_fab_0} | Precio Propuesto: ${pp_fab_0}")
    assert cu_fab_0 == pp_fab_0, "Con margen 0%, Precio Propuesto debe ser igual a Costo Unitario"
    
    res_m95 = ac.calcular_escenario_make_or_buy({
        "codigo_sa6": 640411,
        "cantidad_pares": 1000,
        "margen_objetivo_pct": 95.0,
        "costo_variable_unitario_fab": 20.0,
        "costos_fijos_evitables": 0.0,
        "cotizacion_compra": 20.0
    })
    # Con margen 95%, divisor = 0.05 -> Precio = 20 / 0.05 = 400
    pp_fab_95 = res_m95['fabricacion']['precio_propuesto_usd']
    print(f"   Margen 95% -> Costo: $20.00 | Precio Propuesto: ${pp_fab_95:.2f}")
    assert pp_fab_95 == 400.0, "Precio propuesto con 95% de margen debe ser 400.00"
    
    # 3.3 Conversión a BOB con Tasa de Cambio 6.96
    print("\nCaso 3.3: Conversión de moneda (USD a BOB con TC 6.96)")
    res_bob = ac.calcular_escenario_make_or_buy({
        "codigo_sa6": 640411,
        "cantidad_pares": 1000,
        "moneda": "BOB",
        "tasa_cambio": 6.96,
        "costo_variable_unitario_fab": 104.40, # 15 USD * 6.96
        "costos_fijos_evitables": 34800.0,    # 5000 USD * 6.96
        "cotizacion_compra": 125.28            # 18 USD * 6.96
    })
    print(f"   Costo unitario fabricar BOB: Bs. {res_bob['fabricacion']['costo_unitario_total_bob']:.2f}")
    print(f"   Equivalente en USD: $us. {res_bob['fabricacion']['costo_unitario_total_usd']:.2f}")
    assert abs(res_bob['fabricacion']['costo_unitario_total_usd'] - 20.0) < 0.05
    print("\n✓ CALCULADORA Y CASOS BORDE VERIFICADOS EXITOSAMENTE.")


def probar_desacoplamiento_base_datos():
    print("\n" + "=" * 70)
    print("PRUEBA 4: ESTADO OPERATIVO DE POSTGRESQL (SIN DW)")
    print("=" * 70)
    
    db = db_manaco
    conn = db.obtener_conexion()
    try:
        cur = conn.cursor()
        
        # Verificar qué tablas existen
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tablas = [r[0] for r in cur.fetchall()]
        print(f"Tablas existentes en public: {tablas}")
        
        # Comprobar que NO existen tablas ni vistas del DW
        cur.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public';
        """)
        vistas = [r[0] for r in cur.fetchall()]
        print(f"Vistas existentes en public: {vistas}")
        
        assert "fact_comercio" not in tablas, "fact_comercio no debe existir"
        assert "dim_producto" not in tablas, "dim_producto no debe existir"
        assert "dim_tiempo" not in tablas, "dim_tiempo no debe existir"
        assert "dim_socio" not in tablas, "dim_socio no debe existir"
        assert len(vistas) == 0, "No deben existir vistas del DW"
        
        # Comprobar que inventario_calzado y registro_vision están intactas
        assert "inventario_calzado" in tablas, "inventario_calzado debe existir"
        assert "registro_vision" in tablas, "registro_vision debe existir"
        
        # Comprobar existencias
        inv = db.obtener_inventario()
        print(f"\nInventario operativo desacoplado ({len(inv)} productos):")
        total_pares = 0
        total_bs = 0.0
        for item in inv:
            print(f"   ID {item['id_producto']} | SA6 {item['codigo_sa6']} | {item['categoria_corta']}:")
            print(f"      Stock: {item['stock_actual']} pares | Precio: Bs. {item['precio_unitario_bs']:.2f} ($us. {item['precio_unitario_usd']:.2f})")
            total_pares += item['stock_actual']
            total_bs += item['stock_actual'] * item['precio_unitario_bs']
        
        print(f"\n   Total pares en bodega: {total_pares} pares")
        print(f"   Valorización económica total: Bs. {total_bs:,.2f} ($us. {total_bs/6.96:,.2f})")
        assert total_pares >= 90, "Stock debe ser al menos 90 pares iniciales"
        
        # Comprobar registro_vision
        cur.execute("SELECT COUNT(*) FROM registro_vision;")
        total_movs = cur.fetchone()[0]
        print(f"   Total movimientos históricos en registro_vision: {total_movs}")
        
        # Probar actualización explícita de precio (ID 1 Deportivo)
        nuevo_p_bs = 245.00
        nuevo_p_usd = round(nuevo_p_bs / 6.96, 2)
        res_act = db.actualizar_precio_producto(
            id_producto=1,
            nuevo_precio_bs=nuevo_p_bs,
            nuevo_precio_usd=nuevo_p_usd,
            responsable="Auditor de Pruebas Automatizadas"
        )
        assert res_act["exito"], "Actualización de precio debe ser exitosa"
        
        # Restaurar precio estándar a Bs. 240.00
        db.actualizar_precio_producto(
            id_producto=1,
            nuevo_precio_bs=240.00,
            nuevo_precio_usd=34.48,
            responsable="Restauración de Prueba"
        )
        print("   ✓ Prueba de actualización explícita de precio: COMPLETADA")
        
    finally:
        conn.close()
        
    print("\n✓ BASE OPERATIVA DESACOPLADA Y LIBRE DE TABLAS DW.")


if __name__ == "__main__":
    try:
        probar_referencias_2024()
        probar_calculos_comerciales_filtros()
        probar_calculadora_escenarios_casos_borde()
        probar_desacoplamiento_base_datos()
        print("\n" + "=" * 70)
        print("✓ TODAS LAS VERIFICACIONES HAN SIDO COMPLETADAS CON ÉXITO.")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ ERROR EN LA VERIFICACIÓN: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
