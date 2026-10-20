# Estación 2: Diagnóstico Empresarial mediante Ciencia de Datos
**Programa:** Ingeniería de Sistemas, Ciencia de Datos e Inteligencia de Negocios (6.° Semestre)  
**Modalidad:** Aprendizaje Basado en Retos (ABR)  
**Proyecto:** Manaco BI  
**Rol:** Equipo Consultor de Ciencia de Datos y Estrategia Empresarial  

---

## 1. Ficha Técnica y Estructura Depurada de Datos

A partir de la inspección y depuración del archivo `Bae de Datos MANACO - INTERMEDIO (1).xlsx`, se consolidó la siguiente estructura:

* **Universo de Registros:** 240 transacciones de comercio exterior.
* **Período de Análisis:** 5 años continuos (2020 a 2024).
* **Flujos Registrados:** 120 importaciones y 120 exportaciones.
* **País Reportante:** España (mercado de referencia de comercio exterior de calzado).
* **Socios Comerciales:** 30 países socios activos (Grecia, Países Bajos, Vietnam, Indonesia, Alemania, etc.).
* **Categorías de Producto (Arancel SA6):**
  1. *Calzado con suela de caucho/plástico y parte superior de cuero*
  2. *Calzado con suela de cuero y parte superior de cuero/material similar*
  3. *Calzado deportivo con suela de caucho/plástico*

---

## 2. Tablas Depuradas e Indicadores Clave

### 2.1. Balance Global por Flujo Comercial (2020 - 2024)

| Flujo Comercial | Registros | Valor Total (Millones USD) | Cantidad Total (Millones Pares) | Valor Ponderado por Par (USD/Par) |
| :--- | :---: | :---: | :---: | :---: |
| **Importación** | 120 | **$18,506.09 M** | **751.09 M** | **$24.64** |
| **Exportación** | 120 | **$10,917.35 M** | **410.77 M** | **$26.58** |
| **Balanza Comercial** | - | **-$7,588.74 M (Déficit)** | **-340.32 M (Déficit)** | - |

> **Nota Metodológica Fundamental:**  
> El valor ponderado por par se calculó como $\frac{\sum \text{Valor USD}}{\sum \text{Pares}}$. Si se calculara el promedio simple de la columna unitaria, el resultado arrojaría **$32.55 USD**, incurriendo en una sobreestimación del **42%** debido al sesgo de promediar promedios sin ponderar volúmenes.

---

### 2.2. Evolución Anual del Comercio (Valor y Cantidad)

| Año | Flujo Comercial | Valor Comercial (Millones USD) | Cantidad de Pares | Valor por Par Ponderado (USD) |
| :---: | :--- | :---: | :---: | :---: |
| **2020** | Exportación | $987.93 M | 36,828,978 | $26.82 |
| **2020** | Importación | $1,811.91 M | 77,095,383 | $23.50 |
| **2021** | Exportación | $2,521.35 M | 90,124,065 | $27.98 |
| **2021** | Importación | $1,430.18 M | 98,392,100 | $14.54 |
| **2022** | Exportación | $1,613.91 M | 59,493,326 | $27.13 |
| **2022** | Importación | $6,385.53 M | 241,446,512 | $26.45 |
| **2023** | Exportación | $3,140.22 M | 129,958,817 | $24.16 |
| **2023** | Importación | $1,190.21 M | 45,588,516 | $26.11 |
| **2024** | Exportación | $2,653.93 M | 94,366,461 | $28.12 |
| **2024** | Importación | $7,688.26 M | 288,566,407 | $26.64 |

---

### 2.3. Desglose por Categoría de Calzado (Valor vs. Volumen)

| Categoría de Calzado (SA6) | Flujo | Valor Total (Millones USD) | Cantidad de Pares (Millones) | Valor Ponderado (USD/Par) |
| :--- | :--- | :---: | :---: | :---: |
| **Suela caucho/plástico y superior cuero** | Exportación | $8,514.23 M | 320.75 M | $26.54 |
| **Suela caucho/plástico y superior cuero** | Importación | $11,709.68 M | 497.50 M | $23.54 |
| **Deportivo (suela caucho/plástico)** | Exportación | $2,173.93 M | 84.49 M | $25.73 |
| **Deportivo (suela caucho/plástico)** | Importación | $6,447.48 M | 245.87 M | $26.22 |
| **Suela de cuero y superior de cuero** | Exportación | $229.19 M | 5.53 M | **$41.42** |
| **Suela de cuero y superior de cuero** | Importación | $348.93 M | 7.72 M | **$45.22** |

---

### 2.4. Principales Socios Comerciales (Top 5)

#### Top 5 Socios en Importaciones:
1. **Grecia:** $2,109.63 M USD | 80.49 M pares ($26.21 / par)
2. **Países Bajos:** $1,754.06 M USD | 85.49 M pares ($20.52 / par)
3. **Vietnam:** $1,517.65 M USD | 52.06 M pares ($29.15 / par)
4. **Irlanda:** $912.70 M USD | 21.73 M pares ($42.00 / par)
5. **Turquía:** $907.97 M USD | 26.14 M pares ($34.73 / par)

#### Top 5 Socios en Exportaciones:
1. **Indonesia:** $2,286.29 M USD | 104.74 M pares ($21.83 / par)
2. **Vietnam:** $786.04 M USD | 37.08 M pares ($21.20 / par)
3. **Eslovenia:** $749.39 M USD | 26.87 M pares ($27.89 / par)
4. **Irlanda:** $606.26 M USD | 21.46 M pares ($28.25 / par)
5. **Grecia:** $553.22 M USD | 17.92 M pares ($30.88 / par)

---

## 3. Visualizaciones Clave

1. **Gráfico 1: Evolución Anual de Importaciones vs. Exportaciones (USD y Pares)**  
   Muestra el crecimiento explosivo de las importaciones en 2022 ($6.38B) y 2024 ($7.69B), superando holgadamente a las exportaciones y consolidando un déficit comercial continuo.
2. **Gráfico 2: Principales Socios Comerciales (Top 10)**  
   Permite visualizar la concentración del comercio en centros logísticos europeos (Grecia, Países Bajos) y polos de manufactura asiática (Vietnam, Indonesia).
3. **Gráfico 3: Comparación de Valor por Par por Categoría**  
   Contrasta visualmente cómo el calzado con suela de cuero alcanza valores superiores a los **$41 - $45 USD/par**, duplicando al calzado deportivo y sintético (**$23 - $26 USD/par**).

---

## 4. Síntesis Ejecutiva

### Tres Hallazgos Clave

1. **Déficit Estructural y Crecimiento Desmedido de Importaciones:**  
   El mercado analizado presenta un saldo comercial fuertemente deficitario: las importaciones ($18,506 M USD) superan a las exportaciones ($10,917 M USD) en un **69.5% en valor** y un **82.8% en volumen de pares**. En particular, el año 2024 registró un récord de 288.5 millones de pares importados frente a 94.4 millones exportados (relación de 3 a 1).
2. **Divergencia entre Volumen y Valor según Categoría de Calzado:**  
   * Al medir por **volumen (cantidad de pares)**, el calzado con suela de caucho y el deportivo absorben el **98.7%** del mercado importado (743.3 millones de pares de 751 millones totales) compitiendo a precios contenidos ($23 a $26 USD/par).
   * Al medir por **valor unitario**, el calzado con suela de cuero representa apenas el **1.03%** de los pares importados, pero alcanza un valor de **$45.22 USD/par**, evidenciando un segmento exclusivo de alto margen y calidad.
3. **Presencia Bivalente de Países Asiáticos (Proveedores y Destinos):**  
   Países como Vietnam e Indonesia no solo aparecen como grandes receptores de exportaciones a valores moderados (~$21/par), sino también como proveedores determinantes en calzado terminado, reflejando cadenas globales de ensamble y comercialización intensiva.

---

### Dos Limitaciones Metodológicas

1. **Naturaleza del Valor Comercial Aduanero (FOB/CIF vs. PVP):**  
   El indicador `Valor_USD_por_par` derivado de los registros aduaneros refleja únicamente el costo comercial declarado en frontera (mercancía + flete + seguro). **No equivale al precio de venta al público (PVP)**, ya que no contempla aranceles de importación, costos de nacionalización, margen de intermediación mayorista ni el margen del canal minorista (que típicamente multiplica este valor por 2x o 3x en estantería).
2. **Ausencia de Datos Transaccionales Internos de Manaco:**  
   El dataset externo refleja el comportamiento agregado del mercado de calzado, pero carece de variables críticas de Manaco: margen bruto interno, costos directos de mano de obra en Cochabamba, niveles de inventario por tienda, ventas por talla/modelo y tasa de devoluciones. Las conclusiones de este diagnóstico operan como hipótesis de contexto que requieren contrastarse con los datos del ERP interno.

---

### Una Pregunta Estratégica para la Gerencia General de Manaco

> **"¿Debe Manaco reenfocar su producción fabril propia exclusivamente hacia el segmento de calzado de cuero y especialidad (donde el mercado convalida valores superiores a $40 - $45 USD/par y la empresa cuenta con reputación de marca), mientras externaliza o distribuye calzado deportivo de volumen bajo esquemas de maquila para no absorber los altos costos fijos de fabricación frente a la escala internacional?"**

---

## 5. Respuestas a las Preguntas Orientadoras del Caso

* **¿Qué patrones destacan?**  
  La aceleración cíclica de las importaciones cada dos años (2022 y 2024) y la absoluta supremacía del calzado con suela sintética/cuero superior en la balanza comercial.
* **¿Qué cambia al medir valor o cantidad?**  
  Al medir por valor, el calzado con componentes de cuero domina la facturación total; sin embargo, al medir por cantidad, el calzado deportivo y sintético inunda el volumen del mercado con precios unitarios homogéneos.
* **¿Qué conclusiones son válidas y cuáles requieren más datos?**  
  * *Válidas con los datos actuales:* Volúmenes globales de comercio exterior, precios promedio declarados en aduana, principales países de origen/destino y balanza comercial por categoría.
  * *Requieren más datos internos:* Rentabilidad neta de Manaco por línea, elasticidad precio de la demanda boliviana y costo de manufactura local frente al calzado importado.
