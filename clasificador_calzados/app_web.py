"""
app_web.py
Servidor Web Flask para el ecosistema MANACO BI & VISIÓN ARTIFICIAL.
Proporciona:
- Dashboard de Business Intelligence (BI) en tiempo real con KPIs y gráficos analíticos.
- Módulo de Escáner y Reconocimiento de Calzados con cámara web (navegador o local) o subida de fotos.
- Integración nativa con PostgreSQL (manaco_dw) y SQLite con fallback automático.
- Simulador de transacciones de inventario y exportador de datos.
"""

import base64
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from flask import Flask, jsonify, render_template, request, Response, send_file

from config import (ARCHIVO_MODELO, ARCHIVO_CLASES, CONFIANZA_MINIMA,
                    FRAMES_PARA_REGISTRAR, FRAMES_PARA_LIBERAR,
                    recortar_cuadrado, preprocesar, CLASES, NOMBRES_CLASES,
                    MAPEO_DB, COLORES_HEX, TASA_CAMBIO_OFICIAL)
from db_manaco import db_manaco
import analisis_comercial as ac

PUERTO = 5000

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

# Cargar modelo TensorFlow y clases
print(f"[MANACO WEB] Cargando red neuronal desde: {ARCHIVO_MODELO}")
modelo = tf.keras.models.load_model(ARCHIVO_MODELO)
with open(ARCHIVO_CLASES, encoding="utf-8") as f:
    clases_modelo = json.load(f)
CLASE_VACIA = clases_modelo[0]

candado_modelo = threading.Lock()


# =====================================================================
# RUTAS DE PÁGINA Y API
# =====================================================================

@app.route("/")
def index():
    """Página principal: Single Page Application (SPA) Manaco BI & Vision."""
    return render_template("index.html")


@app.route("/api/estado", methods=["GET"])
def api_estado():
    """Devuelve inventario actual, KPIs y estado del motor de base de datos."""
    try:
        inv = db_manaco.obtener_inventario()
        kpis = db_manaco.obtener_kpis()
        movimientos = db_manaco.obtener_movimientos(limite=15)
        return jsonify({
            "exito": True,
            "inventario": inv,
            "kpis": kpis,
            "movimientos": movimientos,
            "motor_db": db_manaco.motor.upper(),
            "clases": CLASES,
            "nombres_clases": NOMBRES_CLASES,
            "colores": COLORES_HEX
        })
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/graficos", methods=["GET"])
def api_graficos():
    """Devuelve los conjuntos de datos formateados para Chart.js en el frontend."""
    try:
        datos = db_manaco.obtener_datos_graficos()
        return jsonify({"exito": True, "datos": datos})
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/comercio/opciones", methods=["GET"])
def api_comercio_opciones():
    """Devuelve opciones de filtrado disponibles directamente desde BDatos_MANACO.xlsx."""
    try:
        opciones = ac.obtener_opciones_filtros()
        return jsonify(opciones)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/comercio/metricas", methods=["GET"])
def api_comercio_metricas():
    """Calcula agregaciones y cocientes ponderados directamente desde BDatos_MANACO.xlsx."""
    try:
        flujo = request.args.get("flujo", "Importación")
        anio_str = request.args.get("anio", "2024")
        sa6_str = request.args.get("codigo_sa6", "")
        socio = request.args.get("socio", "")

        anio = int(anio_str) if anio_str and anio_str.isdigit() else None
        sa6 = int(sa6_str) if sa6_str and sa6_str.isdigit() else None

        res = ac.calcular_metricas_comerciales(flujo=flujo, anio=anio, codigo_sa6=sa6, socio=socio)
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/escenarios/calcular", methods=["POST"])
def api_escenarios_calcular():
    """Ejecuta el calculo diferencial Make-or-Buy (Fabricar vs Importar) y fijacion de precios."""
    try:
        datos = request.get_json(silent=True) or {}
        res = ac.calcular_escenario_make_or_buy(datos)

        # Adjuntar precio activo en inventario para comparacion clara
        inv = db_manaco.obtener_inventario()
        sa_str = str(datos.get("codigo_sa6", "640399"))
        item_inv = next((x for x in inv if str(x["codigo_sa6"]) == sa_str), None)
        if item_inv:
            res["precio_activo_inventario"] = {
                "id_producto": item_inv["id_producto"],
                "categoria": item_inv["categoria_corta"],
                "precio_unitario_bs": item_inv["precio_unitario_bs"],
                "precio_unitario_usd": item_inv["precio_unitario_usd"],
                "stock_actual": item_inv["stock_actual"]
            }
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/escenarios/predefinido/<tipo>", methods=["GET"])
def api_escenarios_predefinido(tipo):
    """Devuelve los parametros de uno de los tres escenarios estandarizados y equilibrados."""
    try:
        res = ac.obtener_escenario_predefinido(tipo)
        return jsonify({"exito": True, "parametros": res})
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/inventario/aplicar-precio", methods=["POST"])
def api_inventario_aplicar_precio():
    """Aplica explicitamente el precio propuesto por el escenario al inventario activo."""
    try:
        datos = request.get_json(silent=True) or {}
        id_prod = int(datos.get("id_producto", 0))
        precio_bs = float(datos.get("nuevo_precio_bs", 0.0))
        precio_usd = float(datos.get("nuevo_precio_usd", 0.0))
        responsable = datos.get("responsable", "Gerente Comercial Manaco")

        if id_prod <= 0 or precio_bs <= 0 or precio_usd <= 0:
            return jsonify({"exito": False, "error": "Parametros de precio o ID de producto invalidos"}), 400

        res = db_manaco.actualizar_precio_producto(
            id_producto=id_prod,
            nuevo_precio_bs=precio_bs,
            nuevo_precio_usd=precio_usd,
            responsable=responsable
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/clasificar", methods=["POST"])
def api_clasificar():
    """Recibe un frame JPEG (Base64 o multipart) y retorna las probabilidades de clasificación."""
    try:
        img_bgr = None

        if "imagen" in request.files:
            archivo = request.files["imagen"]
            arr = np.frombuffer(archivo.read(), np.uint8)
            img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif request.is_json:
            datos_json = request.get_json(silent=True) or {}
            b64_str = datos_json.get("imagen", "")
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            if b64_str:
                bytes_img = base64.b64decode(b64_str)
                arr = np.frombuffer(bytes_img, np.uint8)
                img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return jsonify({"exito": False, "error": "No se recibió una imagen válida"}), 400

        # Preprocesar
        cuadro = recortar_cuadrado(img_bgr)
        tensor_in = np.expand_dims(preprocesar(cuadro), 0)

        # Inferencia con candado para evitar colisiones multihilo en TF
        with candado_modelo:
            probabilidades = modelo(tensor_in, training=False).numpy()[0]

        idx_max = int(np.argmax(probabilidades))
        confianza_max = float(probabilidades[idx_max])
        clase_detectada = clases_modelo[idx_max]

        # Desglose de probabilidades por clase
        probabilidades_dict = {}
        for i, c in enumerate(clases_modelo):
            probabilidades_dict[c] = round(float(probabilidades[i]) * 100, 1)

        nombre_amigable = NOMBRES_CLASES.get(clase_detectada, clase_detectada)

        return jsonify({
            "exito": True,
            "clase": clase_detectada,
            "nombre": nombre_amigable,
            "es_calzado": (clase_detectada != CLASE_VACIA),
            "confianza": round(confianza_max, 4),
            "porcentaje": round(confianza_max * 100, 1),
            "probabilidades": probabilidades_dict,
            "color": COLORES_HEX.get(clase_detectada, "#64748b")
        })
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    """Registra un zapato detectado en la base de datos (PostgreSQL/SQLite) y suma +1 al stock."""
    try:
        datos = request.get_json(silent=True) or {}
        clase = datos.get("clase")
        confianza = float(datos.get("confianza", 0.90))
        origen = datos.get("origen", "escaner_web")
        responsable = datos.get("responsable", "Operador Web Manaco")

        if not clase or clase not in MAPEO_DB:
            return jsonify({"exito": False, "error": f"Categoría de calzado inválida: {clase}"}), 400

        res = db_manaco.registrar_calzado_ia(
            clase_nombre=clase,
            confianza=confianza,
            origen=origen,
            responsable=responsable
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/deshacer", methods=["POST"])
def api_deshacer():
    """Revierte la última acción en la base de datos."""
    try:
        res = db_manaco.deshacer_ultimo_registro()
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/reiniciar", methods=["POST"])
def api_reiniciar():
    """Reinicia el inventario a un nivel basal configurado."""
    try:
        datos = request.get_json(silent=True) or {}
        stock_base = int(datos.get("stock_base", 30))
        res = db_manaco.reiniciar_inventario(stock_base=stock_base)
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/simular", methods=["POST"])
def api_simular():
    """Genera N movimientos sintéticos en la base de datos."""
    try:
        datos = request.get_json(silent=True) or {}
        cantidad = int(datos.get("cantidad", 20))
        res = db_manaco.simular_datos(cantidad=cantidad)
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/exportar-csv", methods=["GET"])
def api_exportar_csv():
    """Exporta el historial de movimientos de inventario en formato CSV descargable."""
    try:
        movs = db_manaco.obtener_movimientos(limite=500)
        lineas = ["id_registro,fecha_hora,id_producto,categoria,accion,cantidad,confianza,origen,responsable\n"]
        for m in movs:
            lineas.append(f"{m['id_registro']},{m['fecha_hora']},{m['id_producto']},\"{m['categoria']}\",{m['accion']},{m['cantidad']},{m['confianza']},\"{m['origen']}\",\"{m['responsable']}\"\n")
        
        csv_data = "".join(lineas)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=manaco_movimientos_inventario.csv"}
        )
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 65)
    print("[MANACO] BI & VISION ARTIFICIAL - SERVIDOR WEB INICIADO")
    print(f"* URL Local:        http://localhost:{PUERTO}")
    print(f"* Motor Base Datos: {db_manaco.motor.upper()}")
    print("=" * 65)
    app.run(host="0.0.0.0", port=PUERTO, debug=False, threaded=True)
