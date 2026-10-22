"""
clasificador_calzados/datos_sinteticos.py
Generador determinista con semilla fija de historial diario (12 meses / 365 días)
para los 6 productos de MANACO BI.

Reglas metodológicas y trazabilidad:
1. Semilla fija (seed=42) para reproducibilidad absoluta e idempotencia.
2. 365 días cronológicos que simulan ventas, reposiciones y saldos diarios coherentes.
3. Ventas discriminadas por 3 canales: Tiendas Propias, Distribuidores y E-commerce.
4. Cada venta almacena su precio unitario efectivo histórico para aislar ingresos.
5. Las reposiciones evitan en todo momento el stock negativo.
6. Se separa con origen = 'sintetico_12m' de los movimientos interactivos y del Excel.
7. Declaración explícita: No se infiere edad ni segmentación etaria desde los datos.
   Métricas de conversión y abandono digital se reportan como "No disponible".
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
from config import TASA_CAMBIO_OFICIAL

SEMILLA_DETERMINISTA = 42

REGLAS_SINTETICAS = {
    "semilla": SEMILLA_DETERMINISTA,
    "periodo_dias": 365,
    "canales_probabilidades": {
        "Tiendas Propias": 0.58,
        "Distribuidores Mayoristas": 0.27,
        "E-commerce / Tienda Online": 0.15
    },
    "estacionalidad_mensual": {
        1: 0.95,   # Enero
        2: 0.90,   # Febrero (Post-festividades)
        3: 1.00,   # Marzo
        4: 1.05,   # Abril
        5: 1.25,   # Mayo (Día de la Madre en Bolivia)
        6: 1.00,   # Junio
        7: 1.05,   # Julio
        8: 1.15,   # Agosto (Fiestas patrias / eventos)
        9: 1.05,   # Septiembre
        10: 1.00,  # Octubre
        11: 1.10,  # Noviembre (Preparación fin de año)
        12: 1.50   # Diciembre (Aguinaldo y Navidad)
    },
    "demandas_base_diarias": {
        1: {"sku": "DEP-BAS", "media": 4.0, "finde_mult": 1.40},
        2: {"sku": "DEP-CNF", "media": 2.8, "finde_mult": 1.30},
        3: {"sku": "CAS-BAS", "media": 3.4, "finde_mult": 1.35},
        4: {"sku": "CAS-CNF", "media": 2.2, "finde_mult": 1.25},
        5: {"sku": "VES-BAS", "media": 1.9, "fin_mes_mult": 1.35},
        6: {"sku": "VES-CNF", "media": 1.3, "fin_mes_mult": 1.30}
    },
    "aviso_metodologico": "Datos generados sintéticamente con fines de planificación y evaluación de modelos predictivos. No representan auditorías contables ni cotizaciones contractuales de Manaco."
}


def generar_historial_sintetico_12m(db_instancia, forzar_regeneracion: bool = False) -> Dict[str, Any]:
    """
    Genera e inserta en la base de datos el historial sintético de 12 meses (365 días).
    Es idempotente: si ya existen registros sintéticos y forzar_regeneracion es False,
    no los duplica.
    """
    conn = db_instancia.obtener_conexion()
    try:
        cur = conn.cursor()
        
        # Verificar idempotencia
        cur.execute("SELECT COUNT(*) FROM registro_vision WHERE origen = 'sintetico_12m';")
        cant_existente = cur.fetchone()[0]

        if cant_existente > 0 and not forzar_regeneracion:
            return {
                "exito": True,
                "mensaje": f"El historial sintético ya está cargado ({cant_existente} movimientos registrados). No se duplicó.",
                "total_registros": cant_existente,
                "idempotente": True,
                "reglas": REGLAS_SINTETICAS
            }

        # Si se fuerza regeneración, eliminar solo los anteriores sintéticos
        if forzar_regeneracion and cant_existente > 0:
            cur.execute("DELETE FROM registro_vision WHERE origen = 'sintetico_12m';")
            conn.commit()

        # Configurar generador de números pseudoaleatorios
        rng = random.Random(SEMILLA_DETERMINISTA)

        # Obtener catálogo activo de productos
        cur.execute("""
            SELECT id_producto, codigo_sku, categoria_corta, nombre_producto, 
                   precio_unitario_usd, precio_unitario_bs, stock_minimo
            FROM inventario_calzado
            ORDER BY id_producto;
        """)
        prods = cur.fetchall()
        prods_dict = {
            r[0]: {
                "id_producto": r[0],
                "sku": r[1],
                "categoria_corta": r[2],
                "nombre_producto": r[3],
                "precio_usd": float(r[4]),
                "precio_bs": float(r[5]),
                "stock_minimo": int(r[6])
            }
            for r in prods
        }

        # Fecha base: Hoy menos 365 días
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=365)

        # Saldos simulados por producto
        stock_simulado = {p_id: 35 for p_id in prods_dict}
        movimientos_a_insertar = []

        canales = ["Tiendas Propias", "Distribuidores Mayoristas", "E-commerce / Tienda Online"]
        pesos_canales = [0.58, 0.27, 0.15]

        # Iterar los 365 días
        for dia_idx in range(365):
            fecha_dia = fecha_inicio + timedelta(days=dia_idx)
            mes = fecha_dia.month
            dia_sem = fecha_dia.weekday() # 0 = Lunes, 5 = Sábado, 6 = Domingo
            es_fin_semana = dia_sem in (4, 5, 6) # Viernes a Domingo
            es_fin_mes = fecha_dia.day >= 25

            factor_mes = REGLAS_SINTETICAS["estacionalidad_mensual"].get(mes, 1.0)

            for p_id, p_info in prods_dict.items():
                regla = REGLAS_SINTETICAS["demandas_base_diarias"].get(p_id, {"media": 2.5})
                media = regla["media"] * factor_mes

                if es_fin_semana and "finde_mult" in regla:
                    media *= regla["finde_mult"]
                if es_fin_mes and "fin_mes_mult" in regla:
                    media *= regla["fin_mes_mult"]

                # Cantidad de pares vendidos hoy (Poisson / normal discreta)
                # Asegurar un mínimo de variación estocástica
                cant_pares_venta = max(0, int(round(rng.gauss(media, media * 0.35))))

                # Si hay inventario para vender
                if cant_pares_venta > 0:
                    cant_efectiva = min(stock_simulado[p_id], cant_pares_venta)
                    if cant_efectiva > 0:
                        stock_simulado[p_id] -= cant_efectiva
                        canal = rng.choices(canales, weights=pesos_canales, k=1)[0]
                        p_usd = p_info["precio_usd"]
                        p_bs = p_info["precio_bs"]

                        # Descuento comercial leve solo para distribuidores mayoristas (5%)
                        if canal == "Distribuidores Mayoristas":
                            p_usd = round(p_usd * 0.95, 2)
                            p_bs = round(p_bs * 0.95, 2)

                        ingreso_usd = round(cant_efectiva * p_usd, 2)
                        ingreso_bs = round(cant_efectiva * p_bs, 2)

                        movimientos_a_insertar.append((
                            fecha_dia,
                            p_id,
                            p_info["categoria_corta"],
                            p_info["nombre_producto"],
                            "VENTA",
                            cant_efectiva,
                            p_usd,
                            p_bs,
                            ingreso_usd,
                            ingreso_bs,
                            canal,
                            stock_simulado[p_id],
                            1.0,
                            "sintetico_12m",
                            "Simulador Transaccional 12M",
                            f"Venta diaria en canal {canal}"
                        ))

                # Regla de reposición automática de simulación: si cae por debajo del mínimo, generar entrada
                if stock_simulado[p_id] <= p_info["stock_minimo"]:
                    lote_reposicion = rng.randint(25, 45)
                    stock_simulado[p_id] += lote_reposicion
                    movimientos_a_insertar.append((
                        fecha_dia + timedelta(hours=8),
                        p_id,
                        p_info["categoria_corta"],
                        p_info["nombre_producto"],
                        "ENTRADA",
                        lote_reposicion,
                        0.00,
                        0.00,
                        0.00,
                        0.00,
                        "N/A",
                        stock_simulado[p_id],
                        1.0,
                        "sintetico_12m",
                        "Reposición Fabril Simulada",
                        f"Lote de reabastecimiento programado ({lote_reposicion} pares)"
                    ))

        # Insertar en base de datos
        if db_instancia.motor == "postgresql":
            cur.executemany("""
                INSERT INTO registro_vision (
                    fecha_hora, id_producto, categoria_nombre, producto_nombre,
                    accion, cantidad, precio_unitario_venta_usd, precio_unitario_venta_bs,
                    ingreso_total_usd, ingreso_total_bs, canal_venta, stock_resultante,
                    confianza, origen, responsable, nota
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                );
            """, movimientos_a_insertar)
        else:
            cur.executemany("""
                INSERT INTO registro_vision (
                    fecha_hora, id_producto, categoria_nombre, producto_nombre,
                    accion, cantidad, precio_unitario_venta_usd, precio_unitario_venta_bs,
                    ingreso_total_usd, ingreso_total_bs, canal_venta, stock_resultante,
                    confianza, origen, responsable, nota
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?
                );
            """, [
                (
                    m[0].isoformat(), m[1], m[2], m[3],
                    m[4], m[5], m[6], m[7],
                    m[8], m[9], m[10], m[11],
                    m[12], m[13], m[14], m[15]
                )
                for m in movimientos_a_insertar
            ])

        conn.commit()

        # Calcular métricas resumen
        total_ventas_pares = sum(m[5] for m in movimientos_a_insertar if m[4] == "VENTA")
        total_ingresos_usd = sum(m[8] for m in movimientos_a_insertar if m[4] == "VENTA")
        total_ingresos_bs = sum(m[9] for m in movimientos_a_insertar if m[4] == "VENTA")

        return {
            "exito": True,
            "mensaje": f"Se generaron e insertaron {len(movimientos_a_insertar):,} transacciones sintéticas para 365 días con semilla {SEMILLA_DETERMINISTA}.",
            "total_registros": len(movimientos_a_insertar),
            "total_pares_vendidos": total_ventas_pares,
            "total_ingresos_usd": round(total_ingresos_usd, 2),
            "total_ingresos_bs": round(total_ingresos_bs, 2),
            "idempotente": False,
            "reglas": REGLAS_SINTETICAS
        }

    finally:
        conn.close()
