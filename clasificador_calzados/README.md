# 👞 Clasificador de Calzados Manaco con Inventario y Dashboard BI

Sistema integral de **Visión Artificial**, **Control de Inventario en Tiempo Real** y **Business Intelligence (BI)** para **Fábrica Boliviana de Calzados Manaco**.

---

## 📌 Categorías de Calzado Soportadas (3 Categorías del Catálogo Manaco)

Siguiendo el esquema dimensional de `dim_producto` en el Data Warehouse (`manaco_dw`), el sistema reconoce:

1. **`calzado_deportivo`** (SA6: `640411`) - Calzado deportivo con suela de caucho/plástico (Sneakers / Tenis).
2. **`calzado_casual`** (SA6: `640399`) - Calzado con suela de caucho/plástico y capellada de cuero (Mocasines / Botines).
3. **`calzado_formal`** (SA6: `640420`) - Calzado formal con suela y capellada de cuero (Línea ejecutiva / Vestir).
4. **`sin_calzado`** (Clase 0) - Fondo vacío, manos u objetos no relacionados.

---

## 🚀 Arquitectura y Componentes del Proyecto

| Componente | Archivo | Descripción |
|---|---|---|
| **Configuración** | [`config.py`](config.py) | Hiperparámetros, umbrales de confianza, categorías y mapeos con el DW. |
| **Capa de Persistencia** | [`db_manaco.py`](db_manaco.py) | Conexión híbrida a **PostgreSQL** (`manaco_dw`) con fallback transparente a **SQLite**. |
| **Simulador de Datos** | [`simulador_datos.py`](simulador_datos.py) | Genera movimientos sintéticos realistas para pruebas y dashboards. |
| **Paso 1: Captura** | [`1_capturar_imagenes.py`](1_capturar_imagenes.py) | Captura de imágenes con cámara web para armar o ampliar el dataset. |
| **Paso 2: Entrenamiento** | [`2_entrenar_modelo.py`](2_entrenar_modelo.py) y [`.ipynb`](2_entrenar_modelo.ipynb) | Entrenamiento de CNN convolucional profunda con Data Augmentation. |
| **Paso 3: App de Escritorio** | [`3_app_inventario.py`](3_app_inventario.py) | Aplicación OpenCV con HUD tecnológico, beeps sonoros y conexión a la base de datos. |
| **Paso 4: Plataforma Web BI** | [`app_web.py`](app_web.py) | Servidor web Flask con Dashboard BI interactivo, escáner en tiempo real y gráficos. |

---

## 🛠️ Ejecución de la Plataforma Web (Recomendado)

Inicia el servidor web en el puerto `5000`:

```powershell
.\.venv\Scripts\python.exe clasificador_calzados\app_web.py
```

Abre en tu navegador: **[http://localhost:5000](http://localhost:5000)**

### Módulos incluidos en la interfaz web:
- **📊 Dashboard BI Gerencial:** KPIs de inventario (pares totales, valorización en Bs. y $us., categoría líder y tasa de acierto IA) y 4 gráficos interactivos con Chart.js.
- **📷 Escáner IA de Calzado:** Usa la cámara web en vivo o sube una fotografía. Al detectar un calzado con confianza > 75%, reproduce un sonido de confirmación y suma automáticamente a la base de datos.
- **📋 Movimientos & Auditoría:** Trazabilidad completa con opción de búsqueda y exportación a CSV.
- **⚙️ Simulador & Data Warehouse:** Generador sintético de 10 a 150 transacciones con un solo clic.

---

## 🖥️ Ejecución de la App de Escritorio (OpenCV)

Si deseas ejecutar la ventana de escritorio tradicional (similar a la app de escritorio de botellas):

```powershell
.\.venv\Scripts\python.exe clasificador_calzados\3_app_inventario.py
```

**Controles en la app de escritorio:**
- `ESPACIO`: Forzar registro del calzado detectado inmediatamente.
- `z`: Deshacer el último registro.
- `r`: Reiniciar inventario a niveles base.
- `s`: Simular 5 movimientos aleatorios de inventario.
- `q` o `ESC`: Salir.

---

## 📸 Capturar Nuevas Fotos y Re-entrenar

1. **Capturar imágenes:**
   ```powershell
   .\.venv\Scripts\python.exe clasificador_calzados\1_capturar_imagenes.py
   ```
   - Teclas `0`, `1`, `2`, `3` eligen la categoría.
   - `ESPACIO` activa/pausa la ráfaga continua (~5 fotos/seg).
   - `g` guarda una foto individual.

2. **Re-entrenar el modelo:**
   ```powershell
   .\.venv\Scripts\python.exe clasificador_calzados\2_entrenar_modelo.py
   ```
   O abre [`2_entrenar_modelo.ipynb`](2_entrenar_modelo.ipynb) en VS Code / Jupyter seleccionando el kernel `.venv`.
