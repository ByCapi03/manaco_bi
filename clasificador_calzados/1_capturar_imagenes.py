"""
1_capturar_imagenes.py
PASO 1: Captura de imágenes con cámara para armar el dataset de calzados Manaco.

Controles:
  0..3     -> Seleccionar clase:
              0: sin_calzado (fondo vacío, manos, objetos)
              1: calzado_deportivo (zapatillas/sneakers)
              2: calzado_casual (calzado casual/botines de cuero)
              3: calzado_formal (zapatos formales de vestir)
  ESPACIO  -> Iniciar/Pausar captura continua (~5 fotos por segundo)
  g        -> Guardar UNA foto individual
  q / ESC  -> Salir del capturador
"""

import os
import time
import cv2
import numpy as np

from config import CLASES, NOMBRES_CLASES, CARPETA_DATASET, CAMARA, recortar_cuadrado, COLORES_BGR

# Crear directorios para cada clase si no existen
for c in CLASES:
    os.makedirs(os.path.join(CARPETA_DATASET, c), exist_ok=True)

# Conteo en caché para no consultar el disco en cada frame
conteos = {c: len(os.listdir(os.path.join(CARPETA_DATASET, c))) for c in CLASES}


def actualizar_conteo(clase):
    conteos[clase] = len(os.listdir(os.path.join(CARPETA_DATASET, clase)))


def guardar_muestra(imagen, clase):
    nombre = f"{int(time.time() * 1000)}.jpg"
    ruta = os.path.join(CARPETA_DATASET, clase, nombre)
    cv2.imwrite(ruta, cv2.resize(imagen, (300, 300)))
    conteos[clase] += 1


def dibujar_panel_transparente(img, x1, y1, x2, y2, color=(15, 23, 42), alpha=0.82):
    """Dibuja un rectángulo semi-transparente estilo Dark Glassmorphism Manaco."""
    sub_img = img[y1:y2, x1:x2]
    rect = np.full(sub_img.shape, color, dtype=np.uint8)
    img[y1:y2, x1:x2] = cv2.addWeighted(rect, alpha, sub_img, 1.0 - alpha, 0)


def dibujar_mira_enfoque(img, x1, y1, x2, y2, color, longitud=32, grosor=2):
    """Dibuja esquinas tecnológicas de enfoque estilo escáner industrial Manaco."""
    # Superior Izquierda
    cv2.line(img, (x1, y1), (x1 + longitud, y1), color, grosor)
    cv2.line(img, (x1, y1), (x1, y1 + longitud), color, grosor)
    # Superior Derecha
    cv2.line(img, (x2, y1), (x2 - longitud, y1), color, grosor)
    cv2.line(img, (x2, y1), (x2, y1 + longitud), color, grosor)
    # Inferior Izquierda
    cv2.line(img, (x1, y2), (x1 + longitud, y2), color, grosor)
    cv2.line(img, (x1, y2), (x1, y2 - longitud), color, grosor)
    # Inferior Derecha
    cv2.line(img, (x2, y2), (x2 - longitud, y2), color, grosor)
    cv2.line(img, (x2, y2), (x2, y2 - longitud), color, grosor)


def main():
    print("=" * 65)
    print("👟 CAPTURADOR DE DATASET - CALZADOS MANACO")
    print(f"Abriendo camara indice: {CAMARA}")
    print("Teclas: 0..3 (Clase) | ESPACIO (Rafaga) | 'g' (1 Foto) | 'q' (Salir)")
    print("=" * 65)

    camara = cv2.VideoCapture(CAMARA)
    if not camara.isOpened():
        raise SystemExit(f"No se pudo acceder a la camara {CAMARA}. Ajusta CAMARA en config.py")

    clase_actual = 1  # Inicia por defecto en calzado_deportivo
    captura_continua = False
    ultimo_guardado = 0.0
    intervalo_guardado = 0.20  # 5 capturas/seg en modo ráfaga

    cv2.namedWindow("MANACO - Captura de Muestras", cv2.WINDOW_AUTOSIZE)

    while True:
        ret, frame = camara.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)  # Modo espejo
        alto, ancho = frame.shape[:2]

        # Región central cuadrada para el zapato
        lado = int(min(alto, ancho) * 0.70)
        x1 = (ancho - lado) // 2
        y1 = (alto - lado) // 2
        x2 = x1 + lado
        y2 = y1 + lado

        cuadro = frame[y1:y2, x1:x2]

        # Guardar en ráfaga
        ahora = time.time()
        if captura_continua and (ahora - ultimo_guardado) >= intervalo_guardado:
            guardar_muestra(cuadro, CLASES[clase_actual])
            ultimo_guardado = ahora

        # --- DIBUJAR INTERFAZ HUD ---
        # 1. Cabecera superior
        dibujar_panel_transparente(frame, 15, 12, ancho - 15, 75, color=(15, 23, 42), alpha=0.85)
        cv2.putText(frame, "MANACO AI VISION - ENTRENAMIENTO", (28, 38),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (240, 240, 250), 1, cv2.LINE_AA)
        cv2.putText(frame, "Posicione el calzado en el cuadro central y rote suavemente", (28, 62),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 175, 200), 1, cv2.LINE_AA)

        # 2. Mira de enfoque central
        nombre_c = CLASES[clase_actual]
        color_c = COLORES_BGR.get(nombre_c, (0, 255, 255))
        dibujar_mira_enfoque(frame, x1, y1, x2, y2, color_c, longitud=35, grosor=2)

        # 3. Panel de estado inferior
        dibujar_panel_transparente(frame, 15, alto - 120, ancho - 15, alto - 15, color=(15, 23, 42), alpha=0.85)

        # Estado de captura
        if captura_continua:
            cv2.circle(frame, (35, alto - 85), 7, (0, 0, 255), -1)
            cv2.putText(frame, "GRABANDO RAFAGA (ESPACIO para pausar)", (52, alto - 80),
                        cv2.FONT_HERSHEY_DUPLEX, 0.50, (80, 80, 255), 1, cv2.LINE_AA)
        else:
            cv2.circle(frame, (35, alto - 85), 7, (0, 220, 100), -1)
            cv2.putText(frame, "LISTO (ESPACIO: rafaga | 'g': 1 foto)", (52, alto - 80),
                        cv2.FONT_HERSHEY_DUPLEX, 0.50, (180, 230, 180), 1, cv2.LINE_AA)

        # Clases y contadores
        offset_x = 28
        for idx, cl in enumerate(CLASES):
            es_activa = (idx == clase_actual)
            txt = f"[{idx}] {cl.replace('calzado_', '')}: {conteos[cl]}"
            col = color_c if es_activa else (130, 140, 160)
            grosor = 2 if es_activa else 1
            cv2.putText(frame, txt, (offset_x, alto - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, grosor, cv2.LINE_AA)
            offset_x += 140

        cv2.imshow("MANACO - Captura de Muestras", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla in (ord('q'), 27):  # 'q' o ESC
            break
        elif tecla == ord(' '):      # Barra espaciadora
            captura_continua = not captura_continua
        elif tecla == ord('g'):      # Guardar 1 foto
            guardar_muestra(cuadro, CLASES[clase_actual])
        elif ord('0') <= tecla <= ord('3'):
            idx_solicitado = tecla - ord('0')
            if idx_solicitado < len(CLASES):
                clase_actual = idx_solicitado

    camara.release()
    cv2.destroyAllWindows()
    print("\n--- RESUMEN FINAL DEL DATASET ---")
    for cl in CLASES:
        print(f"• {cl}: {conteos[cl]} fotos guardadas")
    print("=" * 65)


if __name__ == "__main__":
    main()
