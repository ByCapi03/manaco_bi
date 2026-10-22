"""
limpiar_datasets.py
Herramienta de limpieza, purga y reseteo de datasets para el ecosistema MANACO BI.

Permite:
1. Limpiar las imagenes del dataset de vision artificial (eliminar fotos base/sinteticas
   o fotos de prueba para comenzar una captura de calzados reales desde cero).
2. Limpiar el historial transaccional de movimientos (registro_vision) y reiniciar
   el stock de inventario en la base de datos (PostgreSQL o SQLite).
3. Resumen visual del estado actual del dataset antes y despues de la limpieza.

Uso:
    python clasificador_calzados/limpiar_datasets.py --imagenes      (Limpia solo fotos del dataset)
    python clasificador_calzados/limpiar_datasets.py --inventario    (Limpia movimientos y resetea stock)
    python clasificador_calzados/limpiar_datasets.py --todo          (Limpia imagenes y base de datos)
    python clasificador_calzados/limpiar_datasets.py                 (Modo interactivo en consola)
"""

import os
import sys
import argparse
from pathlib import Path

# Asegurar importacion de modulos locales
CARPETA_ACTUAL = Path(__file__).resolve().parent
if str(CARPETA_ACTUAL) not in sys.path:
    sys.path.insert(0, str(CARPETA_ACTUAL))

from config import CLASES, CARPETA_DATASET, NOMBRES_CLASES
from db_manaco import db_manaco


def obtener_conteo_imagenes():
    """Retorna un diccionario con la cantidad de imagenes por clase."""
    conteo = {}
    for c in CLASES:
        ruta = os.path.join(CARPETA_DATASET, c)
        if os.path.exists(ruta):
            archivos = [f for f in os.listdir(ruta) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            conteo[c] = len(archivos)
        else:
            conteo[c] = 0
    return conteo


def mostrar_estado_actual():
    """Muestra en consola el estado actual de las imagenes y la base de datos."""
    conteos = obtener_conteo_imagenes()
    total_imgs = sum(conteos.values())
    kpis = db_manaco.obtener_kpis()
    movs = db_manaco.obtener_movimientos(limite=1)

    print("=" * 65)
    print(" ESTADO ACTUAL DE LOS DATASETS (MANACO BI & VISION)")
    print("=" * 65)
    print(" 1. DATASET DE VISION ARTIFICIAL (Imagenes en disco):")
    for c in CLASES:
        nombre = NOMBRES_CLASES.get(c, c)
        print(f"    - {c:18} : {conteos.get(c, 0):4d} imagenes ({nombre})")
    print(f"    -> Total de imagenes en dataset: {total_imgs}")
    print()
    print(f" 2. BASE DE DATOS TRANSACCIONAL (Motor: {db_manaco.motor.upper()}):")
    print(f"    - Total pares en stock:         {kpis['total_pares']:,} pares")
    print(f"    - Valor total inventario:       Bs. {kpis['total_valor_bs']} | $us. {kpis['total_valor_usd']}")
    print(f"    - Registros en historial:       {kpis['total_ingresos_ia']} detecciones IA registradas")
    print("=" * 65)
    return total_imgs, kpis


def limpiar_imagenes():
    """Elimina las imagenes dentro de las carpetas de clases, manteniendo las carpetas."""
    print("\n[LIMPIEZA] Eliminando archivos de imagen en dataset/...")
    eliminadas_total = 0
    for c in CLASES:
        ruta = os.path.join(CARPETA_DATASET, c)
        if not os.path.exists(ruta):
            os.makedirs(ruta, exist_ok=True)
            continue
        archivos = [f for f in os.listdir(ruta) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        for f in archivos:
            try:
                os.remove(os.path.join(ruta, f))
                eliminadas_total += 1
            except Exception as e:
                print(f"  [!] No se pudo eliminar {f}: {e}")
        print(f"  [OK] Categoria '{c}': {len(archivos)} imagenes eliminadas.")
    print(f"[EXITO] Total de imagenes depuradas: {eliminadas_total}. Carpetas listas para nuevas capturas.")
    return eliminadas_total


def limpiar_inventario(stock_base=30):
    """Reinicia la base de datos de inventario y borra registros de auditoria/vision."""
    print(f"\n[LIMPIEZA] Reiniciando inventario a {stock_base} pares por categoria en {db_manaco.motor.upper()}...")
    res = db_manaco.reiniciar_inventario(stock_base=stock_base)
    if res.get("exito"):
        print(f"  [OK] {res.get('mensaje')}")
        print("  [OK] Tabla 'registro_vision' purgada a 0 registros.")
    else:
        print(f"  [ERROR]: {res.get('error')}")
    return res


def menu_interactivo():
    """Menu interactivo por consola."""
    mostrar_estado_actual()
    print("\n¿Que operacion de limpieza deseas realizar?")
    print("  [1] Limpiar solo imagenes del dataset (dejar carpetas listas para fotos reales)")
    print("  [2] Limpiar/Reiniciar base de datos de inventario y auditoria (stock a nivel base)")
    print("  [3] Limpiar TODO (Imagenes del dataset + Base de datos de inventario)")
    print("  [4] Cancelar y salir")
    
    opcion = input("\nSelecciona una opcion (1-4): ").strip()
    if opcion == "1":
        confirmar = input("¿Confirmas eliminar todas las imagenes del dataset? (s/n): ").strip().lower()
        if confirmar in ["s", "si", "y", "yes"]:
            limpiar_imagenes()
            mostrar_estado_actual()
    elif opcion == "2":
        confirmar = input("¿Confirmas reiniciar el inventario y purgar el historial? (s/n): ").strip().lower()
        if confirmar in ["s", "si", "y", "yes"]:
            limpiar_inventario()
            mostrar_estado_actual()
    elif opcion == "3":
        confirmar = input("¿Confirmas purgar imagenes e inventario completo? (s/n): ").strip().lower()
        if confirmar in ["s", "si", "y", "yes"]:
            limpiar_imagenes()
            limpiar_inventario()
            mostrar_estado_actual()
    else:
        print("\nOperacion cancelada. No se realizo ningun cambio.")


def main():
    parser = argparse.ArgumentParser(description="Limpiador de Datasets y Base de Datos Manaco BI")
    parser.add_argument("--imagenes", action="store_true", help="Elimina todas las imagenes del dataset de vision")
    parser.add_argument("--inventario", action="store_true", help="Reinicia el inventario y borra el historial de movimientos")
    parser.add_argument("--todo", action="store_true", help="Limpia imagenes e inventario")
    parser.add_argument("--stock-base", type=int, default=30, help="Nivel de stock inicial para cada categoria al reiniciar (default: 30)")
    parser.add_argument("--info", action="store_true", help="Solo muestra el estado actual sin modificar nada")
    args = parser.parse_args()

    if args.info:
        mostrar_estado_actual()
        return

    if args.todo:
        limpiar_imagenes()
        limpiar_inventario(stock_base=args.stock_base)
        mostrar_estado_actual()
    elif args.imagenes:
        limpiar_imagenes()
        mostrar_estado_actual()
    elif args.inventario:
        limpiar_inventario(stock_base=args.stock_base)
        mostrar_estado_actual()
    else:
        # Modo interactivo
        try:
            menu_interactivo()
        except (KeyboardInterrupt, EOFError):
            print("\nOperacion interrumpida por el usuario.")


if __name__ == "__main__":
    main()
