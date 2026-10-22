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
        "datos": {
            "cobertura_por_anio": cobertura_por_anio,
            "categorias": evaluaciones_categorias
        },
        "aviso_metodologico": "Serie histórica de 5 años (2020-2024) reportada por aduanas de España. La cobertura variable de socios y el tamaño limitado de la muestra restringen la precisión predictiva. Esta proyección NO constituye ni debe interpretarse como la demanda comercial de calzados de MANACO."
    }


def evaluar_pronostico_ventas_operativas(db_instancia, id_producto: int = None, lead_time_config: int = None, stock_seguridad_config: int = None) -> Dict[str, Any]:
    """
    Evalúa modelos predictivos sobre las ventas operativas del catálogo con estricta separación cronológica.
    - Excluye entradas, ajustes u otras salidas que no representen ventas.
    - Conserva diferenciados los datos simulados y las ventas registradas.
    - Completa con cero los días sin ventas únicamente dentro del período de registro conocido [d_min, d_max].
    - Compara Promedio Móvil (7 días) vs Pronóstico Ingenuo (Lag-1) calculando MAE en pares/día.
    - Proyecta 7 días con fechas calendario reales.
    - Calcula necesidad y faltante de cobertura preventivo:
      Demanda en plazo = suma de ventas pronosticadas durante su plazo de entrega.
      Umbral de reposición = Demanda en plazo + Reserva de seguridad.
      Posición de inventario = Stock disponible + Entradas pendientes confirmadas.
      Faltante de cobertura = máx(0, Umbral - Posición de inventario).
    """
    conn = db_instancia.obtener_conexion()
    try:
        cur = conn.cursor()

        # 1. Catálogo de productos completo
        filtro_cat = f"WHERE id_producto = {id_producto}" if id_producto else ""
        cur.execute(f"""
            SELECT 
                id_producto, codigo_sku, nombre_producto, categoria_corta,
                stock_actual, stock_minimo, lead_time_dias, stock_seguridad, pedidos_pendientes
            FROM inventario_calzado
            {filtro_cat}
            ORDER BY id_producto ASC;
        """)
        cat_filas = cur.fetchall()
        if not cat_filas:
            return {
                "exito": False,
                "estado": "Sin productos",
                "mensaje": "No se encontraron productos en el inventario.",
                "productos": []
            }

        catalogo_dict = {}
        for cf in cat_filas:
            p_id = cf[0]
            catalogo_dict[p_id] = {
                "id_producto": p_id,
                "sku": cf[1],
                "nombre": cf[2],
                "categoria": cf[3],
                "stock_actual": int(cf[4]),
                "stock_minimo": int(cf[5]),
                "lead_time_dias": int(cf[6] or 7),
                "stock_seguridad": int(cf[7] or 10),
                "pedidos_pendientes": int(cf[8] or 0)
            }

        # 2. Metadatos de procedencia de ventas (simuladas vs registradas en vivo)
        cur.execute("""
            SELECT 
                origen,
                COUNT(*) as cant_movs,
                COALESCE(SUM(cantidad), 0) as cant_pares,
                MIN(DATE(fecha_hora)) as min_fecha,
                MAX(DATE(fecha_hora)) as max_fecha
            FROM registro_vision
            WHERE accion = 'VENTA'
            GROUP BY origen;
        """)
        origen_filas = cur.fetchall()
        total_simuladas = 0
        total_registradas = 0
        min_sim, max_sim = None, None
        min_reg, max_reg = None, None

        for of in origen_filas:
            orig = str(of[0])
            pares = int(of[2])
            f_min = of[3]
            f_max = of[4]
            if orig == "sintetico_12m":
                total_simuladas += pares
                min_sim = f_min
                max_sim = f_max
            else:
                total_registradas += pares
                if min_reg is None or (f_min and f_min < min_reg):
                    min_reg = f_min
                if max_reg is None or (f_max and f_max > max_reg):
                    max_reg = f_max

        # Etiqueta breve descriptiva de la fuente
        partes_etiqueta = []
        if total_simuladas > 0 and min_sim and max_sim:
            partes_etiqueta.append(f"Simulación 12M ({min_sim.strftime('%d/%m/%Y')} al {max_sim.strftime('%d/%m/%Y')})")
        if total_registradas > 0 and min_reg and max_reg:
            partes_etiqueta.append(f"Ventas registradas en vivo ({total_registradas} pares)")

        etiqueta_fuente = " + ".join(partes_etiqueta) if partes_etiqueta else "Ventas operativas registradas"
        badge_simulada = "Pronóstico con ventas simuladas" if total_simuladas > 0 else "Pronóstico con ventas registradas"

        fuente_datos = {
            "es_simulado": total_simuladas > 0,
            "total_ventas_simuladas": total_simuladas,
            "periodo_simulado": f"{min_sim.strftime('%d/%m/%Y')} a {max_sim.strftime('%d/%m/%Y')}" if (min_sim and max_sim) else None,
            "total_ventas_registradas": total_registradas,
            "periodo_registrado": f"{min_reg.strftime('%d/%m/%Y')} a {max_reg.strftime('%d/%m/%Y')}" if (min_reg and max_reg) else None,
            "etiqueta_fuente": etiqueta_fuente,
            "badge_texto": badge_simulada
        }

        # 3. Ventas operativas reales fechadas agrupadas por día y producto (excluyendo entradas/ajustes)
        filtro_prod = f"AND rv.id_producto = {id_producto}" if id_producto else ""
        cur.execute(f"""
            SELECT 
                DATE(rv.fecha_hora) as dia,
                rv.id_producto,
                SUM(rv.cantidad) as total_pares
            FROM registro_vision rv
            WHERE rv.accion = 'VENTA' {filtro_prod}
            GROUP BY DATE(rv.fecha_hora), rv.id_producto
            ORDER BY dia ASC;
        """)
        ventas_filas = cur.fetchall()

        # Agrupar ventas diarias por producto: {p_id: {dia: pares}}
        ventas_por_prod = {p_id: {} for p_id in catalogo_dict}
        for vf in ventas_filas:
            d = vf[0]
            pid = vf[1]
            cant = int(vf[2])
            if pid in ventas_por_prod:
                ventas_por_prod[pid][d] = cant

        resultados_productos = []
        maes_ma7_acum = []
        maes_naive_acum = []
        total_ventas_previstas_7d = 0
        total_pares_por_reponer = 0
        total_prods_por_reponer = 0
        lead_times_usados = []

        for p_id, p_info in catalogo_dict.items():
            ventas_dict = ventas_por_prod.get(p_id, {})

            # Si no hay ventas registradas
            if not ventas_dict:
                resultados_productos.append({
                    "id_producto": p_id,
                    "sku": p_info["sku"],
                    "nombre_producto": p_info["nombre"],
                    "categoria": p_info["categoria"],
                    "disponible": p_info["stock_actual"],
                    "lead_time_dias": lead_time_config or p_info["lead_time_dias"],
                    "reserva_seguridad": stock_seguridad_config if stock_seguridad_config is not None else p_info["stock_seguridad"],
                    "demanda_plazo": 0,
                    "necesidad": stock_seguridad_config if stock_seguridad_config is not None else p_info["stock_seguridad"],
                    "pendientes_recibir": p_info["pedidos_pendientes"],
                    "posicion_inventario": p_info["stock_actual"] + p_info["pedidos_pendientes"],
                    "faltante_cobertura": max(0, (stock_seguridad_config if stock_seguridad_config is not None else p_info["stock_seguridad"]) - (p_info["stock_actual"] + p_info["pedidos_pendientes"])),
                    "estado": "Historial insuficiente",
                    "mensaje_estado": "Historial insuficiente (sin ventas registradas)",
                    "ventas_previstas_7d": 0,
                    "demanda_diaria_media": 0.0,
                    "evaluacion": {
                        "periodo_evaluado_dias": 0,
                        "mae_promedio_movil": None,
                        "mae_ingenuo": None,
                        "mejor_modelo": "Historial insuficiente"
                    },
                    "historico_reciente": {"fechas": [], "valores": []},
                    "pronostico_7d": {"fechas": [], "valores": []}
                })
                continue

            # Período de registro conocido [d_min, d_max] para este producto
            fechas_ordenadas = sorted(ventas_dict.keys())
            d_min = fechas_ordenadas[0]
            d_max = fechas_ordenadas[-1]
            total_dias_rango = (d_max - d_min).days + 1

            if total_dias_rango < 14:
                # Menos de 14 días en el período conocido: marcar historial insuficiente
                resultados_productos.append({
                    "id_producto": p_id,
                    "sku": p_info["sku"],
                    "nombre_producto": p_info["nombre"],
                    "categoria": p_info["categoria"],
                    "disponible": p_info["stock_actual"],
                    "lead_time_dias": lead_time_config or p_info["lead_time_dias"],
                    "reserva_seguridad": stock_seguridad_config if stock_seguridad_config is not None else p_info["stock_seguridad"],
                    "demanda_plazo": 0,
                    "necesidad": stock_seguridad_config if stock_seguridad_config is not None else p_info["stock_seguridad"],
                    "pendientes_recibir": p_info["pedidos_pendientes"],
                    "posicion_inventario": p_info["stock_actual"] + p_info["pedidos_pendientes"],
                    "faltante_cobertura": max(0, (stock_seguridad_config if stock_seguridad_config is not None else p_info["stock_seguridad"]) - (p_info["stock_actual"] + p_info["pedidos_pendientes"])),
                    "estado": "Historial insuficiente",
                    "mensaje_estado": f"Historial insuficiente ({total_dias_rango} días; se requieren ≥ 14)",
                    "ventas_previstas_7d": 0,
                    "demanda_diaria_media": 0.0,
                    "evaluacion": {
                        "periodo_evaluado_dias": 0,
                        "mae_promedio_movil": None,
                        "mae_ingenuo": None,
                        "mejor_modelo": "Historial insuficiente"
                    },
                    "historico_reciente": {"fechas": [], "valores": []},
                    "pronostico_7d": {"fechas": [], "valores": []}
                })
                continue

            # Completar días sin ventas con 0 ÚNICAMENTE dentro de [d_min, d_max]
            # No se asume demanda cero fuera de este período de registro.
            fechas_completas = []
            pares_completos = []
            for offset in range(total_dias_rango):
                dia_actual = d_min + timedelta(days=offset)
                fechas_completas.append(dia_actual)
                pares_completos.append(float(ventas_dict.get(dia_actual, 0.0)))

            serie = np.array(pares_completos, dtype=float)
            n_total = len(serie)

            # Partición cronológica estricta: 80% train, 20% test (mínimo 7 días de test)
            n_train = max(7, int(n_total * 0.8))
            train = serie[:n_train]
            test = serie[n_train:]
            n_test = len(test)

            # 1. Modelo de referencia: Pronóstico Ingenuo (Lag-1) sobre el conjunto de test
            # y_hat_t = y_{t-1}
            preds_naive = np.zeros(n_test)
            preds_naive[0] = train[-1]
            preds_naive[1:] = test[:-1]
            mae_naive = float(np.mean(np.abs(test - preds_naive)))

            # 2. Modelo Principal: Promedio Móvil (7 días)
            # Evaluado paso a paso con los 7 valores precedentes reales
            serie_para_eval = np.concatenate([train[-7:], test])
            preds_ma7 = []
            for i in range(n_test):
                ventana = serie_para_eval[i:i+7]
                preds_ma7.append(float(np.mean(ventana)))
            preds_ma7 = np.array(preds_ma7)
            mae_ma7 = float(np.mean(np.abs(test - preds_ma7)))

            mejor_modelo = "Promedio Móvil (7D)" if mae_ma7 <= mae_naive else "Pronóstico Ingenuo (Lag-1)"
            mae_ganador = min(mae_ma7, mae_naive)
            maes_ma7_acum.append(mae_ma7)
            maes_naive_acum.append(mae_naive)

            # 3. Pronóstico de los próximos 7 días a partir de la última ventana disponible
            ventana_futura = serie[-7:].tolist()
            proyeccion_7d = []
            fechas_horizonte_7d = []
            base_date = d_max
            for step in range(1, 8):
                fecha_fut = base_date + timedelta(days=step)
                fechas_horizonte_7d.append(fecha_fut.strftime("%d/%m"))
                prox_val = max(0.0, float(np.mean(ventana_futura[-7:])))
                proyeccion_7d.append(round(prox_val, 1))
                ventana_futura.append(prox_val)

            total_semana_7d = int(round(sum(proyeccion_7d)))
            demanda_diaria_media = float(np.mean(proyeccion_7d))

            # Parámetros operativos (con soporte a edición interactiva)
            plazo_prod = lead_time_config if (lead_time_config is not None and lead_time_config > 0) else p_info["lead_time_dias"]
            reserva_prod = stock_seguridad_config if (stock_seguridad_config is not None and stock_seguridad_config >= 0) else p_info["stock_seguridad"]
            disponible_prod = p_info["stock_actual"]
            pendientes_prod = p_info["pedidos_pendientes"]

            lead_times_usados.append(plazo_prod)

            # 4. Cálculo de reposición unificado por producto:
            # - Demanda en plazo = suma de ventas pronosticadas durante su plazo de entrega
            demanda_en_plazo = int(round(demanda_diaria_media * plazo_prod))
            # - Umbral de reposición (necesidad) = Demanda en plazo + Reserva de seguridad
            umbral_reposicion = demanda_en_plazo + reserva_prod
            necesidad = umbral_reposicion
            # - Posición de inventario = Stock disponible + Entradas pendientes confirmadas
            posicion_inventario = disponible_prod + pendientes_prod
            # - Faltante de cobertura = máx(0, Umbral - Posición de inventario)
            faltante_cobertura = max(0, umbral_reposicion - posicion_inventario)
            estado_cobertura = "Bajo cobertura" if faltante_cobertura > 0 else "Normal"

            total_ventas_previstas_7d += total_semana_7d
            total_pares_por_reponer += faltante_cobertura
            if faltante_cobertura > 0:
                total_prods_por_reponer += 1

            # Historial reciente: últimos 21 días conocidos para el gráfico
            n_reciente = min(21, n_total)
            fechas_recientes_str = [f.strftime("%d/%m") for f in fechas_completas[-n_reciente:]]
            valores_recientes = [int(round(v)) for v in serie[-n_reciente:]]

            resultados_productos.append({
                "id_producto": p_id,
                "sku": p_info["sku"],
                "nombre_producto": p_info["nombre"],
                "categoria": p_info["categoria"],
                "disponible": disponible_prod,
                "lead_time_dias": plazo_prod,
                "reserva_seguridad": reserva_prod,
                "demanda_plazo": demanda_en_plazo,
                "necesidad": necesidad,
                "pendientes_recibir": pendientes_prod,
                "posicion_inventario": posicion_inventario,
                "faltante_cobertura": faltante_cobertura,
                "estado": estado_cobertura,
                "ventas_previstas_7d": total_semana_7d,
                "demanda_diaria_media": round(demanda_diaria_media, 2),
                # Compatibilidad hacia atrás de nombres anteriores
                "stock_actual": disponible_prod,
                "stock_seguridad": reserva_prod,
                "demanda_lead_time_estimada": demanda_en_plazo,
                "punto_reorden": umbral_reposicion,
                "sugerencia_reposicion_pares": faltante_cobertura,
                "alerta_stock": faltante_cobertura > 0,
                "evaluacion": {
                    "periodo_evaluado_dias": n_test,
                    "mae_promedio_movil": round(mae_ma7, 2),
                    "mae_ingenuo": round(mae_naive, 2),
                    "mejor_modelo": mejor_modelo,
                    "mae_ganador_pares": round(mae_ganador, 2),
                    "unidad": "pares/día",
                    "nivel_agregacion": "Por SKU",
                    "metodo": "Promedio Móvil 7D vs Ingenuo Lag-1",
                    "aviso_mejora": "Sumar datos reales no garantiza mejorar la precisión si la varianza del mercado aumenta."
                },
                "historico_reciente": {
                    "fechas": fechas_recientes_str,
                    "valores": valores_recientes
                },
                "pronostico_7d": {
                    "fechas": fechas_horizonte_7d,
                    "valores_diarios_pares": proyeccion_7d,
                    "total_semana_pares": total_semana_7d
                }
            })

        # Plazo común o "Según producto"
        if lead_times_usados and len(set(lead_times_usados)) == 1:
            plazo_comun_txt = f"{lead_times_usados[0]} días"
        else:
            plazo_comun_txt = "Según producto"

        mae_prom_general = round(float(np.mean(maes_ma7_acum)), 2) if maes_ma7_acum else 0.0
        mae_naive_general = round(float(np.mean(maes_naive_acum)), 2) if maes_naive_acum else 0.0

        totales_resumen = {
            "total_ventas_previstas_7d": total_ventas_previstas_7d,
            "pares_por_reponer": total_pares_por_reponer,
            "productos_por_reponer": total_prods_por_reponer,
            "plazo_comun": plazo_comun_txt,
            "mae_promedio_general": mae_prom_general,
            "mae_naive_general": mae_naive_general,
            "total_sugerencia_reposicion": total_pares_por_reponer  # retrocompatibilidad
        }

        # Respuesta con dualidad raíz y 'datos' para máxima robustez
        return {
            "exito": True,
            "totales_resumen": totales_resumen,
            "fuente_datos": fuente_datos,
            "productos": resultados_productos,
            "datos": {
                "kpis": {
                    "total_ventas_previstas_7d": total_ventas_previstas_7d,
                    "pares_por_reponer": total_pares_por_reponer,
                    "productos_por_reponer": total_prods_por_reponer,
                    "plazo_comun": plazo_comun_txt,
                    "mae_promedio_general": mae_prom_general,
                    "mae_naive_general": mae_naive_general,
                    "sugerencia_reposicion_total": total_pares_por_reponer
                },
                "fuente_datos": fuente_datos,
                "productos": resultados_productos
            },
            "aviso_metodologico": "Evaluación con partición temporal out-of-sample sin fuga de información. El faltante de cobertura es una recomendación preventiva y no realiza órdenes de compra ni altera el stock automáticamente."
        }

    finally:
        conn.close()

