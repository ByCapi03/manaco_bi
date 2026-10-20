# Estación 2: Diagnóstico Empresarial mediante Ciencia de Datos
**Programa:** Ingeniería de Sistemas, Ciencia de Datos e Inteligencia de Negocios (6.° Semestre)  
**Modalidad:** Aprendizaje Basado en Retos (ABR)  
**Proyecto:** Manaco BI  
**Rol:** Equipo Consultor de Ciencia de Datos y Estrategia Empresarial  

---

## 1. Ficha Técnica y Estructura Depurada de Datos

A partir de la inspección directa del archivo `Bae de Datos MANACO - INTERMEDIO (1).xlsx`, se verificó la siguiente estructura:

* **Universo de Registros:** 240 filas y 10 columnas.
* **País Reportante:** España (único país reportante en el 100% de los registros).
* **Distribución Temporal Real:** Años 2020 a 2024 (creciente por año):
  - **2020:** 28 registros (15 exportaciones, 13 importaciones)
  - **2021:** 34 registros (19 exportaciones, 15 importaciones)
  - **2022:** 46 registros (18 exportaciones, 28 importaciones)
  - **2023:** 50 registros (26 exportaciones, 24 importaciones)
  - **2024:** 82 registros (42 exportaciones, 40 importaciones)
  - *Total:* 240 registros (120 de importación y 120 de exportación).
* **Socios Comerciales:** 30 países socios activos (sin registros "Mundo").
* **Categorías de Producto (Arancel SA6):**
  1. *Calzado con suela de caucho/plástico y parte superior de cuero*
  2. *Calzado con suela de cuero y parte superior de cuero/material similar*
  3. *Calzado deportivo con suela de caucho/plástico*
* **Calidad e Integridad:** 0 valores nulos, 0 duplicados exactos de fila completa.
* **Granularidad y Combinaciones Repetidas:** Existen 10 combinaciones dimensionales repetidas que involucran 20 filas con importes y cantidades distintas. Dado que su significado de negocio no está confirmado en la fuente, **se conservan íntegramente las 240 filas** sin eliminarlas ni consolidarlas, definiendo la granularidad del modelo estrictamente como **una fila del archivo fuente**.

---

## 2. Tablas Depuradas e Indicadores Clave

### 2.1. Balance por Flujo Comercial (Conjunto Completo de 240 Registros)

| Flujo Comercial | Número de Registros | Suma Valor Comercial (USD) | Suma Cantidad Pares | Cociente de Sumas (Valor/Par Ponderado) | Promedio Simple de `Valor_USD_por_par` (Referencia) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Exportación** | 120 | $10,917,349,349.48 | 410,771,647 | **$26.58 / par** (26.5777) | $35.11 / par (35.1116) |
| **Importación** | 120 | $18,506,091,720.31 | 751,088,918 | **$24.64 / par** (24.6390) | $37.71 / par (37.7133) |
| **Total General** | **240** | **$29,423,441,069.79** | **1,161,860,565** | **$25.32 / par** (25.3244) | **$36.41 / par** (36.4124) |
| **Balanza Comercial** | - | **-$7,588,742,370.83** (Déficit) | **-340,317,271 pares** (Déficit) | - | - |

> **Nota Metodológica:**  
> El valor comercial aproximado por par por flujo se calcula como el cociente de sumas $\frac{\sum \text{Valor}}{\sum \text{Pares}}$, resultando en **$26.58 USD** para exportaciones y **$24.64 USD** para importaciones (y **$25.32 USD** en el total global).  
> El promedio simple del indicador unitario ($35.11 en exportaciones, $37.71 en importaciones y $36.41 global) se presenta exclusivamente como comparación para constatar el sesgo estadístico que se produce al no ponderar por el volumen real de cada registro.

---

### 2.2. Evolución Anual del Comercio Registrado

| Año | Flujo Comercial | Registros | Suma Valor Comercial (USD) | Suma Cantidad Pares | Cociente de Sumas (USD/Par) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **2020** | Exportación | 15 | $987,933,970.08 | 36,828,978 | $26.82 |
| **2020** | Importación | 13 | $1,811,913,877.01 | 77,095,383 | $23.50 |
| **2021** | Exportación | 19 | $2,521,354,378.89 | 90,124,065 | $27.98 |
| **2021** | Importación | 15 | $1,430,184,738.40 | 98,392,100 | $14.54 |
| **2022** | Exportación | 18 | $1,613,910,713.88 | 59,493,326 | $27.13 |
| **2022** | Importación | 28 | $6,385,526,569.21 | 241,446,512 | $26.45 |
| **2023** | Exportación | 26 | $3,140,224,196.25 | 129,958,817 | $24.16 |
| **2023** | Importación | 24 | $1,190,210,193.89 | 45,588,516 | $26.11 |
| **2024** | Exportación | 42 | $2,653,926,090.38 | 94,366,461 | $28.12 |
| **2024** | Importación | 40 | $7,688,256,341.80 | 288,566,407 | $26.64 |

---

### 2.3. Desglose por Categoría de Calzado (Valor vs. Volumen)

| Categoría de Calzado (SA6) | Flujo | Valor Total (Millones USD) | Cantidad de Pares (Millones) | Cociente de Sumas (USD/Par) |
| :--- | :--- | :---: | :---: | :---: |
| **Suela caucho/plástico y superior cuero** | Exportación | $8,514.23 M | 320.75 M | $26.54 |
| **Suela caucho/plástico y superior cuero** | Importación | $11,709.68 M | 497.50 M | $23.54 |
| **Deportivo (suela caucho/plástico)** | Exportación | $2,173.93 M | 84.49 M | $25.73 |
| **Deportivo (suela caucho/plástico)** | Importación | $6,447.48 M | 245.87 M | $26.22 |
| **Suela de cuero y superior de cuero** | Exportación | $229.19 M | 5.53 M | **$41.42** |
| **Suela de cuero y superior de cuero** | Importación | $348.93 M | 7.72 M | **$45.22** |

---

### 2.4. Principales Socios Comerciales

#### Top 5 Socios en Importaciones (por Valor Comercial):
1. **Grecia:** $2,109.63 M USD | 80.49 M pares | Cociente: $26.21 / par
2. **Países Bajos:** $1,754.06 M USD | 85.49 M pares | Cociente: $20.52 / par
3. **Vietnam:** $1,517.65 M USD | 52.06 M pares | Cociente: $29.15 / par
4. **Irlanda:** $912.70 M USD | 21.73 M pares | Cociente: $42.00 / par
5. **Turquía:** $907.97 M USD | 26.14 M pares | Cociente: $34.73 / par

#### Top 5 Socios en Exportaciones (por Valor Comercial):
1. **Indonesia:** $2,286.29 M USD | 104.74 M pares | Cociente: $21.83 / par
2. **Vietnam:** $786.04 M USD | 37.08 M pares | Cociente: $21.20 / par
3. **Eslovenia:** $749.39 M USD | 26.87 M pares | Cociente: $27.89 / par
4. **Irlanda:** $606.26 M USD | 21.46 M pares | Cociente: $28.25 / par
5. **Grecia:** $553.22 M USD | 17.92 M pares | Cociente: $30.88 / par

---

## 3. Visualizaciones Clave

1. **Gráfico 1: Importaciones frente a Exportaciones por Año (2020 - 2024)**  
   *Archivo generado:* `docs/grafico1_import_vs_export.png`  
   Muestra el crecimiento de las importaciones en 2022 ($6.39B) y 2024 ($7.69B), superando a las exportaciones en valor y consolidando una brecha comercial en el mercado observado.
2. **Gráfico 2: Top 10 Socios Comerciales de Importación**  
   *Archivo generado:* `docs/grafico2_principales_socios.png`  
   Presenta la distribución del valor importado según país socio comercial dentro de los registros disponibles.
3. **Gráfico 3: Comparación de Valor Comercial Ponderado por Par (USD/Par)**  
   *Archivo generado:* `docs/grafico3_valor_por_par.png`  
   Compara el cociente de sumas entre categorías, donde el calzado con suela de cuero alcanza valores superiores a los **$41 - $45 USD/par**, frente al calzado deportivo y sintético (**$23 - $26 USD/par**).

---

## 4. Síntesis Ejecutiva

### Tres Hallazgos Clave

1. **Diferencia entre Flujos de Importación y Exportación en el Conjunto de Datos:**  
   En los registros observados, las importaciones ($18,506.09 M USD) superan a las exportaciones ($10,917.35 M USD) en un **69.5% en valor** y un **82.8% en volumen de pares**, con una concentración de registros en 2024 (82 de los 240 registros totales).
2. **Divergencia entre Volumen y Valor según Categoría de Calzado:**  
   * Al medir por **volumen (cantidad de pares)**, el calzado con suela sintética/superior cuero y el deportivo absorben el **98.7%** de los pares importados (743.3 millones de 751.1 millones totales).
   * Al medir por **valor unitario aproximado**, el calzado con suela de cuero representa apenas el **1.03%** de los pares importados, pero alcanza un cociente de **$45.22 USD/par**, frente a los $23.54 y $26.22 de las otras categorías.
3. **Papel de los Socios Comerciales en los Registros Disponibles:**  
   Países como Vietnam e Indonesia figuran con participación relevante tanto en importación como en exportación, registrando cocientes moderados (~$21 a $29 USD/par).

---

### Dos Limitaciones Metodológicas

1. **El Valor Comercial Registrado no Equivale al Precio Minorista de Venta:**  
   El indicador `Valor_USD_por_par` corresponde al valor comercial registrado en la base de comercio exterior. **No equivale al precio de venta al consumidor final en tienda (PVP)**, ya que no contempla costos arancelarios de nacionalización, transporte interno, costos de distribución ni el margen del canal minorista.
2. **El Comercio Exterior de España es una Referencia Externa, no las Operaciones de Manaco:**  
   El dataset refleja transacciones de comercio exterior reportadas por España. **No representa las ventas, costos de producción, inventarios ni la rentabilidad de Manaco en Bolivia.** Las conclusiones extraídas constituyen hipótesis de mercado externo que requieren contrastarse con datos transaccionales internos de la empresa.

---

### Una Pregunta Estratégica para Manaco

> **"A partir de la evidencia de mercado que muestra que el calzado con componentes de cuero alcanza valores comerciales sensiblemente mayores ($41-$45 USD/par) frente al calzado deportivo ($23-$26 USD/par), ¿debería Manaco evaluar la viabilidad de reorientar su capacidad manufacturera local hacia líneas de cuero y especialidad, mientras analiza opciones de abastecimiento externo o distribución para calzado deportivo de bajo precio unitario?"**
