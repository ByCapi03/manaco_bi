# 📖 Manual de Usuario y Guía de Métricas: MANACO BI Suite
**Sistema de Inteligencia de Negocios, Costos y Control de Inventarios con Visión Artificial**  
*Documento de Consulta Rápida para Gerencia, Operadores y Analistas*

---

## 🎯 1. ¿Cómo está Organizada la Pantalla? (Barra Lateral Izquierda)

Para facilitarte el control total del negocio, la aplicación ahora cuenta con un **Menú Lateral a la Izquierda** organizado en dos secciones principales:

```
┌───────────────────────────────────────────────────┐
│               BARRA LATERAL IZQUIERDA             │
├───────────────────────────────────────────────────┤
│ 📊 Dashboard General   (Vista ejecutiva completa) │
│ 📷 Cámara IA Almacén   (Escaneo e ingreso rápido) │
├───────────────────────────────────────────────────┤
│         APARTADO: 5 PROBLEMAS EMPRESARIALES       │
│ 💰 1. Costos y Precios    (¿Fabricar o importar?) │
│ 📦 2. Inventario y Bodega (Existencias y auditoría│
│ 👞 3. Productos y Portafolio (Básico vs Confort)  │
│ 📈 4. Demanda y Planificación (Pronósticos y reord│
│ 🏬 5. Ventas y Canales    (Rendimiento comercial) │
└───────────────────────────────────────────────────┘
```

Al hacer clic en cualquier opción del lado izquierdo, la pantalla central cambia de inmediato sin recargar la página.

---

## 📊 2. Entendiendo el Dashboard General (Pantalla Principal)

Esta pantalla te muestra la **fotografía en tiempo real** de toda la fábrica y bodega de calzados.

### A. Los 4 Indicadores Superiores (KPIs)
1. **Stock Total en Almacén (90 pares):**  
   - *¿Qué es?* La suma física de todos los calzados disponibles en la bodega central.  
   - *¿Por qué 90?* Empezamos con 15 pares de cada uno de los 6 modelos del catálogo ($6 \times 15 = 90$ pares).  
   - *Capacidad ocupada (10%):* La bodega tiene capacidad para 900 pares. Al tener 90 pares, estamos usando el 10% del espacio disponible.
2. **Valorización Económica (Bs. 26,400.00 / $us. 3,793.10):**  
   - *¿Qué es?* El valor monetario de todos los calzados que tienes guardados en almacén.  
   - *¿Cómo se calcula?* Se multiplica el stock de cada zapato por su precio unitario de catálogo ($15 \times \text{Precio}$).
3. **Categoría Líder en Stock:**  
   - *¿Qué es?* La categoría de calzado que actualmente tiene mayor volumen de pares disponibles (Deportivo o Casual).
4. **Ingestas por Visión IA:**  
   - *¿Qué es?* El conteo de zapatos que han sido registrados ingresando a almacén usando la cámara web con Inteligencia Artificial.

---

### B. Las 6 Tarjetas de Productos (Catálogo Manaco)

En el centro del Dashboard verás seis tarjetas con íconos de calzado:

| Producto | Código SA6 | ¿Qué Calzado Es? | Stock Actual | Stock Mínimo | Precio Sugerido | Estado |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **1. Deportivo Básico** | 640411 | Zapatilla deportiva suela goma | 15 pares | 30 pares | **Bs. 295.08** ($42.40 USD) | ⚠️ Stock Bajo |
| **2. Deportivo Confort** | 640411 | Zapatilla ergonómica / gel | 15 pares | 25 pares | **Bs. 336.05** ($48.28 USD) | ⚠️ Stock Bajo |
| **3. Casual Básico** | 640399 | Zapato mocasín / cuero diario | 15 pares | 20 pares | **Bs. 279.82** ($40.20 USD) | ⚠️ Stock Bajo |
| **4. Casual Confort** | 640399 | Zapato cuero plantilla acolchada | 15 pares | 15 pares | **Bs. 319.69** ($45.93 USD) | ⚠️ Stock Bajo |
| **5. Vestir Básico** | 640420 | Zapato formal suela de cuero | 15 pares | 10 pares | **Bs. 468.94** ($67.38 USD) | ✓ Óptimo |
| **6. Vestir Confort** | 640420 | Zapato Oxford cuero premium | 15 pares | 10 pares | **Bs. 522.32** ($75.05 USD) | ✓ Óptimo |

* **¿Por qué dice "⚠️ Stock Bajo"?**  
  Porque el stock actual (15 pares) está por debajo del stock mínimo de seguridad (por ejemplo, Deportivo Básico requiere mínimo 30 pares para no sufrir desabastecimiento si las ventas suben).
* **¿Por qué Vestir dice "✓ Óptimo"?**  
  Porque tiene 15 pares y su mínimo requerido es de solo 10 pares.

---

## 📷 3. Cómo Funciona el Ingreso de Inventario con la Cámara IA

**¡Ya no necesitas formularios manuales ni modales molestos para mover inventario!** Todo el ingreso físico se hace de forma visual e inteligente:

1. Ve a la opción **"📷 Cámara IA Almacén"** en la barra izquierda.
2. Presiona el botón verde **"Iniciar Cámara Web"**.
3. Acerca el zapato al recuadro de escaneo de la cámara.
4. La Inteligencia Artificial detectará de inmediato la categoría (por ejemplo: *Calzado Deportivo, 88% de confianza*).
5. Como una cámara no puede adivinar si el zapato tiene plantilla ortopédica o plantilla básica, el sistema te mostrará dos botones directos:
   - `[ Ingresar Deportivo Básico (+1 par) ]`
   - `[ Ingresar Deportivo Confort (+1 par) ]`
6. Al presionar el botón de tu modelo:
   - Se reproduce un sonido armónico de confirmación (`Ding`).
   - El inventario suma inmediatamente **+1 par** a ese modelo.
   - El Dashboard General se actualiza en tiempo real.
7. Si te equivocaste, solo presiona **"↩️ Deshacer Último"** y el par se descuenta de nuevo.

---

## 💰 4. Guía de los 5 Problemas Empresariales (Apartado Izquierdo)

Cada uno de los 5 botones del apartado izquierdo resuelve una pregunta estratégica de negocio:

---

### Problema 1: Costos y Precios (¿Fabricar en Bolivia o Importar?)
* **La Pregunta:** ¿Nos sale más barato fabricar un lote de zapatos en la fábrica de Cochabamba o traerlo importado de Asia/Europa? ¿A qué precio debemos venderlo para ganar dinero?
* **Los Números que Ves:**
  - **Referencia Externa ($27.80, $26.15, $45.53 USD/par):** Es lo que cuesta en promedio un par de zapatos en la aduana según el archivo oficial de Excel (`BDatos_MANACO.xlsx`).
  - **Gastos Adicionales ($4.00 a $7.00 USD/par):** Costos de flete marítimo, seguro y trámites para poner el calzado en Bolivia.
  - **Costo Estimado Unitario:** Referencia + Gastos (Ej: $27.80 + $4.00 = **$31.80 USD/par**).
  - **Margen Objetivo (25% o 30%):** La ganancia que la empresa quiere obtener sobre el precio final de venta.
  - **Precio Propuesto:** Se calcula con la fórmula comercial:
    $$\text{Precio} = \frac{\text{Costo Estimado}}{1 - \text{Margen}} = \frac{31.80}{1 - 0.25} = \frac{31.80}{0.75} = \$42.40 \text{ USD (Bs. 295.08)}$$
  - **Punto de Indiferencia (Q*):** Es la cantidad exacta de pares donde los dos costos empatan. Si produces **más** de esa cantidad, te conviene fabricar localmente; si produces **menos**, te conviene importar.

---

### Problema 2: Inventario y Bodega (Control de Existencias)
* **La Pregunta:** ¿Cuántos pares tenemos en total, qué categorías tienen quiebre y cómo auditamos cada salida?
* **Los Números que Ves:**
  - Entradas acumuladas de pares.
  - Salidas por despachos de venta.
  - Productos en alerta roja por estar bajo el stock de seguridad.
  - **Regla Estricta:** El sistema nunca permite ventas que dejen el inventario en negativo. Si intentas sacar 50 pares y solo tienes 15, el sistema rechaza la operación automáticamente.

---

### Problema 3: Productos y Diferenciación (Portafolio de Calzados)
* **La Pregunta:** ¿Por qué no debemos competir en zapatillas sintéticas baratas y qué ventaja tiene el calzado de cuero?
* **Los Números que Ves:**
  - **Casual Cuero (78.6% del mercado):** Es la categoría reina en volumen comercial internacional.
  - **Deportivo (20.7%):** Dominado por gigantes mundiales de bajo costo.
  - **Formal Vestir (0.8% del volumen, pero $45.53 USD/par):** Es el calzado de mayor valor unitario.
  - **Línea Básico (25% de margen):** Modelos de entrada para el día a día.
  - **Línea Confort (30% de margen):** Modelos con cueros seleccionados y ergonomía superior.

---

### Problema 4: Demanda y Planificación (Pronósticos y Reposición)
* **La Pregunta:** ¿Cuántos pares nos van a comprar en los próximos 7 días y cuántos debemos pedir a producción para no quedarnos sin stock?
* **Los Números que Ves:**
  - **Ventas Previstas (7 Días):** Demanda proyectada mediante modelo de Promedio Móvil.
  - **MAE (1.02 pares):** *Error Absoluto Medio*. Significa que el pronóstico es de alta precisión: en promedio solo se equivoca por 1 solo par de zapatos respecto a la realidad.
  - **Punto de Reorden:** El nivel de inventario crítico en el que debes pedir reposición.
  - **Sugerencia de Reposición:**
    $$\text{Reposición} = (\text{Demanda Prevista} \times \text{Días de Entrega}) + \text{Stock de Seguridad} - \text{Stock Actual}$$
  - **Botón "Confirmar Reposición":** Con un solo clic apruebas el pedido y los pares ingresan a bodega formalmente.

---

### Problema 5: Ventas y Canales (Desempeño Comercial)
* **La Pregunta:** ¿Por dónde vendemos más y por qué hay datos que dicen "No disponible"?
* **Los Números que Ves:**
  - **Tiendas Propias (58% del volumen):** El canal principal físico de Manaco.
  - **Distribuidores Mayoristas (27%):** Ventas en lotes a comerciantes de todo el país.
  - **E-commerce / Tienda Online (15%):** Ventas por internet.
  - **Picos en Mayo y Diciembre:** El gráfico temporal muestra los incrementos del Día de la Madre (mayo) y fiestas de fin de año con aguinaldo (diciembre).
  - **¿Por qué "Conversión Digital" dice "No disponible"?**  
    *Por honestidad y rigor analítico:* Para calcular cuántas personas compran en una web necesitas registrar las visitas (visitas y carritos). Como el archivo Excel solo tiene datos de aduana y no de visitas a una tienda web, el sistema **no inventa números falsos** y te avisa transparentemente que esa métrica requiere telemetría digital adicional.

---

## 💡 5. Resumen de Preguntas Frecuentes

| Duda | Respuesta Rápida |
| :--- | :--- |
| **¿Cómo cambio de Dólares ($us) a Bolivianos (Bs)?** | En la parte inferior de la barra izquierda tienes los botones `$us` y `Bs.`, además de una casilla para cambiar el tipo de cambio oficial (por defecto Bs. 6.96). |
| **¿Si cambio los precios hoy, se alteran las ventas pasadas?** | **No.** Cada venta guarda en su propio recibo el precio exacto con el que se vendió ese día. Las ventas históricas no se tocan. |
| **¿El sistema hace compras automáticas solo?** | **No.** La sugerencia de reposición te avisa cuántos pares hacen falta, pero tú debes hacer clic en "Confirmar Reposición" para que se apruebe. |
