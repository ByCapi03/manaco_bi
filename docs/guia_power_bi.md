# Guía de Implementación del Tablero Power BI - MANACO BI
**Proyecto:** Data Warehouse y Tablero de Inteligencia de Negocios para MANACO  
**Origen de Datos:** PostgreSQL (`localhost:5432`, base de datos `manaco_dw`)  
**Modo de Conexión:** Importar  
**Propósito:** Soportar técnicamente el análisis de la Estación 2 y el diagnóstico de comercio exterior.

---

## 1. Conexión a PostgreSQL y Configuración del Modelo Estrella

### 1.1. Paso a Paso para Conectar Power BI Desktop

1. Abre **Power BI Desktop**.
2. En la cinta de opciones superior, selecciona **Obtener datos** $\rightarrow$ **Más...** $\rightarrow$ **Base de datos** $\rightarrow$ **Base de datos PostgreSQL** $\rightarrow$ **Conectar**.
3. Configura los parámetros de conexión:
   * **Servidor:** `localhost:5432` (o simplemente `localhost`).
   * **Base de datos:** `manaco_dw`.
   * **Modo de conectividad de datos:** Selecciona **Importar**.
4. Haz clic en **Aceptar**.
5. Si solicita credenciales de acceso:
   * Selecciona la pestaña **Base de datos**.
   * Ingresa tu usuario (ej. `postgres`) y la contraseña configurada en tu archivo `.env`.
   * Si aparece una advertencia sobre la compatibilidad de cifrado, selecciona *Aceptar / Continuar sin cifrado* para conexiones locales.
6. En la ventana **Navegador**, marca las siguientes **6 tablas** del modelo estrella:
   * `dim_periodo`
   * `dim_producto`
   * `dim_reportante`
   * `dim_socio`
   * `dim_flujo`
   * `fact_comercio`  
   *(Opcional: puedes cargar también `vw_resumen_por_flujo` exclusivamente para contrastar totales y verificar la consistencia de las medidas DAX, manteniéndola desconectada del modelo).*
7. Haz clic en **Cargar**.

---

### 1.2. Configuración de Relaciones en la Vista de Modelo

En la pestaña **Vista de Modelo** (icono de diagrama en el panel izquierdo), verifica que existan exactamente las 5 relaciones del esquema estrella entre las claves primarias de cada dimensión y sus claves foráneas en `fact_comercio`:

```
    ┌────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │  dim_periodo   │       │  dim_reportante │       │    dim_flujo    │
    │  (id_periodo)  │       │ (id_reportante) │       │   (id_flujo)    │
    └───────┬────────┘       └────────┬────────┘       └────────┬────────┘
            │ 1                       │ 1                       │ 1
            │                         │                         │
            │ *                       │ *                       │ *
    ┌───────┴─────────────────────────┴─────────────────────────┴────────┐
    │                           fact_comercio                            │
    │ (id_periodo, id_reportante, id_flujo, id_producto, id_socio)       │
    └───────┬───────────────────────────────────────────────────┬────────┘
            │ *                                                 │ *
            │                                                   │
            │ 1                                                 │ 1
    ┌───────┴────────┐                                 ┌────────┴────────┐
    │  dim_producto  │                                 │    dim_socio    │
    │  (id_producto) │                                 │    (id_socio)   │
    └────────────────┘                                 └─────────────────┘
```

#### Especificación Exacta de las 5 Relaciones:

| N.° | Tabla Dimensión (Lado 1 - PK) | Campo Clave | Tabla Hechos (Lado Varios - FK) | Campo Clave | Cardinalidad | Dirección de Filtro Cruzado | Estado |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **1** | `dim_periodo` | `id_periodo` | `fact_comercio` | `id_periodo` | 1 a varios ($1:*$) | **Única** (dimensión $\rightarrow$ hechos) | Activa |
| **2** | `dim_producto` | `id_producto` | `fact_comercio` | `id_producto` | 1 a varios ($1:*$) | **Única** (dimensión $\rightarrow$ hechos) | Activa |
| **3** | `dim_reportante`| `id_reportante`| `fact_comercio` | `id_reportante` | 1 a varios ($1:*$) | **Única** (dimensión $\rightarrow$ hechos) | Activa |
| **4** | `dim_socio` | `id_socio` | `fact_comercio` | `id_socio` | 1 a varios ($1:*$) | **Única** (dimensión $\rightarrow$ hechos) | Activa |
| **5** | `dim_flujo` | `id_flujo` | `fact_comercio` | `id_flujo` | 1 a varios ($1:*$) | **Única** (dimensión $\rightarrow$ hechos) | Activa |

> **Regla de Diseño:** Mantener la dirección de filtro cruzado como **Única**. La vista `vw_resumen_por_flujo` debe permanecer desconectada sin relaciones, utilizándose únicamente como tabla de contraste estática.

---

## 2. Medidas DAX Requeridas

Crea estas medidas en `fact_comercio` (o en una tabla dedicada `_Medidas`):

### 2.1. Valor Comercial Total (USD)
Suma monetaria total del valor comercial registrado en el archivo.
```dax
Valor Comercial USD = 
SUM(fact_comercio[valor_usd])
```

### 2.2. Cantidad Total de Pares
Suma total del volumen físico de calzado en pares registrado.
```dax
Cantidad Pares = 
SUM(fact_comercio[cantidad_pares])
```

### 2.3. Número de Registros
Conteo de registros del archivo cargados en la tabla de hechos.
```dax
Número de Registros = 
COUNTROWS(fact_comercio)
```

### 2.4. Valor Comercial Aproximado por Par (Ponderado)
**Regla Fundamental:** Se calcula como el cociente de sumas $\frac{\sum \text{Valor}}{\sum \text{Pares}}$. Si no existe cantidad válida o la suma de pares es cero/nula, devuelve `BLANK()`. **Bajo ninguna circunstancia se debe utilizar el promedio simple de la columna unitaria como KPI.**
```dax
Valor Comercial por Par = 
DIVIDE(
    [Valor Comercial USD],
    [Cantidad Pares],
    BLANK()
)
```

### 2.5. Valor Importado (USD)
Filtra específicamente los registros del flujo de importación.
```dax
Valor Importado = 
CALCULATE(
    [Valor Comercial USD],
    dim_flujo[flujo_comercial] = "Importación"
)
```

### 2.6. Valor Exportado (USD)
Filtra específicamente los registros del flujo de exportación.
```dax
Valor Exportado = 
CALCULATE(
    [Valor Comercial USD],
    dim_flujo[flujo_comercial] = "Exportación"
)
```

---

### 2.7. Documentación Técnica del Contexto de Filtro en las Medidas DAX
* **Comportamiento de `Valor Importado` y `Valor Exportado`:**  
  Debido a que ambas medidas utilizan `CALCULATE([Valor Comercial USD], dim_flujo[flujo_comercial] = "...")`, la condición interna **sustituye y sobreescribe** cualquier filtro proveniente del segmentador de flujo para ese campo en sus respectivas tarjetas. Por lo tanto, si el usuario selecciona "Exportación" en un segmentador, la tarjeta `[Valor Importado]` seguirá mostrando el total importado por diseño deliberado de la medida.
* **Comportamiento de las Medidas Generales y Gráficos:**  
  Las medidas generales (`[Valor Comercial USD]`, `[Cantidad Pares]`, `[Número de Registros]`, `[Valor Comercial por Par]`) y los gráficos no tienen filtros internos fijados; por lo tanto, **sí responden y se recalculan dinámicamente** según la selección del segmentador de flujo.
* *Nota:* Este comportamiento es intencional y garantiza que las tarjetas de totales por flujo siempre sirvan como marco de referencia visible, independientemente de los filtros cruzados aplicados a los gráficos.

---

## 3. Diseño de la Página de Diagnóstico Empresarial

Crea una página en Power BI titulada **"Diagnóstico de Comercio Exterior"** organizada con la siguiente distribución espacial:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ENCABEZADO: Título del Proyecto, Referencia Externa y Cuadro con Notas Metodológicas            │
├───────────────────────────────┬─────────────────────────────────┬───────────────────────────────┤
│ [ Tarjeta 1 ]                 │ [ Tarjeta 2 ]                   │ [ Tarjeta 3 ]                 │
│ Valor Importado               │ Valor Exportado                 │ Cantidad Total Pares          │
├───────────────────────────────┴─────────────────────────────────┴───────────────────────────────┤
│ FILTROS SUPERIORES (Segmentadores): Año | Categoría de Calzado | Flujo Comercial | Socio Comercial│
├────────────────────────────────────────────────┬────────────────────────────────────────────────┤
│ GRÁFICO 1 (Columnas Agrupadas)                 │ GRÁFICO 2 (Barras Horizontales)                │
│ Importaciones frente a Exportaciones por Año   │ Principales 10 Socios por Valor                │
├────────────────────────────────────────────────┴────────────────────────────────────────────────┤
│ GRÁFICO 3 (Columnas Agrupadas)                                                                  │
│ Valor Comercial Ponderado por Par (USD/Par) según Categoría de Calzado y Flujo                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1. Especificación de Objetos Visuales y Campos

#### A. Tarjetas Numéricas Superiores (KPIs)
1. **Tarjeta 1: Valor Importado**
   * *Campo:* Medida `[Valor Importado]`.
   * *Formato:* Moneda ($), muestra ~$18.51 mil M.
2. **Tarjeta 2: Valor Exportado**
   * *Campo:* Medida `[Valor Exportado]`.
   * *Formato:* Moneda ($), muestra ~$10.92 mil M.
3. **Tarjeta 3: Volumen Total**
   * *Campo:* Medida `[Cantidad Pares]`.
   * *Formato:* Decimal con separador de miles, muestra 1,161.86 M de pares.

#### B. Gráfico 1: Columnas Agrupadas - Importaciones frente a Exportaciones por Año
* **Tipo Visual:** Gráfico de columnas agrupadas (*Clustered column chart*).
* **Eje X:** `dim_periodo[anio]` (Año).
* **Leyenda:** `dim_flujo[flujo_comercial]` (Flujo Comercial).
* **Eje Y:** Medida `[Valor Comercial USD]`.
* **Propósito:** Mostrar la evolución anual de importaciones frente a exportaciones, evidenciando los registros acumulados en 2022 y 2024.

#### C. Gráfico 2: Barras Horizontales - Principales Socios por Valor
* **Tipo Visual:** Gráfico de barras agrupadas horizontales (*Clustered bar chart*).
* **Eje Y:** `dim_socio[socio_comercial]`.
* **Eje X:** Medida `[Valor Comercial USD]`.
* **Filtro de Nivel Visual:** Filtro Top N $\rightarrow$ Superior **10** según la medida `[Valor Comercial USD]`.
* **Propósito:** Identificar la concentración de valor por socio. Al seleccionar un flujo en el segmentador, permite distinguir entre principales proveedores (en Importación) y principales destinos (en Exportación).

#### D. Gráfico 3: Columnas Agrupadas - Valor por Par según Categoría y Flujo
* **Tipo Visual:** Gráfico de columnas agrupadas (*Clustered column chart*).
* **Eje X:** `dim_producto[categoria_calzado]` (utilizando la descripción oficial de la dimensión).
* **Leyenda:** `dim_flujo[flujo_comercial]`.
* **Eje Y:** Medida `[Valor Comercial por Par]`.
* **Propósito:** Contrastar los niveles de valor unitario por categoría, observando el comportamiento de las tres descripciones de producto del modelo.

#### E. Segmentadores (Slicers)
Ubica 4 segmentadores en la parte superior:
1. **Año:** Campo `dim_periodo[anio]`.
2. **Categoría:** Campo `dim_producto[categoria_calzado]`.
3. **Flujo:** Campo `dim_flujo[flujo_comercial]`.
4. **Socio:** Campo `dim_socio[socio_comercial]`.

---

## 4. Protocolo de Verificación sin Filtros (Checklist de Control)

Comprueba en Power BI que los valores de las medidas sin ningún filtro activo coincidan exactamente con la base de datos PostgreSQL:

| Indicador / Medida | Valor Exacto sin Filtros | Comprobación en Tablero |
| :--- | :---: | :---: |
| **Número de Registros** | **240** | [ ] Coincide con `COUNTROWS` |
| **Registros Exportación** | **120** | [ ] Coincide con consulta SQL |
| **Registros Importación** | **120** | [ ] Coincide con consulta SQL |
| **Valor Total Exportado** | **$10,917,349,349.48 USD** (~$10,917.35 M) | [ ] Coincide |
| **Cantidad Pares Exportados** | **410,771,647 pares** (~410.77 M) | [ ] Coincide |
| **Valor por Par Exportado** | **$26.58 USD / par** | [ ] Coincide ($10.92B / 410.77M) |
| **Valor Total Importado** | **$18,506,091,720.31 USD** (~$18,506.09 M) | [ ] Coincide |
| **Cantidad Pares Importados** | **751,088,918 pares** (~751.09 M) | [ ] Coincide |
| **Valor por Par Importado** | **$24.64 USD / par** | [ ] Coincide ($18.51B / 751.09M) |
| **Valor Total General (Ambos Flujos)** | **$29,423,441,069.79 USD** | [ ] Coincide |
| **Pares Totales Generales** | **1,161,860,565 pares** | [ ] Coincide |
| **Valor por Par Global Ponderado** | **$25.32 USD / par** | [ ] Coincide ($29.42B / 1,161.86M) |

### Comprobación de Interactividad de Segmentadores:
1. **Al filtrar por Flujo = "Importación":**
   * Las medidas generales (`[Valor Comercial USD]`, `[Cantidad Pares]`, `[Valor Comercial por Par]`) se actualizan a los valores de importación ($18,506.09 M USD, 751.09 M pares y **$24.64 USD/par**).
   * La tarjeta `[Valor Exportado]` se mantiene en su valor por el modificador `CALCULATE` (diseño documentado).
   * El Gráfico 2 de socios muestra a Grecia ($2,109.63 M), Países Bajos ($1,754.06 M), Vietnam ($1,517.65 M), Irlanda ($912.70 M) y Turquía ($907.97 M) en el Top 5.
2. **Al filtrar por Flujo = "Exportación":**
   * Las medidas generales se actualizan a los valores de exportación ($10,917.35 M USD, 410.77 M pares y **$26.58 USD/par**).
   * El Gráfico 2 de socios muestra a Indonesia ($2,286.29 M), Vietnam ($786.04 M), Eslovenia ($749.39 M), Irlanda ($606.26 M) y Grecia ($553.22 M).
3. **Al filtrar por Año = 2024:**
   * La medida `[Número de Registros]` marca exactamente **82**.
   * Los gráficos reflejan únicamente los registros de 2024 ($7,688.26 M USD en importación y $2,653.93 M USD en exportación).

---

## 5. Verificación de Categorías e Interpretación para la Estación 2

### 5.1. Consulta Verificada en PostgreSQL por Categoría y Flujo

```sql
SELECT 
    pr.codigo_sa6,
    pr.categoria_calzado,
    f.flujo_comercial,
    SUM(c.valor_usd) AS valor_usd,
    SUM(c.cantidad_pares) AS cantidad_pares,
    ROUND(
        (SUM(c.cantidad_pares) * 100.0 / SUM(SUM(c.cantidad_pares)) OVER (PARTITION BY f.flujo_comercial)),
        2
    ) AS pct_pares_flujo,
    ROUND(
        SUM(c.valor_usd) / NULLIF(SUM(c.cantidad_pares), 0),
        2
    ) AS cociente_valor_por_par
FROM fact_comercio c
JOIN dim_producto pr ON c.id_producto = pr.id_producto
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
GROUP BY pr.codigo_sa6, pr.categoria_calzado, f.flujo_comercial
ORDER BY f.flujo_comercial, valor_usd DESC;
```

#### Resultados Obtenidos en la Base de Datos:

| Código SA6 | Descripción Oficial de Categoría (`dim_producto`) | Flujo Comercial | Valor Comercial (USD) | Cantidad de Pares | Participación en Pares del Flujo | Cociente Valor por Par (USD/Par) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **640399** | Calzado con suela de caucho/plástico y parte superior de cuero | **Exportación** | $8,514,235,202.14 | 320,751,937 | **78.09%** | **$26.54** |
| **640411** | Calzado deportivo con suela de caucho/plástico | **Exportación** | $2,173,925,768.82 | 84,486,912 | **20.57%** | **$25.73** |
| **640420** | Calzado con suela de cuero y parte superior de cuero/material similar | **Exportación** | $229,188,378.52 | 5,532,798 | **1.35%** | **$41.42** |
| *Total Export.* | *(Suma de las 3 categorías)* | *Exportación* | *$10,917,349,349.48* | *410,771,647* | ***100.01%**** | *$26.58* |
| **640399** | Calzado con suela de caucho/plástico y parte superior de cuero | **Importación** | $11,709,684,709.81 | 497,500,841 | **66.24%** | **$23.54** |
| **640411** | Calzado deportivo con suela de caucho/plástico | **Importación** | $6,447,479,590.82 | 245,871,098 | **32.74%** | **$26.22** |
| **640420** | Calzado con suela de cuero y parte superior de cuero/material similar | **Importación** | $348,927,419.68 | 7,716,979 | **1.03%** | **$45.22** |
| *Total Import.* | *(Suma de las 3 categorías)* | *Importación* | *$18,506,091,720.31* | *751,088,918* | ***100.01%**** | *$24.64* |

*\*Nota de redondeo:* La suma de participaciones porcentuales resulta en **100.01%** en ambos flujos debido al redondeo estándar de dos decimales de cada sumando. La suma con decimales completos es exactamente **100.00%** (en importación: $66.2373\% + 32.7353\% + 1.0274\% = 100.0000\%$; en exportación: $78.0852\% + 20.5679\% + 1.3469\% = 100.0000\%$).

---

### 5.2. Tres Hallazgos Clave con Evidencia Empírica

1. **Diferencia entre Volúmenes Registrados de Importación y Exportación:**  
   En los 240 registros del archivo, las importaciones registradas (751,088,918 pares y $18,506,091,720.31 USD) superan a las exportaciones (410,771,647 pares y $10,917,349,349.48 USD) en un **82.8% en pares** y un **69.5% en valor**. El año 2024 concentra el mayor número de registros del archivo (82 registros de 240), acumulando $7,688.26 M USD en importaciones y $2,653.93 M USD en exportaciones.
2. **Distribución del Volumen Físico y Nivel de Valor Unitario por Categoría:**  
   * En importación, las dos categorías con suela de caucho/plástico (`640399` y `640411`) suman conjuntamente el **98.98% de los pares** (66.24% y 32.74% respectivamente, sumando 743.37 millones de pares), registrando cocientes de **$23.54** y **$26.22 USD/par**.  
   * En contraste, la categoría `640420` (*Calzado con suela de cuero y parte superior de cuero/material similar*) representa únicamente el **1.03% de los pares importados** (7.72 millones de pares), pero registra el cociente unitario más elevado del conjunto: **$45.22 USD/par** en importación y **$41.42 USD/par** en exportación.
3. **Distribución por Socio Comercial en los Registros Disponibles:**  
   En importaciones, los mayores registros de valor se concentran en Grecia ($2,109.63 M USD), Países Bajos ($1,754.06 M USD) y Vietnam ($1,517.65 M USD con un cociente de $29.15/par). En exportaciones, Indonesia encabeza los registros en valor y volumen ($2,286.29 M USD y 104.74 millones de pares a $21.83/par).

---

### 5.3. Dos Limitaciones Metodológicas Infranqueables

1. **El Valor Comercial Registrado no Equivale al Precio Minorista de Venta (PVP):**  
   El cociente unitario refleja el valor comercial declarado en frontera en la base de comercio exterior. **No equivale al precio de venta al consumidor final en tienda (PVP)**, ya que no contempla costos arancelarios de nacionalización en Bolivia, transporte interno, almacenamiento de producto terminado, costos de comercialización ni el margen del canal minorista.
2. **Referencia Externa de Mercado (España no es la Operación de MANACO):**  
   Los datos provienen de transacciones de comercio exterior reportadas por España como país reportante. **No representan las ventas, costos de producción, inventarios ni la rentabilidad de MANACO en Bolivia.** Las conclusiones describen dinámicas del conjunto de datos externo y deben contrastarse con los datos transaccionales internos de la empresa.

---

### 5.4. Pregunta Estratégica Reformulada para MANACO

> **"A partir de la diferencia observada en los registros externos, donde el calzado con suela de cuero y parte superior de cuero/material similar presenta un valor comercial aproximado por par sensiblemente más alto ($41.42 en exportación y $45.22 en importación) que el calzado con suela de caucho/plástico ($23-$26 USD/par), ¿qué categorías de producto convendría priorizar, mantener o abastecer externamente en MANACO una vez evaluados los datos internos de costos de fabricación, capacidad instalada en planta, rotación de inventarios y demanda efectiva del consumidor boliviano?"**

---

## 6. Notas Metodológicas Obligatorias para el Tablero

Inserta un cuadro de texto en la parte inferior del tablero con las siguientes notas para contextualizar la visualización:

> **Notas Metodológicas del Modelo:**
> 1. **Fuente de Datos:** Registros de comercio exterior reportados por España (2020–2024), utilizados como conjunto de datos referencial externo para el caso MANACO.
> 2. **Alcance de los Resultados:** Los indicadores describen estrictamente los 240 registros del archivo disponibles en el Data Warehouse.
> 3. **Variabilidad de Cobertura Temporal:** La cantidad de transacciones registradas varía por año (2020: 28, 2021: 34, 2022: 46, 2023: 50, 2024: 82); el incremento de registros del archivo no debe interpretarse como crecimiento general del mercado.
> 4. **Granularidad del Archivo:** Se identificaron 10 combinaciones dimensionales repetidas (20 filas); dado que su significado no está documentado en la fuente original, se conservan las 240 filas definiendo la granularidad como una fila del archivo fuente.
> 5. **Indicador por Par:** Calculado como cociente ponderado $\frac{\sum \text{Valor USD}}{\sum \text{Cantidad Pares}}$. No representa el precio de venta minorista, el margen de ganancia ni el costo de manufactura de MANACO en Bolivia.
