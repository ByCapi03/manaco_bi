"""
2_entrenar_modelo.py
PASO 2: Entrenar el modelo de clasificación de calzados Manaco con TensorFlow/Keras.
Aplica aumento de datos (Data Augmentation) dentro del modelo y guarda 'modelo_calzados.keras' y 'clases.json'.
Puede ejecutarse directamente: python 2_entrenar_modelo.py o desde 2_entrenar_modelo.ipynb
"""

import json
import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping

from config import (ARCHIVO_CLASES, ARCHIVO_MODELO, CARPETA_DATASET, CLASES,
                    TAMANO_IMG, preprocesar)


def construir_modelo(num_clases):
    """Define la arquitectura convolucional profunda con Data Augmentation integrado."""
    aumento_datos = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.10),
        tf.keras.layers.RandomTranslation(0.15, 0.15),
        tf.keras.layers.RandomZoom((-0.2, 0.2)),
        tf.keras.layers.RandomContrast(0.2),
        tf.keras.layers.RandomBrightness(0.2, value_range=(0, 1)),
    ], name="aumento_calzado")

    modelo = tf.keras.models.Sequential([
        tf.keras.layers.Input(shape=(TAMANO_IMG, TAMANO_IMG, 3)),
        aumento_datos,
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2, 2),

        tf.keras.layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2, 2),

        tf.keras.layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2, 2),

        tf.keras.layers.Dropout(0.4),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(256, activation='relu'),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(num_clases, activation='softmax')
    ], name="manaco_shoe_cnn")

    modelo.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return modelo


def generar_dataset_base_si_vacio():
    """Si el dataset esta vacio, crea muestras iniciales para permitir pruebas inmediatas del sistema."""
    total_imgs = sum(len(os.listdir(os.path.join(CARPETA_DATASET, c))) for c in CLASES if os.path.exists(os.path.join(CARPETA_DATASET, c)))
    if total_imgs >= 20:
        return

    print("[AVISO] Dataset con pocas imagenes. Generando conjunto base sintético para pruebas inmediatas...")
    # Colores representativos de cada tipo de zapato:
    # 0: sin_calzado (fondo neutro beige/gris)
    # 1: calzado_deportivo (blanco/azul/neon)
    # 2: calzado_casual (marron/tierra/cuero)
    # 3: calzado_formal (negro brillante/charol)
    paletas = {
        "sin_calzado": [(210, 205, 195), (180, 180, 180), (220, 220, 220)],
        "calzado_deportivo": [(240, 60, 40), (30, 180, 230), (240, 240, 240)],
        "calzado_casual": [(40, 80, 140), (30, 60, 100), (70, 110, 160)],
        "calzado_formal": [(25, 25, 25), (40, 35, 30), (15, 15, 18)]
    }

    rng = np.random.default_rng(42)
    for clase, colores in paletas.items():
        dir_c = os.path.join(CARPETA_DATASET, clase)
        os.makedirs(dir_c, exist_ok=True)
        for i in range(15):
            base_col = colores[i % len(colores)]
            img = np.ones((TAMANO_IMG, TAMANO_IMG, 3), dtype=np.uint8) * np.array(base_col, dtype=np.uint8)
            # Agregar textura y ruido
            ruido = rng.integers(-25, 25, (TAMANO_IMG, TAMANO_IMG, 3))
            img = np.clip(img.astype(np.int32) + ruido, 0, 255).astype(np.uint8)
            # Agregar formas simuladas si es calzado
            if clase != "sin_calzado":
                cv2.ellipse(img, (TAMANO_IMG//2, TAMANO_IMG//2), (35, 18), 20, 0, 360, (200, 200, 200), -1)
            cv2.imwrite(os.path.join(dir_c, f"base_{i:03d}.jpg"), img)


def main():
    print("=" * 60)
    print("--- PASO 2: Entrenando modelo clasificador de calzados Manaco ---")
    print(f"Clases objetivo ({len(CLASES)}): {CLASES}")
    print("=" * 60)

    for c in CLASES:
        os.makedirs(os.path.join(CARPETA_DATASET, c), exist_ok=True)

    generar_dataset_base_si_vacio()

    # 1. Cargar imágenes
    X = []
    y = []
    print("\nCargando y preprocesando dataset...")
    for idx, c in enumerate(CLASES):
        carpeta = os.path.join(CARPETA_DATASET, c)
        archivos = [f for f in os.listdir(carpeta) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        print(f" -> {c}: {len(archivos)} imagenes")
        for arc in archivos:
            ruta = os.path.join(carpeta, arc)
            img = cv2.imread(ruta)
            if img is None:
                continue
            X.append(preprocesar(img))
            y.append(idx)

    assert len(X) > 0, f"No hay imagenes en {CARPETA_DATASET}"
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int32)
    print(f"\nTotal muestras cargadas: {len(X)} | Forma del tensor: {X.shape}")

    # 2. Mezclar y particionar (85% train, 15% val)
    idx_perm = np.random.default_rng(42).permutation(len(X))
    X = X[idx_perm]
    y = y[idx_perm]

    corte = max(1, int(len(X) * 0.85))
    X_train, X_val = X[:corte], X[corte:]
    y_train, y_val = y[:corte], y[corte:]
    if len(X_val) == 0:
        X_val, y_val = X_train, y_train

    print(f"Muestras de entrenamiento: {len(X_train)} | Muestras de validacion: {len(X_val)}")

    # 3. Construir modelo
    modelo = construir_modelo(len(CLASES))
    modelo.summary()

    # 4. Entrenar
    parar_temprano = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)
    epocas = 35 if len(X) > 50 else 15

    print(f"\nIniciando entrenamiento ({epocas} epocas)...")
    modelo.fit(
        X_train, y_train,
        batch_size=min(32, len(X_train)),
        epochs=epocas,
        validation_data=(X_val, y_val),
        callbacks=[parar_temprano],
        verbose=1
    )

    # 5. Guardar modelo y clases
    modelo.save(ARCHIVO_MODELO)
    with open(ARCHIVO_CLASES, "w", encoding="utf-8") as f:
        json.dump(CLASES, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"[OK] Modelo guardado en: {ARCHIVO_MODELO}")
    print(f"[OK] Clases guardadas en: {ARCHIVO_CLASES}")
    print("=" * 60)


if __name__ == "__main__":
    main()
