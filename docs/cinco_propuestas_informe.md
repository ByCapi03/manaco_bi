# Actualización de las Cinco Propuestas Estratégicas - Proyecto MANACO BI

**Programa:** Ingeniería de Sistemas, Ciencia de Datos e Inteligencia de Negocios  
**Proyecto:** Manaco BI & Vision AI Suite  
**Arquitectura:** 5 Pestañas Orientadas a Problemas Empresariales (Directo desde Excel con Pandas, sin DW)  
**Fecha de Actualización:** 2026-10-22  

---

## Marco General de Reestructuración

De acuerdo con las directrices estratégicas de la consultoría:
1. **Desacoplamiento del Data Warehouse:** Se eliminó la dependencia de PostgreSQL (`fact_comercio`) para el análisis comercial, procesando directamente `data/raw/BDatos_MANACO.xlsx` mediante `pandas`.
2. **Catálogo de Demostración:** Se establecieron seis productos ficticios (dos por categoría SA6), manteniendo existencias operativas independientes y calculando las categorías arancelarias por agregación estricta de sumas.
3. **Aislamiento Financiero:** Las ventas registran el precio unitario efectivo al momento de la transacción para proteger los ingresos históricos frente a calibraciones posteriores del catálogo.
4. **Distinción Epistemológica:** Se distingue taxativamente entre **Problemas del Caso**, **Hipótesis**, **Resultados Reales Obtenidos** y **Limitaciones Pendientes**.

---

## Propuesta 1: Costos, Fijación de Precios y Evaluación Make-or-Buy

### 1.1. Problema del Caso Empresarial
Manaco enfrenta incertidumbre sobre cuándo le resulta más rentable fabricar en su planta local versus importar calzado terminado, en un contexto de precios deprimidos por importaciones asiáticas masivas. Asimismo, existe el riesgo de fijar precios minoristas sin cubrir los gastos de internación/flete o erosionar el margen objetivo del negocio.

### 1.2. Hipótesis de Trabajo
1. Existe un punto de indiferencia en volumen ($Q^*$) a partir del cual los costos fijos fabriles se diluyen y la fabricación local se vuelve más económica que la importación.
2. Una regla de margen sobre ventas parametrizable ($P = (\text{Costo Referencia} + \text{Gastos}) / (1 - \text{Margen})$) permite establecer precios sugeridos competitivos basados en referencias aduaneras reales sin comprometer la sostenibilidad financiera.

### 1.3. Metodología y Datos
- **Fuente de Referencia Aduanera 2024:** Cociente de sumas full precision sobre `BDatos_MANACO.xlsx`: $\frac{\sum \text{Valor\_USD}}{\sum \text{Cantidad\_pares}}$ por código SA6.
- **Parámetros Iniciales del Catálogo:**
  - *Deportivo Básico (640411):* Ref $27.80 + Gastos $4.00, Margen 25% $\rightarrow$ **$42.40 USD / Bs. 295.08**.
  - *Deportivo Confort (640411):* Ref $27.80 + Gastos $6.00, Margen 30% $\rightarrow$ **$48.28 USD / Bs. 336.05**.
  - *Casual Básico (640399):* Ref $26.15 + Gastos $4.00, Margen 25% $\rightarrow$ **$40.20 USD / Bs. 279.82**.
  - *Casual Confort (640399):* Ref $26.15 + Gastos $6.00, Margen 30% $\rightarrow$ **$45.93 USD / Bs. 319.69**.
  - *Vestir Básico (640420):* Ref $45.53 + Gastos $5.00, Margen 25% $\rightarrow$ **$67.38 USD / Bs. 468.94**.
  - *Vestir Confort (640420):* Ref $45.53 + Gastos $7.00, Margen 30% $\rightarrow$ **$75.05 USD / Bs. 522.32**.
- **Moneda y Conversión:** Interfaz con conmutador dinámico USD / BOB con tasa oficial parametrizable (default Bs. 6.96).

### 1.4. Resultados Reales Obtenidos
- Se implementó el motor de cálculo diferencial Make-or-Buy en `/api/escenarios/calcular`, graficando la curva de costo total y el desglose de componentes.
- Se implementó la acción principal "Aplicar Precio al Catálogo" (`/api/inventario/aplicar-precio`).
- **Prueba Ejecutada:** Se actualizó el precio del catálogo del Producto 1 y se constató que los ingresos históricos de ventas previas se mantuvieron invariables en **Bs. 2,338,680.23**.

### 1.5. Limitaciones Pendientes
- Los datos del Excel corresponden a declaraciones aduaneras de España, no a cotizaciones FOB/CIF con destino Bolivia.
- Los gastos de flete, aranceles y costos fabriles son parámetros simulados para análisis de escenarios, no balances auditados de planta.

---

## Propuesta 2: Inventario, Visión Artificial y Auditoría Transaccional

### 1.1. Problema del Caso Empresarial
Falta de control en tiempo real sobre las existencias físicas en bodega, riesgo de registrar stock negativo ante despachos descoordinados y necesidad de automatizar la recepción de calzados mediante herramientas modernas sin generar registros duplicados involuntarios.

### 1.2. Hipótesis de Trabajo
1. Un modelo de visión artificial (CNN MobileNetV2) puede clasificar rápidamente la categoría arancelaria del calzado; al requerir la selección manual entre la versión Básica o Confort, se evitan errores de clasificación fina y conteos duplicados involuntarios.
2. Un control transaccional atómico a nivel base de datos (`CHECK (stock_actual >= 0)`) y validación previa en la API elimina por completo el stock negativo.

### 1.3. Metodología y Datos
- **Catálogo:** 6 productos ficticios en `inventario_calzado`.
- **Agregación:** Existencias por producto; las existencias de categoría se calculan exclusivamente por suma dinámica.
- **Clasificador IA:** Modelo CNN entrenado con 4 clases (`calzado_deportivo`, `calzado_casual`, `calzado_formal`, `sin_calzado`). Al detectar calzado con confianza $\ge 70\%$, la interfaz presenta botones interactivos para elegir entre los dos modelos correspondientes (+1 par).
- **Tipos de Movimiento:** `VENTA`, `ENTRADA`, `INGRESO_IA`, `TRASLADO`, `AJUSTE`.

### 1.4. Resultados Reales Obtenidos
- Existencias iniciales de 90 pares migradas sin pérdidas (15 pares por producto, exactamente 30 pares por categoría).
- **Prueba Ejecutada (Rechazo de Venta Excesiva):** Intento de venta de 73 pares con stock disponible de 23 pares $\rightarrow$ Rechazado con código HTTP 400 y mensaje `"Salida rechazada por stock insuficiente. Disponible: 23 pares, Solicitado: 73 pares"`. Stock negativo prevenido al 100%.
- **Prueba Ejecutada (Venta Válida):** Venta de 2 pares registrada con ID #2395, stock resultante 21 pares, guardando precio unitario e ingreso total.
- **Auditoría:** Historial transaccional completo consultable con filtros de acción y canal, y exportación a CSV descargable.

### 1.5. Limitaciones Pendientes
- La cámara web depende de la iluminación ambiental y el ángulo del calzado; la CNN distingue la macro-categoría pero no detalles finos como materiales de plantilla, razón por la cual la selección final de modelo requiere validación del operador.

---

## Propuesta 3: Portafolio de Productos y Diferenciación Comercial

### 1.1. Problema del Caso Empresarial
Riesgo de comoditización al intentar competir únicamente por precio en categorías sintéticas/deportivas frente a fabricantes extranjeros de bajo costo, desaprovechando la tradición de calzado de cuero y el potencial de productos con mayor valor agregado.

### 1.2. Hipótesis de Trabajo
1. Estructurar el portafolio en dos líneas diferenciadas (**Básico** para volumen con margen del 25% y **Confort** con ergonomía y margen del 30%) optimiza el margen de contribución global y atiende distintos segmentos de poder adquisitivo.
2. Analizar la concentración del mercado internacional permite identificar nichos líderes en volumen y valor.

### 1.3. Metodología y Datos
- **Catálogo de 6 Productos Ficticios:**
  - SA 640411 (Deportivo): *Deportivo Básico* y *Deportivo Confort*.
  - SA 640399 (Casual Cuero): *Casual Básico* y *Casual Confort*.
  - SA 640420 (Formal Vestir): *Vestir Básico* y *Vestir Confort*.
- **Participación Comercial Externa:** Analizada directamente sobre los 1,161 millones de pares del Excel de aduanas de España.

### 1.4. Resultados Reales Obtenidos
- **Participación Externa:** El 78.6% del volumen comercializado corresponde a calzado con parte superior de cuero y suela sintética/goma (SA 640399, 226.75M pares importados en 2024), 20.7% a deportivo sintético (SA 640411, 59.58M pares) y 0.8% a formal con suela de cuero (SA 640420, 2.24M pares con el mayor valor unitario: $45.53 USD/par).
- **Márgenes del Portafolio:** Margen proyectado ponderado del 27.5% sobre ventas. Valorización del stock activo en bodega: Bs. 26,400.00 ($3,793.10 USD).
- Tabla interactiva con especificaciones completas de los seis productos e integración con el ranking Top 10 de socios comerciales (Grecia, Países Bajos, Vietnam, etc.).

### 1.5. Limitaciones Pendientes
- El catálogo de 6 productos es una simplificación con fines pedagógicos y analíticos; no representa la gama completa de centenares de SKUs que opera Manaco en Bolivia.
- El mapeo arancelario es demostrativo y no constituye una certificación de clasificación arancelaria oficial.

---

## Propuesta 4: Planificación de la Demanda y Reabastecimiento Preventivo

### 1.1. Problema del Caso Empresarial
Falta de previsión de la demanda que conduce a descalces entre aprovisionamiento y ventas, provocando roturas de stock en productos de alta rotación o acumulación de inventario inmovilizado.

### 1.2. Hipótesis de Trabajo
1. En series anuales de comercio exterior (Excel), comparar modelos ingenuos (*Naive*) con tendencias lineales mediante evaluación fuera de muestra permite identificar la inercia macro del mercado.
2. En ventas operativas diarias, un promedio móvil (MA7) evaluado cronológicamente ofrece un pronóstico a 7 días con bajo error absoluto (MAE en pares).
3. Una fórmula analítica de punto de reorden y sugerencia de reposición ($S = \max(0, \text{Demanda Lead Time} + \text{Stock Seguridad} - \text{Stock Disponible} - \text{Pendientes})$) previene el desabastecimiento sin emitir órdenes de compra automáticas no deseadas.

### 1.3. Metodología y Datos
- **A. Proyecciones Excel:** Entrenamiento 2020-2023, Evaluación temporal 2024.
  - *Deportivo (640411):* Error Naive 70.2%, Error Tendencia 23.5% $\rightarrow$ Mejor: Tendencia Lineal. Proyección 2025: 64.91M pares.
  - *Casual Cuero (640399):* Error Naive 88.5%, Error Tendencia 76.6% $\rightarrow$ Mejor: Tendencia Lineal. Proyección 2025: 247.45M pares.
  - *Formal Vestir (640420):* Error Naive 18.7%, Error Tendencia 48.1% $\rightarrow$ Mejor: Pronóstico Ingenuo. Proyección 2025: 2.24M pares.
- **B. Ventas Operativas Diarias:** Partición cronológica estricta (primeros 80% train, últimos 20% / 73 días test).
  - Modelo evaluado: Promedio Móvil 7 días (MA7) vs Pronóstico Ingenuo.
  - Métrica de error: **MAE = 1.02 pares físicos**.
  - Pronóstico para los próximos 7 días: 133 pares totales del catálogo.
- **Sugerencia de Reposición:** Calculada por producto con Lead Time configurable (7 días) y Stock de Seguridad (10 pares). Requiere confirmación humana explícita.

### 1.4. Resultados Reales Obtenidos
- Endpoints implementados: `/api/predicciones/excel`, `/api/predicciones/operativas`, `/api/inventario/confirmar-reposicion`.
- **Prueba Ejecutada:** Se confirmó la reposición sugerida para el Producto 1 (+10 pares). Se registró formalmente una `ENTRADA` en bodega y el stock se incrementó de 21 a 31 pares de forma inmediata.

### 1.5. Limitaciones Pendientes
- La serie del Excel abarca únicamente 5 años y su cobertura presenta variabilidad anual; no debe interpretarse como la demanda de calzado de Manaco en Bolivia.
- Los modelos predictivos no generan intervalos de confianza sin un método estocástico explícito y se limitan a un horizonte operativo de corto plazo (7 días).

---

## Propuesta 5: Ventas, Desempeño de Canales y Rigor Metodológico

### 1.1. Problema del Caso Empresarial
Dependencia histórica de tiendas físicas propias y distribuidores tradicionales, con escasa visibilidad del rendimiento comparativo frente al canal digital y riesgo de formular conclusiones erróneas basadas en datos inexistentes.

### 1.2. Hipótesis de Trabajo
1. Un historial transaccional de 12 meses generado sintéticamente con semilla fija (seed=42) permite modelar la estacionalidad del mercado boliviano (picos en mayo por el Día de la Madre y diciembre por Aguinaldo/Navidad).
2. Las ventas por canal pueden distribuirse coherentemente (Tiendas Propias ~58%, Distribuidores Mayoristas ~27%, E-commerce ~15%).
3. Por transparencia y rigor científico, cualquier métrica que carezca de datos de recolección primarios debe declararse explícitamente como "No disponible".

### 1.3. Metodología y Datos
- **Generador Determinista:** `clasificador_calzados/datos_sinteticos.py` con semilla fija (`seed=42`).
- **Idempotencia:** Verifica si existen registros sintéticos previos; re-ejecutarlo no duplica ni corrompe transacciones.
- **Volumen Generado:** 365 días, 2,362 movimientos, 6,959 pares vendidos, Bs. 2,338,090.07 en ingresos brutos.
- **Canales Modelados:**
  - *Tiendas Propias:* 4,036 pares (58.0%), Bs. 1,356,092.24, ticket medio 1.7 pares.
  - *Distribuidores Mayoristas:* 1,879 pares (27.0%), Bs. 631,284.32, ticket medio 12.4 pares.
  - *E-commerce / Tienda Online:* 1,044 pares (15.0%), Bs. 350,713.51, ticket medio 1.2 pares.
- **Declaración Explícita de "No disponible":**
  - *Tasa de Conversión Digital:* Requiere datos de sesiones/visitas y pedidos concretados (no disponibles).
  - *Abandono de Carritos:* Requiere carritos iniciados y compras finalizadas en plataforma web (no disponibles).
  - *Segmentación Demográfica / Pérdida del Segmento Joven:* Ni el Excel aduanero ni las tablas de inventario registran la edad de los compradores; cualquier afirmación al respecto carece de respaldo empírico en los datos disponibles.

### 1.4. Resultados Reales Obtenidos
- Se desplegó la pestaña "Ventas y Canales" con gráficos de dona y evolución mensual con los dos picos estacionales.
- La tarjeta KPI de Conversión y Abandono Digital muestra claramente la etiqueta gris `"No disponible"` con la justificación técnica correspondiente.
- Endpoint `/api/sinteticos/generar` permite regenerar el historial determinista bajo demanda.

### 1.5. Limitaciones Pendientes
- Las ventas de los tres canales son sintéticas y diseñadas con fines de demostración de analítica comercial; no corresponden a un volcado del ERP SAP de Manaco.

---

## Matriz Resumen de Validación y Cumplimiento

| Requerimiento del Pliego | Estado | Evidencia de Implementación |
| :--- | :---: | :--- |
| **5 Pestañas orientadas a problemas** | Cumplido | `index.html`, `app.js`, `app.css` con diseño modular moderno. |
| **Directo desde Excel con pandas** | Cumplido | `clasificador_calzados/analisis_comercio.py` lee `BDatos_MANACO.xlsx`. |
| **Retiro total de dependencia del DW** | Cumplido | Arranque desacoplado; tablas operativas locales en PostgreSQL/SQLite. |
| **Catálogo de 6 productos ficticios** | Cumplido | SKUs `DEP-BAS`, `DEP-CNF`, `CAS-BAS`, `CAS-CNF`, `VES-BAS`, `VES-CNF`. |
| **Recálculo de referencia 2024 full precision** | Cumplido | Deportivo ($27.80), Casual ($26.15), Vestir ($45.53) calculados por cociente de sumas. |
| **Precios iniciales y conversión USD/BOB** | Cumplido | Fórmula $P = (\text{ref}+\text{gastos})/(1-\text{margen})$ con conmutador en header (TC 6.96). |
| **Aislamiento financiero de ventas pasadas** | Cumplido | Precio efectivo guardado en cada registro; probado sin alteración histórica. |
| **Inventario por producto y suma por categoría** | Cumplido | `obtener_inventario_por_categoria()` suma cantidades dinámicamente. |
| **Rechazo estricto de stock negativo** | Cumplido | Validación transaccional y constraint DB; venta excesiva rechazada con 400. |
| **Cámara con selector de modelo interactivo** | Cumplido | Modal de botones Básico vs Confort para evitar conteos duplicados. |
| **Historial sintético determinista (seed=42)** | Cumplido | 12 meses reproducibles e idempotentes sin duplicación. |
| **Pronósticos temporales y MAE en pares** | Cumplido | Naive vs Tendencia (Excel) y MA7 (operativas) con MAE = 1.02 pares. |
| **Reposición interactiva con confirmación** | Cumplido | Modal con ingreso manual; no genera compras automáticas descontroladas. |
| **Etiquetas de origen breves** | Cumplido | Badges `"Fuente Excel"`, `"Simulación"`, `"Movimientos registrados"`, `"No disponible"`. |
| **Paneles plegables para parámetros** | Cumplido | Elementos `<details>` con metodología y parámetros avanzados. |
