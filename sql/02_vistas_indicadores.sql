-- =====================================================================
-- 02_vistas_indicadores.sql
-- Vistas Analíticas e Indicadores Clave (KPIs) para Power BI
-- =====================================================================

-- 1. Vista: Importaciones vs Exportaciones por Año
CREATE OR REPLACE VIEW vw_comercio_anual AS
SELECT 
    p.anio,
    f.flujo_comercial,
    COUNT(c.id_hecho) AS total_registros,
    SUM(c.valor_usd) AS valor_total_usd,
    SUM(c.cantidad_pares) AS cantidad_total_pares,
    -- Regla Fundamental: Valor por par = SUM(valor) / SUM(cantidad)
    CASE 
        WHEN SUM(c.cantidad_pares) > 0 
        THEN ROUND(SUM(c.valor_usd) / SUM(c.cantidad_pares), 2)
        ELSE NULL 
    END AS valor_usd_por_par_ponderado
FROM fact_comercio c
JOIN dim_periodo p ON c.id_periodo = p.id_periodo
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
JOIN dim_socio s ON c.id_socio = s.id_socio
WHERE s.tipo_socio = 'País' -- Evitar doble conteo excluyendo 'Mundo'
GROUP BY p.anio, f.flujo_comercial
ORDER BY p.anio, f.flujo_comercial;


-- 2. Vista: Principales Socios Comerciales por Flujo
CREATE OR REPLACE VIEW vw_top_socios_comercio AS
SELECT 
    s.socio_comercial,
    s.tipo_socio,
    f.flujo_comercial,
    SUM(c.valor_usd) AS valor_total_usd,
    SUM(c.cantidad_pares) AS cantidad_total_pares,
    CASE 
        WHEN SUM(c.cantidad_pares) > 0 
        THEN ROUND(SUM(c.valor_usd) / SUM(c.cantidad_pares), 2)
        ELSE NULL 
    END AS valor_usd_por_par_ponderado
FROM fact_comercio c
JOIN dim_socio s ON c.id_socio = s.id_socio
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
WHERE s.tipo_socio = 'País'
GROUP BY s.socio_comercial, s.tipo_socio, f.flujo_comercial
ORDER BY valor_total_usd DESC;


-- 3. Vista: Indicadores por Categoría de Calzado (Valor vs Cantidad)
CREATE OR REPLACE VIEW vw_kpis_por_categoria AS
SELECT 
    pr.codigo_sa6,
    pr.categoria_calzado,
    f.flujo_comercial,
    p.anio,
    SUM(c.valor_usd) AS valor_total_usd,
    SUM(c.cantidad_pares) AS cantidad_total_pares,
    CASE 
        WHEN SUM(c.cantidad_pares) > 0 
        THEN ROUND(SUM(c.valor_usd) / SUM(c.cantidad_pares), 2)
        ELSE NULL 
    END AS valor_usd_por_par_ponderado
FROM fact_comercio c
JOIN dim_producto pr ON c.id_producto = pr.id_producto
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
JOIN dim_periodo p ON c.id_periodo = p.id_periodo
JOIN dim_socio s ON c.id_socio = s.id_socio
WHERE s.tipo_socio = 'País'
GROUP BY pr.codigo_sa6, pr.categoria_calzado, f.flujo_comercial, p.anio
ORDER BY p.anio, valor_total_usd DESC;
