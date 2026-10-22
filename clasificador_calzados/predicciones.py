"""
clasificador_calzados/predicciones.py
Módulo de pronósticos estadísticos, evaluación temporal y planificación de inventario.

Componentes:
A. Proyección Anual Exploratoria de Comercio Exterior (Excel):
   - Comparación de Pronóstico Ingenuo vs Tendencia Lineal.
   - Evaluación cronológica fuera de muestra (Train 2020-2023, Test 2024).
   - Cobertura anual y declaración estricta de limitaciones.
   - No se presenta como demanda de MANACO.

B. Pronóstico de Ventas Operativas y Reposición de Stock:
   - Comparación de Promedio Móvil (7 días) vs Pronóstico Ingenuo con partición cronológica.
   - MAE (Error Absoluto Medio) en unidades de pares.
   - Pronóstico a 7 días vista por producto.
   - Cálculo de reposición sugerida interactiva:
     Sugerencia = max(0, (Demanda * LeadTime) + StockSeguridad - StockDisponible - PedidosPendientes)
   - Manejo explícito de "Datos insuficientes".
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


def evaluar_proyecciones_excel_comercio(df_excel: pd.DataFrame = None) -> Dict[str, Any]:
    """
    Evalúa modelos de proyección anual sobre los registros de importación del Excel.
    Compara Pronóstico Ingenuo vs Tendencia Simple con partición temporal (Train: 2020-2023, Test: 2024).
    """
    if df_excel is None:
        import analisis_comercial as ac
        df_excel = ac.cargar_dataset_excel()

    sub = df_excel[df_excel["Flujo_comercial"] == "Importación"].copy()
    
    # Cobertura por año
    cobertura_por_anio = []
    for anio in sorted(sub["Año"].unique()):
        df_a = sub[sub["Año"] == anio]
        cobertura_por_anio.append({
            "anio": int(anio),
            "total_registros": len(df_a),
            "socios_distintos": int(df_a["Socio_comercial"].nunique()),
            "valor_usd": round(float(df_a["Valor_USD"].sum()), 2),
            "cantidad_pares": int(df_a["Cantidad_pares"].sum())
        })

    # Proyecciones por categoría
    categorias_map = {
        640411: "Deportivo (SA 640411)",
        640399: "Casual Cuero (SA 640399)",
        640420: "Formal Vestir (SA 640420)"
    }

    evaluaciones_categorias = []

    for sa6, nombre_cat in categorias_map.items():
        df_cat = sub[sub["Código_SA6"] == sa6].groupby("Año").agg({
            "Cantidad_pares": "sum",
            "Valor_USD": "sum"
        }).reset_index().sort_values("Año")

        anios = df_cat["Año"].tolist()
        pares = df_cat["Cantidad_pares"].tolist()

        # Partición cronológica: Train 2020-2023 (índices 0..3), Test 2024 (índice 4)
        if len(pares) >= 5:
            train_anios = anios[:4] # [2020, 2021, 2022, 2023]
            train_pares = pares[:4]
            test_anio = anios[4]   # 2024
            real_2024 = pares[4]

            # 1. Pronóstico Ingenuo: y_hat_2024 = y_2023
            pred_naive_2024 = train_pares[-1]
            error_naive_2024 = abs(real_2024 - pred_naive_2024)
            pct_error_naive = (error_naive_2024 / max(1, real_2024)) * 100

            # 2. Tendencia Lineal Simple: y = a + b * (t - 2020)
            t_train = np.array(train_anios) - 2020
            p_train = np.array(train_pares)
            coefs = np.polyfit(t_train, p_train, deg=1) # coefs[0] = pendiente, coefs[1] = intercepto

            pred_trend_2024 = max(0, float(np.polyval(coefs, test_anio - 2020)))
            error_trend_2024 = abs(real_2024 - pred_trend_2024)
            pct_error_trend = (error_trend_2024 / max(1, real_2024)) * 100

            # Proyección exploratoria 2025
            coefs_full = np.polyfit(np.array(anios) - 2020, np.array(pares), deg=1)
            proj_naive_2025 = real_2024
            proj_trend_2025 = max(0, float(np.polyval(coefs_full, 2025 - 2020)))

            evaluaciones_categorias.append({
                "codigo_sa6": str(sa6),
                "categoria": nombre_cat,
                "historico": {
                    "anios": [int(a) for a in anios],
                    "pares": [int(p) for p in pares]
                },
                "evaluacion_2024": {
                    "real_2024_pares": int(real_2024),
                    "pred_naive_pares": int(pred_naive_2024),
                    "error_naive_pares": int(error_naive_2024),
                    "error_naive_pct": round(pct_error_naive, 1),
                    "pred_trend_pares": int(pred_trend_2024),
                    "error_trend_pares": int(error_trend_2024),
                    "error_trend_pct": round(pct_error_trend, 1),
                    "mejor_modelo": "Tendencia Lineal" if error_trend_2024 < error_naive_2024 else "Pronóstico Ingenuo"
                },
                "proyeccion_2025_exploratoria": {
                    "naive_2025_pares": int(proj_naive_2025),
                    "trend_2025_pares": int(proj_trend_2025)
                }
            })

    return {
        "exito": True,
        "cobertura_por_anio": cobertura_por_anio,
        "categorias": evaluaciones_categorias,
        "aviso_metodologico": "Serie histórica de 5 años (2020-2024) reportada por aduanas de España. La cobertura variable de socios y el tamaño limitado de la muestra restringen la precisión predictiva. Esta proyección NO constituye ni debe interpretarse como la demanda comercial de calzados de MANACO."
    }


def evaluar_pronostico_ventas_operativas(db_instancia, id_producto: int = None, lead_time_config: int = 7, stock_seguridad_config: int = 10) -> Dict[str, Any]:
    """
    Evalúa modelos predictivos sobre las ventas operativas del catálogo con separación cronológica.
    Compara Promedio Móvil (7 días) vs Pronóstico Ingenuo (Lag-1).
    Calcula MAE en unidades de pares y genera sugerencia de reposición con fórmula de reorden.
    """
    conn = db_instancia.obtener_conexion()
    try:
        cur = conn.cursor()

        # Obtener ventas históricas agrupadas por día y producto
        filtro_prod = f"AND rv.id_producto = {id_producto}" if id_producto else ""
        cur.execute(f"""
            SELECT 
                DATE(rv.fecha_hora) as dia,
                rv.id_producto,
                ic.codigo_sku,
                ic.nombre_producto,
                ic.categoria_corta,
                ic.stock_actual,
                ic.stock_minimo,
                ic.lead_time_dias,
                ic.stock_seguridad,
                ic.pedidos_pendientes,
                SUM(rv.cantidad) as total_pares,
                SUM(rv.ingreso_total_bs) as total_bs
            FROM registro_vision rv
            JOIN inventario_calzado ic ON rv.id_producto = ic.id_producto
            WHERE rv.accion = 'VENTA' {filtro_prod}
            GROUP BY DATE(rv.fecha_hora), rv.id_producto, ic.codigo_sku, ic.nombre_producto, 
                     ic.categoria_corta, ic.stock_actual, ic.stock_minimo, ic.lead_time_dias, 
                     ic.stock_seguridad, ic.pedidos_pendientes
            ORDER BY dia ASC;
        """)
        filas = cur.fetchall()

        if len(filas) < 14:
            return {
                "exito": False,
                "estado": "Datos insuficientes",
                "mensaje": f"Se requieren al menos 14 días con registros de ventas para evaluar modelos predictivos. Actualmente hay {len(filas)} días registrados.",
                "productos": []
            }

        # Organizar por producto
        datos_por_prod = {}
        for r in filas:
            p_id = r[1]
            if p_id not in datos_por_prod:
                datos_por_prod[p_id] = {
                    "id_producto": p_id,
                    "sku": r[2],
                    "nombre": r[3],
                    "categoria": r[4],
                    "stock_actual": r[5],
                    "stock_minimo": r[6],
                    "lead_time": lead_time_config or r[7] or 7,
                    "stock_seguridad": stock_seguridad_config or r[8] or 10,
                    "pedidos_pendientes": r[9] or 0,
                    "fechas": [],
                    "pares": []
                }
            datos_por_prod[p_id]["fechas"].append(str(r[0]))
            datos_por_prod[p_id]["pares"].append(int(r[10]))

        resultados_productos = []
        totales_resumen = {
            "total_ventas_previstas_7d": 0,
            "mae_promedio_pares": 0.0,
            "total_sugerencia_reposicion": 0
        }

        maes_acum = []

        for p_id, p_data in datos_por_prod.items():
            serie = np.array(p_data["pares"], dtype=float)
            n_total = len(serie)

            if n_total < 14:
                continue

            # Separación cronológica: 80% train, 20% test (mínimo 7 días de test)
            n_train = max(7, int(n_total * 0.8))
            train = serie[:n_train]
            test = serie[n_train:]
            n_test = len(test)

            # 1. Modelo Ingenuo (Naive lag-1) en test
            # y_hat_t = y_{t-1}
            preds_naive = np.zeros(n_test)
            preds_naive[0] = train[-1]
            preds_naive[1:] = test[:-1]
            mae_naive = float(np.mean(np.abs(test - preds_naive)))

            # 2. Modelo Promedio Móvil (Moving Average 7 días)
            # Para predecir test[i], toma los 7 valores precedentes reales
            serie_completa = np.concatenate([train[-7:], test])
            preds_ma7 = []
            for i in range(n_test):
                ventana = serie_completa[i:i+7]
                preds_ma7.append(float(np.mean(ventana)))
            preds_ma7 = np.array(preds_ma7)
            mae_ma7 = float(np.mean(np.abs(test - preds_ma7)))

            # Mejor modelo según menor MAE
            mejor_modelo = "Promedio Móvil (7D)" if mae_ma7 <= mae_naive else "Pronóstico Ingenuo"
            mae_ganador = min(mae_ma7, mae_naive)
            maes_acum.append(mae_ganador)

            # Pronóstico para los próximos 7 días a partir de la última ventana disponible
            ventana_futura = serie[-7:].tolist()
            proyeccion_7d = []
            for d in range(7):
                prox_val = max(0.0, float(np.mean(ventana_futura[-7:])))
                proyeccion_7d.append(round(prox_val, 1))
                ventana_futura.append(prox_val)

            total_pronostico_7d = int(round(sum(proyeccion_7d)))
            demanda_diaria_promedio = float(np.mean(proyeccion_7d))

            # Cálculo de la Sugerencia de Reposición Oficial:
            # Demanda en Lead Time = demanda_diaria * lead_time
            # Punto de Reorden = Demanda en Lead Time + stock_seguridad
            # Sugerencia = max(0, Punto de Reorden - stock_actual - pedidos_pendientes)
            demanda_lead_time = demanda_diaria_promedio * p_data["lead_time"]
            punto_reorden = demanda_lead_time + p_data["stock_seguridad"]
            stock_disponible_neto = p_data["stock_actual"] + p_data["pedidos_pendientes"]
            sugerencia_reposicion = max(0, int(round(punto_reorden - stock_disponible_neto)))

            totales_resumen["total_ventas_previstas_7d"] += total_pronostico_7d
            totales_resumen["total_sugerencia_reposicion"] += sugerencia_reposicion

            # Generar fechas del horizonte de 7 días
            fechas_horizonte = []
            base_date = datetime.now()
            for d in range(1, 8):
                fechas_horizonte.append((base_date + timedelta(days=d)).strftime("%d/%m"))

            resultados_productos.append({
                "id_producto": p_id,
                "sku": p_data["sku"],
                "nombre_producto": p_data["nombre"],
                "categoria": p_data["categoria"],
                "evaluacion": {
                    "periodo_evaluado_dias": n_test,
                    "mae_promedio_movil": round(mae_ma7, 2),
                    "mae_ingenuo": round(mae_naive, 2),
                    "mejor_modelo": mejor_modelo,
                    "mae_ganador_pares": round(mae_ganador, 2),
                    "origen_datos": "Ventas operativas registradas en registro_vision"
                },
                "pronostico_proximos_7d": {
                    "fechas": fechas_horizonte,
                    "valores_diarios_pares": proyeccion_7d,
                    "total_semana_pares": total_pronostico_7d,
                    "demanda_diaria_media": round(demanda_diaria_promedio, 2)
                },
                "planificacion_inventario": {
                    "stock_actual": p_data["stock_actual"],
                    "lead_time_dias": p_data["lead_time"],
                    "stock_seguridad": p_data["stock_seguridad"],
                    "pedidos_pendientes": p_data["pedidos_pendientes"],
                    "demanda_prevista_lead_time": round(demanda_lead_time, 1),
                    "punto_reorden": round(punto_reorden, 1),
                    "sugerencia_reposicion_pares": sugerencia_reposicion,
                    "alerta_reorden": p_data["stock_actual"] <= punto_reorden
                }
            })

        if maes_acum:
            totales_resumen["mae_promedio_pares"] = round(float(np.mean(maes_acum)), 2)

        return {
            "exito": True,
            "totales_resumen": totales_resumen,
            "productos": resultados_productos,
            "aviso_metodologico": "Evaluación efectuada con estricta separación cronológica: conjunto de entrenamiento sin filtrar al conjunto de prueba. No se generan intervalos de confianza arbitrarios sin sustento muestral. Las sugerencias de reposición requieren confirmación de un supervisor y no emiten órdenes de compra automáticas."
        }

    finally:
        conn.close()
