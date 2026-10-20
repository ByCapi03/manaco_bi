# Estación 1: Comprensión del Caso Empresarial MANACO
**Programa:** Ingeniería de Sistemas, Ciencia de Datos e Inteligencia de Negocios (6.° Semestre)  
**Modalidad:** Aprendizaje Basado en Retos (ABR)  
**Rol:** Equipo Consultor de Ciencia de Datos y Estrategia Empresarial  

---

## 1. Análisis Integral del Caso (Actividades a y b)

### 1.1. Contexto Empresarial
**Manaco** es la empresa manufacturera y comercializadora de calzado más emblemática de Bolivia. Con décadas de trayectoria, ha cubierto el mercado nacional a través de tiendas propias y distribuidores. Sin embargo, en el trienio reciente su sostenibilidad se ha visto amenazada por un entorno de alta volatilidad y presión competitiva.

### 1.2. Factores Externos e Internos

```
                          ENTORNO MANACO
  ┌─────────────────────────────────────────────────────────────┐
  │ FACTORES EXTERNOS (Oportunidades y Amenazas)                │
  │ • Importación masiva de calzado asiático a bajo costo.      │
  │ • Cambios de hábito: auge del comercio digital y casual.   │
  │ • Contrabando e informalidad en el mercado local.           │
  │ • Fluctuaciones cambiarias y costos de logística global.    │
  └──────────────────────────────┬──────────────────────────────┘
                                 │ Presión Competitiva
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ FACTORES INTERNOS (Fortalezas y Debilidades)                │
  │ • Alta reputación de marca y calidad en calzado de cuero.   │
  │ • Presión sobre costos de producción y almacenamiento.      │
  │ • Falta de integración entre datos de mercado y ventas.     │
  │ • Decisiones comerciales reactivas sin analítica avanzada.  │
  └─────────────────────────────────────────────────────────────┘
```

---

## 2. Diagnóstico de Problemas por Área Funcional (Actividad c y d)

| Área Funcional | Problema Identificado | Información Cuantitativa Necesaria | Información Cualitativa Necesaria |
| :--- | :--- | :--- | :--- |
| **1. Gestión Administrativa y Organizacional** | Silos departamentales; las decisiones estratégicas no se basan en evidencia de datos compartida. | Tiempos de ciclo de decisión; desviación presupuestaria por gerencia. | Nivel de madurez analítica; grado de colaboración interdepartamental. |
| **2. Producción, Inventarios y Logística** | Altos costos de almacenamiento y desalineación entre volumen de producción y demanda real. | Stock inmovilizado por SKU; días de inventario; costo de almacenamiento; mermas. | Cuellos de botella en planta; fiabilidad de proveedores de materias primas. |
| **3. Competitividad y Mercado** | Pérdida de cuota de mercado frente a calzado sintético/deportivo importado a precios reducidos. | Volúmenes y valores arancelarios de importación (códigos SA6); precios unitarios CIF/FOB. | Percepción de marca de Manaco frente a marcas importadas; tendencias de moda. |
| **4. Rentabilidad y Estructura de Costos** | Erosión del margen bruto por incremento de materias primas y rigidez en costos fijos de planta. | Margen de contribución por línea; desglose de costo directo vs indirecto por par fabricado. | Estrategias de fijación de precios; políticas de descuentos comerciales. |
| **5. Clientes, Segmentación y Marketing** | Falta de trazabilidad en hábitos de consumo y retraso en el despliegue del canal digital/e-commerce. | Ticket promedio por cliente; frecuencia de recompra; ventas por canal físico vs online. | Grado de satisfacción postventa; razones de abandono de compra de calzado formal. |
| **6. Calidad e Integración de Datos** | Dispersión de fuentes: datos de mercado aislados de los sistemas transaccionales internos (ERP/POS). | % de duplicados, valores nulos y registros desactualizados en bases de datos. | Protocolos de gobernanza de datos; estándares de captura en tiendas. |

---

## 3. Respuestas a las Preguntas Orientadoras

### ¿Cuáles son los principales desafíos que enfrenta Manaco?
1. **Diferenciación estratégica:** Evitar una "guerra de precios destructiva" contra el calzado importado sintético/deportivo de bajo costo, fortaleciendo líneas de alto valor (calzado de cuero nacional).
2. **Transformación analítica:** Romper los silos de información e integrar un Data Warehouse unificado para alinear producción, compras y ventas.
3. **Optimización operativa:** Reducir costos de almacenamiento y agilizar la cadena de suministro hacia canales modernos y comercio electrónico.

### ¿Qué factores podrían estar afectando su rentabilidad?
- **Costos de capacidad ociosa y sobrestock:** Mantener inventarios de baja rotación encarece el capital de trabajo.
- **Competencia en precios por unidad:** En calzado sintético/deportivo, los proveedores asiáticos ingresan productos a valores declarados por par muy inferiores a los costos de producción bolivianos.
- **Mix de producto desfavorable:** Sobreproducir categorías de bajo margen en lugar de focalizarse en las líneas donde Manaco posee ventaja de calidad.

### ¿Qué diferencias existen entre las regiones y las líneas de productos?
- **Por líneas de producto:**
  - *Calzado deportivo con suela de caucho/plástico:* Altísimo volumen de importación, dominado por economías de escala internacionales.
  - *Calzado de cuero con suela de cuero o goma:* Segmento de mayor valor agregado, donde Manaco posee tradición artesanal e industrial defendible.
- **Por regiones:** Las ciudades del eje central (La Paz, Santa Cruz, Cochabamba) muestran mayor penetración de canales digitales y competencia comercial, mientras que mercados intermedios demandan calzado escolar y de trabajo resistente.

### ¿Qué información adicional se necesitaría para validar si los problemas son relevantes?
- **Datos internos transaccionales:** Registro de ventas diarias por tienda (POS), costo estándar vs real por par producido (ERP) y niveles de stock por bodega.
- **Datos de comercialización:** Precios de venta al público en tiendas minoristas (para comparar el valor comercial de aduana contra el precio de estantería).

### ¿Qué decisiones empresariales mejorarían si la organización aprovechara mejor sus datos?
- **Planificación de la Producción (Demand Planning):** Fabricar lo que el mercado absorbe según estacionalidad (ej. campaña escolar), reduciendo liquidaciones forzadas.
- **Estrategia de Portafolio y Precios:** Identificar si conviene producir localmente o maquilar/importar ciertas referencias deportivas, concentrando la fábrica en líneas rentables de cuero.
- **Gestión de Compras y Proveedores:** Negociar insumos basándose en tendencias globales de precios de materiales.

### ¿Cuáles son los principales riesgos de tomar decisiones sin información suficiente?
- **Destrucción de margen:** Rebajar precios a ciegas intentando competir con importaciones que tienen subsidios de origen o aranceles mínimos.
- **Descalce de inventario (Stock-out vs Sobrestock):** Quedarse sin existencias de productos estrella y sobrealmacenar modelos que el consumidor ya no prefiere.
- **Inversión infructuosa de capital:** Destinar presupuesto a líneas de producción inviables frente a la competencia global.

---

## 4. Producto Esperado: Matriz de Problemas Prioritarios y Preguntas de Análisis

| N.° | Problema Prioritario | Justificación e Impacto Empresarial | Tipo de Datos Necesarios | Preguntas Clave de Análisis |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Presión competitiva por importaciones de calzado económico** | Amenaza directa a la cuota de mercado local; reduce el margen de fijación de precios en gamas populares. | **Datos Externos** *(Base de Datos adjunta)*: Registros de importación por código SA6, país socio, valor USD y pares. | • ¿Qué categorías de calzado presentan mayor crecimiento de volumen importado en los últimos 5 años?<br>• ¿Cuáles son los principales países abastecedores de calzado de bajo costo? |
| **2** | **Inadecuada lectura del valor comercial por par frente al precio minorista** | Confundir el valor declarado en frontera (CIF/FOB) con el precio al consumidor final genera comparaciones erróneas de rentabilidad. | **Datos Externos e Internos**: Valor por par del dataset externo + precios de venta en tiendas Manaco + aranceles e impuestos locales. | • ¿Cuál es la brecha entre el valor por par importado ponderado y el costo de producción interno?<br>• ¿Cómo varía el valor por par según el socio comercial? |
| **3** | **Falta de alineación entre portafolio de producción y demanda real** | Riesgo de producir calzado con baja demanda o donde no se puede competir con precios de importación. | **Datos Internos**: Ventas por línea de calzado, rotación de inventarios y margen de contribución unitario. | • ¿Qué líneas de calzado presentan mayor tiempo de permanencia en bodega?<br>• ¿En qué categorías tiene Manaco un margen defendible frente a la oferta externa? |
| **4** | **Dependencia y concentración geográfica de socios comerciales** | La concentración en pocos proveedores o destinos genera vulnerabilidad ante disrupciones de fletes y logística. | **Datos Externos**: Distribución de importaciones y exportaciones por socio comercial (evitando doble conteo de "Mundo"). | • ¿Existe dependencia crítica de 2 o 3 socios comerciales?<br>• ¿Qué destinos de exportación presentan oportunidades de expansión para Manaco? |
| **5** | **Aislamiento de la información (Falta de Data Warehouse unificado)** | Decisiones fragmentadas por falta de un repositorio único que vincule inteligencia de mercado con indicadores de gestión. | **Datos Técnicos / Arquitectura**: Tablas dimensionales en PostgreSQL (DW) conectadas a tableros de control en Power BI. | • ¿Cómo modelar un esquema estrella que permita cruzar comercio exterior hoy y datos de planta mañana?<br>• ¿Qué KPIs estratégicos debe monitorear la Gerencia semanalmente? |

---

## 5. Reglas Técnicas Fundamentales para la Defensa Académica

1. **Segregación de Totales "Mundo":**
   Los registros que representen agregados globales ("Mundo" o "World") deben aislarse en la dimensión socio (`tipo_socio = 'Mundo'`) para no duplicar sumas al totalizar por país socio (`tipo_socio = 'País'`).
2. **Tratamiento de Cantidades Desconocidas:**
   Las cantidades en pares ausentes deben preservarse como `NULL` (desconocidas) y nunca sustituirse por `0`, evitando falsear el volumen real del mercado.
3. **Cálculo Ponderado de Valor por Par:**
   $$\text{Valor por Par} = \frac{\sum \text{Valor Total USD}}{\sum \text{Cantidad Pares}}$$
   No se debe promediar la columna unitaria `Valor_USD_por_par` (el promedio de promedios genera un sesgo estadístico inadmisible).
