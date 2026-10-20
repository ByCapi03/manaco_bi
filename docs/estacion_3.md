# Estación 3: Diseño de la Propuesta Estratégica (30 minutos)
**Programa:** Ingeniería de Sistemas, Ciencia de Datos e Inteligencia de Negocios (6.° Semestre)  
**Modalidad:** Aprendizaje Basado en Retos (ABR)  
**Proyecto:** Manaco BI  
**Rol:** Equipo Consultor de Ciencia de Datos y Estrategia Empresarial  

---

# FICHA DE PROPUESTA ESTRATÉGICA (ONE-PAGER EJECUTIVO)

| **Nombre del Proyecto** | **SIM-BI:** Sistema de Inteligencia de Mercado y Planificación de Demanda para MANACO |
| :--- | :--- |
| **Horizonte Temporal** | 3 Años (2026 - 2029) |
| **Patrocinador Ejecutivo** | Gerencia General de Manaco |
| **Áreas Involucradas** | Comercial y Marketing, Producción y Planta, Logística y Almacén, Finanzas, Tecnologías de Información (TI). |

---

## 1. Definición del Problema Empresarial
Manaco enfrenta un **descalce estructural entre la oferta fabril y la demanda real del mercado**, agravado por:
1. **Presión extrema de importaciones económicas:** Más de 288 millones de pares ingresando al mercado en categorías deportivas/sintéticas a costos aduaneros de ~$23-$26 USD/par.
2. **Altos costos de inmovilización:** Exceso de inventario en bodega (sobrestock de modelos no competitivos) y quiebres de stock en líneas de alta demanda.
3. **Decisiones a ciegas (Silos de Información):** Falta de integración entre la inteligencia del mercado exterior y los sistemas transaccionales internos (ERP de manufactura y POS de tiendas).

---

## 2. Solución Analítica de Ciencia de Datos Propuesta

### Arquitectura de la Solución: "Ecosistema Analítico MANACO"
La solución articula tres componentes integrados:
1. **Data Warehouse Corporativo (`manaco_dw` en PostgreSQL):** Repositorio centralizado con esquema estrella que consolida datos aduaneros de mercado exterior y datos internos de ventas por tienda, inventario y costos de planta.
2. **Tableros de Control Estratégico y Operativo (Power BI):** 
   - *Tablero de Inteligencia Competitiva:* Monitoreo continuo de importaciones, precios por par aduaneros y nuevos socios proveedores.
   - *Tablero de Rendimiento Comercial:* Control de rotación de stock por tienda, ticket promedio y margen de contribución.
3. **Módulo Predictivo de Planificación de la Demanda (*Demand Forecasting* en Python):** Modelo de series temporales y machine learning que proyecta la demanda por categoría arancelaria y estacionalidad (campaña escolar, festividades, invierno) para orientar el Plan Maestro de Producción.

* **Datos Necesarios:**
  - *Externos:* Registros arancelarios SA6 de comercio exterior (valor comercial en USD, pares, país socio).
  - *Internos:* Ventas diarias por tienda/SKU (POS), costos estándar y reales de producción (ERP) y niveles de inventario por almacén (WMS).
* **Decisiones que Apoyará:**
  - Definición del volumen exacto a producir por modelo y mes (reduciendo sobrestock).
  - Decisión estratégica de portafolio: fabricación local de líneas de cuero de alta rentabilidad vs. importación/maquila de calzado deportivo económico.
  - Políticas dinámicas de precios y descuentos por canal.

---

## 3. Propuestas de Objetivos SMART para los Próximos 3 Años e Indicadores (KPIs)

> **Nota Metodológica:** Dado que el caso no provee balances contables ni línea base histórica interna de Manaco en Bolivia, los siguientes objetivos e indicadores se formulan como **propuestas estratégicas e hipótesis operativas de trabajo**, sujetas a calibración una vez integrados los datos reales del ERP de planta y POS de tiendas.

| N.° | Propuesta de Objetivo SMART (3 Años) | Indicador Clave (KPI) | Línea Base Hipotética (Año 0) | Meta Propuesta (Año 3) |
| :---: | :--- | :--- | :---: | :---: |
| **1** | **Optimización de Inventarios y Cadena de Suministro:**<br>Reducir los días promedio de permanencia en inventario de producto terminado de 95 a 60 días para el cierre de 2029 mediante planificación predictiva. | **DSI (Days Sales of Inventory):**<br>$\frac{\text{Inventario Promedio}}{\text{Costo de Ventas}} \times 365$ | 95 días | **$\le$ 60 días** |
| **2** | **Rentabilidad y Reposicionamiento del Portafolio:**<br>Incrementar la participación del calzado de cuero de alto valor en los ingresos brutos del 28% al 45% en 36 meses, priorizando la capacidad de planta. | **Mix de Ventas en Cuero (%):**<br>$\frac{\text{Ventas Línea Cuero (USD)}}{\text{Ventas Totales (USD)}} \times 100$<br>**Margen Bruto Global (%)** | Cuero: 28%<br>Margen: 31% | **Cuero: 45%**<br>**Margen: $\ge$ 40%** |
| **3** | **Adopción y Gobernanza Analítica:**<br>Alcanzar un 90% de adopción del Data Warehouse y tablero Power BI en los comités ejecutivos y reducir el error de pronóstico a menos del 12%. | **Tasa de Adopción de BI (%):** Comités con soporte en datos.<br>**MAPE (Error del Pronóstico):** Desviación demanda real vs pronóstico. | Adopción: 15%<br>MAPE: > 35% | **Adopción: $\ge$ 90%**<br>**MAPE: $\le$ 12%** |

---

## 4. Coordinación entre Áreas y Gobernanza

```
                             GERENCIA GENERAL
                  (Sponsor y Alineación Estratégica)
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  GERENCIA COMERCIAL       GERENCIA DE PLANTA       GERENCIA LOGÍSTICA
  • Retroalimentación POS  • Ajuste de órdenes de   • Gestión de stock en
  • Validación de precios    fabricación según BI     bodegas y tiendas
  • Campañas comerciales   • Foco en líneas cuero   • Reducción de mermas
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                       EQUIPO DE CIENCIA DE DATOS & TI
               • Mantenimiento del DW PostgreSQL y Power BI
               • Calibración del modelo predictivo de demanda
               • Capacitación y gobernanza de datos
```

* **Comité Mensual de Datos y Operaciones (S&OP):** Las gerencias Comercial, Planta y Logística se reúnen mensualmente alrededor del tablero Power BI para revisar la demanda proyectada y aprobar las órdenes de fabricación.

---

## 5. Matriz de Riesgos de Implementación y Medidas de Mitigación

| Riesgo Identificado | Impacto / Severidad | Medida de Mitigación Concreta |
| :--- | :---: | :--- |
| **Riesgo 1: Resistencia Cultural al Cambio y Falta de Adopción**<br>Los mandos medios de producción y ventas prefieren seguir decidiendo basados en intuición o planillas de Excel aisladas. | **ALTO** | • **Programa de Alfabetización de Datos (*Data Literacy*):** Talleres prácticos adaptados al lenguaje de cada área.<br>• **Co-diseño de Dashboards:** Involucrar a los gerentes de tienda y planta en la definición de métricas para garantizar su utilidad diaria.<br>• **Directriz Gerencial:** No se aprueban órdenes de producción que no estén sustentadas en el reporte oficial de Power BI. |
| **Riesgo 2: Calidad e Inconsistencia en los Datos Fuente (ERP/POS)**<br>Registros incompletos, duplicados o errores de digitación en tiendas que introduzcan sesgos en los modelos analíticos. | **ALTO** | • **Pipeline ETL Automatizado con Reglas de Validación:** Scripts de validación en Python que rechacen o alerten registros corruptos antes de cargar al Data Warehouse.<br>• **Estandarización de Códigos de Producto (Catálogo Único):** Homologar códigos internos con la clasificación arancelaria SA6.<br>• **Auditorías de Integridad Quincenales** lideradas por el área de TI. |

---

## 6. Viabilidad del Proyecto

* **Técnica:** Utiliza infraestructura de código abierto y herramientas existentes en el mercado (PostgreSQL para almacenamiento, Python para pipelines y modelos, Power BI para visualización).
* **Económica:** Inversión de bajo costo de licencias con un retorno inmediato al liberar capital inmovilizado en sobrestock y capturar mayor margen unitario en calzado de cuero.
* **Operativa:** Implementación gradual por fases (Fase 1: BI descriptivo y DW; Fase 2: Pronóstico de demanda; Fase 3: Optimización integral de inventarios).

---

## 7. Producto Esperado: Respuestas Directas a las Preguntas Clave

A continuación se sintetizan las respuestas literales a las cuatro preguntas exigidas en el producto esperado de la Estación 3:

### 1. ¿Qué problema resolverá la solución?
Resolverá el **descalce crónico entre la producción fabril y la demanda del mercado**, el cual genera sobrestock de modelos sintéticos y deportivos que no pueden competir frente al ingreso masivo de importaciones asiáticas de bajo costo ($23-$26 USD/par). Además, eliminará la toma de decisiones fragmentada entre las gerencias de ventas y producción al proporcionar una fuente única de verdad analítica.

### 2. ¿Qué datos necesita?
Requiere la integración de dos vertientes de información:
* **Datos Externos de Mercado:** Registros de comercio exterior arancelarios (código SA6, valor comercial en USD, cantidad de pares y país de origen/destino).
* **Datos Internos Transaccionales:** Ventas diarias y devoluciones por tienda/SKU (sistemas POS), costos directos de mano de obra y materia prima por modelo (ERP de planta) y niveles de inventario físico y rotación por almacén (WMS).

### 3. ¿Cómo se medirá el resultado?
Se medirá a través de tres métricas de impacto cuantitativo (KPIs SMART) en un horizonte de 3 años:
1. **Días de Inventario Disponible (DSI):** Reducción de 95 a un máximo de 60 días de producto inmovilizado.
2. **Mix de Ventas y Margen de Línea Cuero:** Aumento de la cuota de ventas de calzado de cuero del 28% al 45% y margen bruto global $\ge 40\%$.
3. **Precisión del Pronóstico y Adopción:** Reducción del margen de error de pronóstico de demanda a un $\text{MAPE} \le 12\%$ y una tasa de adopción de BI $\ge 90\%$ en comités gerenciales.

### 4. ¿Es viable con los recursos disponibles?
**Sí, es 100% viable:**
* **Técnicamente:** Aprovecha la pila tecnológica estándar y libre de costos exorbitantes (PostgreSQL para la base de datos, Python para analítica/ETL y Power BI Desktop para cuadros de mando).
* **Económicamente:** El proyecto se autofinancia con el ahorro generado por la reducción de mermas e inventario ocioso, y el mayor margen del calzado de cuero.
* **Operativamente:** Se implementa de forma escalonada por módulos sin interrumpir la operación cotidiana de las fábricas ni de las tiendas.
