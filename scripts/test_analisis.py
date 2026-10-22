"""scripts/test_analisis.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "clasificador_calzados"))

import analisis_comercial as ac

def main():
    print("--- 1. Filtros Disponibles ---")
    f = ac.obtener_opciones_filtros()
    print("Socios:", len(f["socios"]), "| Anios:", f["anios"])
    print("Categorias:", [c["codigo_sa6"] for c in f["categorias"]])

    print("\n--- 2. Comprobacion de Referencias 2024 ---")
    for sa6 in [640399, 640411, 640420]:
        val = ac.obtener_referencia_importacion_2024(sa6)
        print(f"Codigo {sa6}: {val:.2f} USD/par")

    print("\n--- 3. Prueba de Escenarios ---")
    for esc_tipo in ["importar_mas_conveniente", "fabricar_mas_conveniente", "condiciones_equivalentes"]:
        p = ac.obtener_escenario_predefinido(esc_tipo)
        r = ac.calcular_escenario_make_or_buy(p)
        dec = r["analisis_diferencial"]["decision_recomendada"]
        dif = r["analisis_diferencial"]["diferencia_costo_usd"]
        q_star = r["analisis_diferencial"]["punto_indiferencia_pares"]
        print(f"{p['nombre']}")
        print(f"  Decision: {dec} | Dif Costo USD: ${dif:,.2f} | Q* Indiferencia: {q_star}")

if __name__ == "__main__":
    main()
