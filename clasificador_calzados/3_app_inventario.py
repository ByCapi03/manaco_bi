"""
3_app_inventario.py
PASO 3: App de Inventario en Tiempo Real con Visión Artificial para Manaco.
Ejecuta la cámara con OpenCV, clasifica calzados en tiempo real con TensorFlow,
y suma automáticamente al inventario en la Base de Datos (PostgreSQL/SQLite) con feedback visual y sonoro.

Controles:
  ESPACIO  -> Contar el siguiente calzado sin retirar el actual
  z        -> Deshacer el último registro
  r        -> Reiniciar inventario a valores base
  s        -> Simular 5 movimientos de prueba
  q / ESC  -> Salir de la aplicación
"""

import json
import os
import sys
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np
import tensorflow as tf

from config import (ARCHIVO_MODELO, ARCHIVO_CLASES, CAMARA, CONFIANZA_MINIMA,
                    FRAMES_PARA_REGISTRAR, FRAMES_PARA_LIBERAR,
                    recortar_cuadrado, preprocesar, COLORES_BGR, NOMBRES_CLASES)
from db_manaco import db_manaco

try:
    import winsound
except ImportError:
    winsound = None


def reproducir_beep(exito=True):
    if winsound:
        try:
            if exito:
                winsound.Beep(1400, 160)
            else:
                winsound.Beep(600, 250)
        except Exception:
            pass


def dibujar_panel_transparente(img, x1, y1, x2, y2, color=(15, 23, 42), alpha=0.82):
    """Superpone un rectángulo translúcido para lograr estética Dark Glassmorphism Manaco."""
    sub_img = img[y1:y2, x1:x2]
    rect = np.full(sub_img.shape, color, dtype=np.uint8)
    img[y1:y2, x1:x2] = cv2.addWeighted(rect, alpha, sub_img, 1.0 - alpha, 0)


def dibujar_esquinas_guia(img, x1, y1, x2, y2, color, longitud=30, grosor=2):
    """Dibuja esquinas de enfoque tecnológico en el área de escaneo."""
    cv2.line(img, (x1, y1), (x1 + longitud, y1), color, grosor)
    cv2.line(img, (x1, y1), (x1, y1 + longitud), color, grosor)
    cv2.line(img, (x2, y1), (x2 - longitud, y1), color, grosor)
    cv2.line(img, (x2, y1), (x2, y1 + longitud), color, grosor)
    cv2.line(img, (x1, y2), (x1 + longitud, y2), color, grosor)
    cv2.line(img, (x1, y2), (x1, y2 - longitud), color, grosor)
    cv2.line(img, (x2, y2), (x2 - longitud, y2), color, grosor)
    cv2.line(img, (x2, y2), (x2, y2 - longitud), color, grosor)


def main():
    print("=" * 65)
    print("[MANACO] SISTEMA DE INVENTARIO IA - MANACO CALZADOS")
    print(f"Cargando modelo desde: {ARCHIVO_MODELO}")
    print(f"Motor de Base de Datos: {db_manaco.motor.upper()}")
    print("=" * 65)

    if not os.path.exists(ARCHIVO_MODELO) or not os.path.exists(ARCHIVO_CLASES):
        print("[!] Error: No se encontró el modelo o clases. Ejecuta primero 2_entrenar_modelo.py")
        sys.exit(1)

    modelo = tf.keras.models.load_model(ARCHIVO_MODELO)
    with open(ARCHIVO_CLASES, encoding="utf-8") as f:
        clases = json.load(f)
    CLASE_VACIA = clases[0]  # "sin_calzado"

    camara = cv2.VideoCapture(CAMARA)
    if not camara.isOpened():
        raise SystemExit(f"No se pudo abrir la cámara {CAMARA}. Revisa CAMARA en config.py")

    # Dimensiones de la interfaz
    ANCHO_CAM = 640
    ALTO_CAM = 640
    ANCHO_PANEL = 380
    ANCHO_TOTAL = ANCHO_CAM + ANCHO_PANEL
    ALTO_TOTAL = ALTO_CAM

    # Paleta de colores BGR
    COLOR_FONDO_PANEL = (15, 23, 42)
    COLOR_CARD = (25, 35, 60)
    COLOR_BORDE = (45, 60, 95)
    COLOR_TEXTO_BLANCO = (245, 245, 250)
    COLOR_TEXTO_MUTED = (160, 175, 200)
    COLOR_ROJO_MANACO = (60, 40, 225)
    COLOR_CYAN = (245, 160, 30)
    COLOR_AMBAR = (50, 180, 240)

    # Estado del reconocedor
    ultimas = deque(maxlen=max(FRAMES_PARA_REGISTRAR, FRAMES_PARA_LIBERAR))
    bloqueado = False
    mensaje_notif = ""
    frames_mensaje = 0
    color_mensaje = (80, 240, 120)
    ultimo_registro_texto = "Ninguno aun"

    cv2.namedWindow("MANACO - Control de Inventario IA", cv2.WINDOW_AUTOSIZE)

    while True:
        ret, frame = camara.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)  # Efecto espejo
        frame_cuadrado = recortar_cuadrado(frame)
        frame_camara = cv2.resize(frame_cuadrado, (ANCHO_CAM, ALTO_CAM))

        # Región de escaneo (cuadro central)
        margen = 80
        x1_roi, y1_roi = margen, margen
        x2_roi, y2_roi = ANCHO_CAM - margen, ALTO_CAM - margen
        roi_calzado = frame_camara[y1_roi:y2_roi, x1_roi:x2_roi]

        # Inferencia con la CNN
        entrada = np.expand_dims(preprocesar(roi_calzado), 0)
        probabilidades = modelo(entrada, training=False).numpy()[0]
        indice_pred = int(np.argmax(probabilidades))
        confianza_pred = float(probabilidades[indice_pred])
        clase_pred = clases[indice_pred]

        # Lógica de registro por persistencia temporal (cola de frames)
        if confianza_pred >= CONFIANZA_MINIMA:
            ultimas.append(clase_pred)
        else:
            ultimas.append("desconocido")

        # Registro automático cuando se mantiene la misma clase por N frames
        n_mismo = sum(1 for c in list(ultimas)[-FRAMES_PARA_REGISTRAR:] if c == clase_pred)
        if (not bloqueado and clase_pred != CLASE_VACIA and
                confianza_pred >= CONFIANZA_MINIMA and n_mismo >= FRAMES_PARA_REGISTRAR):
            # Guardar en la Base de Datos
            res = db_manaco.registrar_calzado_ia(
                clase_nombre=clase_pred,
                confianza=confianza_pred,
                origen="camara_escritorio",
                responsable="Operador Planta"
            )
            if res.get("exito"):
                bloqueado = True
                reproducir_beep(True)
                nombre_amigable = NOMBRES_CLASES.get(clase_pred, clase_pred)
                mensaje_notif = f"+1 {nombre_amigable.split('(')[0].strip()}"
                color_mensaje = (80, 240, 120)
                frames_mensaje = 40
                ultimo_registro_texto = f"{datetime.now():%H:%M:%S} - {nombre_amigable[:22]}"
            else:
                mensaje_notif = "Error al registrar en DB"
                color_mensaje = (80, 80, 240)
                frames_mensaje = 30

        # Desbloquear cuando se detecta vacío de forma sostenida
        if bloqueado:
            n_vacio = sum(1 for c in list(ultimas)[-FRAMES_PARA_LIBERAR:] if c == CLASE_VACIA)
            if n_vacio >= FRAMES_PARA_LIBERAR:
                bloqueado = False

        # --- CONSTRUCCIÓN DEL LIENZO HUD ---
        lienzo = np.zeros((ALTO_TOTAL, ANCHO_TOTAL, 3), dtype=np.uint8)
        lienzo[:ALTO_CAM, :ANCHO_CAM] = frame_camara

        # Color de la mira según la predicción
        color_deteccion = COLORES_BGR.get(clase_pred, (180, 180, 180))
        if clase_pred == CLASE_VACIA:
            color_deteccion = (120, 120, 130)

        # Dibujar mira de enfoque
        grosor_mira = 3 if bloqueado else 2
        dibujar_esquinas_guia(lienzo, x1_roi, y1_roi, x2_roi, y2_roi, color_deteccion, longitud=40, grosor=grosor_mira)

        # Etiqueta flotante sobre el zapato
        if clase_pred != CLASE_VACIA:
            texto_tag = f"{clase_pred.replace('calzado_', '').upper()} ({confianza_pred * 100:.1f}%)"
            (ancho_t, alto_t), _ = cv2.getTextSize(texto_tag, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
            cv2.rectangle(lienzo, (x1_roi, y1_roi - alto_t - 14), (x1_roi + ancho_t + 16, y1_roi), (15, 23, 42), -1)
            cv2.rectangle(lienzo, (x1_roi, y1_roi - alto_t - 14), (x1_roi + ancho_t + 16, y1_roi), color_deteccion, 1)
            cv2.putText(lienzo, texto_tag, (x1_roi + 8, y1_roi - 6), cv2.FONT_HERSHEY_DUPLEX, 0.55, color_deteccion, 1, cv2.LINE_AA)

        # Notificación emergente temporal en pantalla
        if frames_mensaje > 0:
            frames_mensaje -= 1
            dibujar_panel_transparente(lienzo, 40, ALTO_CAM - 90, ANCHO_CAM - 40, ALTO_CAM - 30, (15, 23, 42), 0.88)
            cv2.putText(lienzo, mensaje_notif, (60, ALTO_CAM - 52), cv2.FONT_HERSHEY_DUPLEX, 0.75, color_mensaje, 2, cv2.LINE_AA)

        # --- PANEL LATERAL DERECHO (CONTROL DE INVENTARIO BI) ---
        panel_x = ANCHO_CAM
        cv2.rectangle(lienzo, (panel_x, 0), (ANCHO_TOTAL, ALTO_TOTAL), COLOR_FONDO_PANEL, -1)
        cv2.line(lienzo, (panel_x, 0), (panel_x, ALTO_TOTAL), COLOR_BORDE, 2)

        # 1. Cabecera Manaco
        dibujar_panel_transparente(lienzo, panel_x + 15, 15, ANCHO_TOTAL - 15, 85, COLOR_CARD, 0.90)
        cv2.putText(lienzo, "MANACO BI & VISION", (panel_x + 25, 45), cv2.FONT_HERSHEY_DUPLEX, 0.70, COLOR_TEXTO_BLANCO, 1, cv2.LINE_AA)
        cv2.putText(lienzo, f"DB: {db_manaco.motor.upper()} | EN LINEA", (panel_x + 25, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (80, 230, 140), 1, cv2.LINE_AA)

        # 2. Stock en Vivo por Categoría
        cv2.putText(lienzo, "INVENTARIO EN TIEMPO REAL", (panel_x + 20, 115), cv2.FONT_HERSHEY_DUPLEX, 0.48, COLOR_TEXTO_MUTED, 1, cv2.LINE_AA)

        inventario_db = db_manaco.obtener_inventario()
        y_tarjeta = 130
        for item in inventario_db:
            id_p = item["id_producto"]
            cat_nom = item["categoria_corta"]
            stock = item["stock_actual"]
            stock_min = item["stock_minimo"]
            precio_bs = item["precio_unitario_bs"]

            # Color según ID
            col_id = COLOR_CYAN if id_p == 1 else (COLOR_AMBAR if id_p == 2 else COLOR_ROJO_MANACO)

            # Tarjeta de producto
            dibujar_panel_transparente(lienzo, panel_x + 15, y_tarjeta, ANCHO_TOTAL - 15, y_tarjeta + 72, COLOR_CARD, 0.85)
            cv2.rectangle(lienzo, (panel_x + 15, y_tarjeta), (panel_x + 20, y_tarjeta + 72), col_id, -1)

            cv2.putText(lienzo, cat_nom, (panel_x + 28, y_tarjeta + 26), cv2.FONT_HERSHEY_DUPLEX, 0.50, COLOR_TEXTO_BLANCO, 1, cv2.LINE_AA)
            cv2.putText(lienzo, f"Stock: {stock} pares (Min: {stock_min})", (panel_x + 28, y_tarjeta + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXTO_MUTED, 1, cv2.LINE_AA)
            cv2.putText(lienzo, f"Bs. {precio_bs:.2f}", (ANCHO_TOTAL - 100, y_tarjeta + 26), cv2.FONT_HERSHEY_DUPLEX, 0.48, col_id, 1, cv2.LINE_AA)

            # Alerta visual si está por debajo del stock mínimo
            if stock <= stock_min:
                cv2.putText(lienzo, "! REORDEN", (ANCHO_TOTAL - 100, y_tarjeta + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (80, 80, 240), 1, cv2.LINE_AA)

            y_tarjeta += 84

        # 3. KPIs rápidos
        kpis = db_manaco.obtener_kpis()
        dibujar_panel_transparente(lienzo, panel_x + 15, y_tarjeta + 10, ANCHO_TOTAL - 15, y_tarjeta + 90, COLOR_CARD, 0.85)
        cv2.putText(lienzo, "VALORIZACION ALMACEN", (panel_x + 25, y_tarjeta + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXTO_MUTED, 1, cv2.LINE_AA)
        cv2.putText(lienzo, f"Bs. {kpis['total_valor_bs']}", (panel_x + 25, y_tarjeta + 58), cv2.FONT_HERSHEY_DUPLEX, 0.65, (80, 240, 160), 1, cv2.LINE_AA)
        cv2.putText(lienzo, f"$us. {kpis['total_valor_usd']}", (ANCHO_TOTAL - 120, y_tarjeta + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_TEXTO_MUTED, 1, cv2.LINE_AA)

        # 4. Último Registro
        dibujar_panel_transparente(lienzo, panel_x + 15, y_tarjeta + 105, ANCHO_TOTAL - 15, y_tarjeta + 160, COLOR_CARD, 0.85)
        cv2.putText(lienzo, "ULTIMA ENTRADA IA", (panel_x + 25, y_tarjeta + 125), cv2.FONT_HERSHEY_SIMPLEX, 0.40, COLOR_TEXTO_MUTED, 1, cv2.LINE_AA)
        cv2.putText(lienzo, ultimo_registro_texto, (panel_x + 25, y_tarjeta + 148), cv2.FONT_HERSHEY_DUPLEX, 0.44, COLOR_TEXTO_BLANCO, 1, cv2.LINE_AA)

        # 5. Atajos de teclado en el fondo
        y_pie = ALTO_TOTAL - 45
        cv2.putText(lienzo, "[ESPACIO] Sig | [Z] Deshacer | [R] Reset | [Q] Salir",
                    (panel_x + 20, y_pie), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 135, 160), 1, cv2.LINE_AA)

        cv2.imshow("MANACO - Control de Inventario IA", lienzo)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla in (ord('q'), 27):  # 'q' o ESC
            break
        elif tecla == ord(' '):      # Forzar registro inmediato
            if clase_pred != CLASE_VACIA:
                res = db_manaco.registrar_calzado_ia(clase_pred, confianza_pred, origen="manual_espacio")
                if res.get("exito"):
                    reproducir_beep(True)
                    mensaje_notif = f"+1 {clase_pred.replace('calzado_', '').upper()}"
                    frames_mensaje = 30
                    ultimo_registro_texto = f"{datetime.now():%H:%M:%S} - {clase_pred}"
        elif tecla == ord('z'):      # Deshacer
            res = db_manaco.deshacer_ultimo_registro()
            reproducir_beep(False)
            mensaje_notif = res.get("mensaje", "Deshecho")
            frames_mensaje = 35
        elif tecla == ord('r'):      # Reiniciar
            db_manaco.reiniciar_inventario()
            reproducir_beep(False)
            mensaje_notif = "Inventario Reiniciado"
            frames_mensaje = 35
        elif tecla == ord('s'):      # Simular movimientos
            db_manaco.simular_datos(5)
            mensaje_notif = "+5 Movimientos Simulados"
            frames_mensaje = 35

    camara.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
