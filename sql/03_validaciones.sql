-- =====================================================================
-- 03_validaciones.sql
-- Consultas reutilizables para verificar la integridad del Data Warehouse
-- Base de datos: manaco_dw
-- =====================================================================

-- 1. CONTEO TOTAL DE FILAS EN fact_comercio (Esperado: 240)
SELECT 
    COUNT(*) AS total_filas_fact,
    CASE WHEN COUNT(*) = 240 THEN 'PASS' ELSE 'FAIL' END AS estado
FROM fact_comercio;


-- 2. UNICIDAD DE CLAVE PRIMARIA EN fact_comercio (Esperado: 0 duplicados)
SELECT 
    id_hecho, 
    COUNT(*) AS repeticiones
FROM fact_comercio
GROUP BY id_hecho
HAVING COUNT(*) > 1;


-- 3. INTEGRIDAD REFERENCIAL: CLAVES FORÁNEAS HUÉRFANAS (Esperado: 0 en todas)
SELECT 
    (SELECT COUNT(*) FROM fact_comercio c LEFT JOIN dim_periodo p ON c.id_periodo = p.id_periodo WHERE p.id_periodo IS NULL) AS huerfanos_periodo,
    (SELECT COUNT(*) FROM fact_comercio c LEFT JOIN dim_producto pr ON c.id_producto = pr.id_producto WHERE pr.id_producto IS NULL) AS huerfanos_producto,
    (SELECT COUNT(*) FROM fact_comercio c LEFT JOIN dim_reportante r ON c.id_reportante = r.id_reportante WHERE r.id_reportante IS NULL) AS huerfanos_reportante,
    (SELECT COUNT(*) FROM fact_comercio c LEFT JOIN dim_socio s ON c.id_socio = s.id_socio WHERE s.id_socio IS NULL) AS huerfanos_socio,
    (SELECT COUNT(*) FROM fact_comercio c LEFT JOIN dim_flujo f ON c.id_flujo = f.id_flujo WHERE f.id_flujo IS NULL) AS huerfanos_flujo;


-- 4. CONTEO DE FILAS POR FLUJO COMERCIAL (Esperado: 120 Exportación, 120 Importación)
SELECT 
    f.flujo_comercial,
    COUNT(c.id_hecho) AS total_filas
FROM fact_comercio c
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
GROUP BY f.flujo_comercial
ORDER BY f.flujo_comercial;


-- 5. CONTEO DE FILAS POR AÑO (Esperado: 2020: 28, 2021: 34, 2022: 46, 2023: 50, 2024: 82)
SELECT 
    p.anio,
    COUNT(c.id_hecho) AS total_filas
FROM fact_comercio c
JOIN dim_periodo p ON c.id_periodo = p.id_periodo
GROUP BY p.anio
ORDER BY p.anio;


-- 6. IDENTIFICACIÓN DE LAS 10 COMBINACIONES DIMENSIONALES REPETIDAS (Esperado: 10 grupos, 20 filas)
WITH repetidos AS (
    SELECT 
        c.id_periodo,
        c.id_producto,
        c.id_reportante,
        c.id_socio,
        c.id_flujo,
        COUNT(*) AS conteo_repeticiones
    FROM fact_comercio c
    GROUP BY c.id_periodo, c.id_producto, c.id_reportante, c.id_socio, c.id_flujo
    HAVING COUNT(*) > 1
)
SELECT 
    COUNT(*) AS combinaciones_repetidas,
    SUM(conteo_repeticiones) AS total_filas_involucradas
FROM repetidos;


-- 7. CONSERVACIÓN DE TOTALES POR FLUJO (Comparación con valores de referencia)
-- Exportación esperada: Valor USD = 10,917,349,349.48 | Pares = 410,771,647 | Unitario = 26.58
-- Importación esperada: Valor USD = 18,506,091,720.31 | Pares = 751,088,918 | Unitario = 24.64
SELECT 
    f.flujo_comercial,
    COUNT(c.id_hecho) AS registros,
    SUM(c.valor_usd) AS suma_valor_usd,
    SUM(c.cantidad_pares) AS suma_pares,
    ROUND(SUM(c.valor_usd) / NULLIF(SUM(c.cantidad_pares), 0), 2) AS valor_por_par_ponderado,
    ROUND(AVG(c.valor_usd_por_par), 2) AS promedio_simple_unitario
FROM fact_comercio c
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
GROUP BY f.flujo_comercial
ORDER BY f.flujo_comercial;


-- 8. VALIDACIÓN DE LA VISTA vw_resumen_por_flujo FRENTE A TABLAS DIRECTAS
SELECT 
    v.flujo_comercial,
    v.total_registros,
    v.suma_valor_usd,
    v.suma_cantidad_pares,
    v.valor_usd_por_par_ponderado,
    v.promedio_simple_unitario
FROM vw_resumen_por_flujo v
ORDER BY v.flujo_comercial;
