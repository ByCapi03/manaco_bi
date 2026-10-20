-- =====================================================================
-- 02_vistas_indicadores.sql
-- Vistas Analíticas e Indicadores Clave (KPIs) para Power BI
-- =====================================================================

-- 1. Vista: Resumen Global por Flujo Comercial
CREATE OR REPLACE VIEW vw_resumen_por_flujo AS
SELECT 
    f.flujo_comercial,
    COUNT(c.id_hecho) AS total_registros,
    SUM(c.valor_usd) AS suma_valor_usd,
    SUM(c.cantidad_pares) AS suma_cantidad_pares,
    -- Regla Fundamental: SUM(valor_usd) / NULLIF(SUM(cantidad_pares), 0)
    ROUND(SUM(c.valor_usd) / NULLIF(SUM(c.cantidad_pares), 0), 2) AS valor_usd_por_par_ponderado,
    ROUND(AVG(c.valor_usd_por_par), 2) AS promedio_simple_unitario
FROM fact_comercio c
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
GROUP BY f.flujo_comercial
ORDER BY f.flujo_comercial;


-- 2. Vista: Importaciones vs Exportaciones por Año
CREATE OR REPLACE VIEW vw_comercio_anual AS
SELECT 
    p.anio,
    f.flujo_comercial,
    COUNT(c.id_hecho) AS total_registros,
    SUM(c.valor_usd) AS valor_total_usd,
    SUM(c.cantidad_pares) AS cantidad_total_pares,
    ROUND(SUM(c.valor_usd) / NULLIF(SUM(c.cantidad_pares), 0), 2) AS valor_usd_por_par_ponderado
FROM fact_comercio c
JOIN dim_periodo p ON c.id_periodo = p.id_periodo
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
GROUP BY p.anio, f.flujo_comercial
ORDER BY p.anio, f.flujo_comercial;


-- 3. Vista: Principales Socios Comerciales por Flujo
CREATE OR REPLACE VIEW vw_top_socios_comercio AS
SELECT 
    s.socio_comercial,
    s.tipo_socio,
    f.flujo_comercial,
    COUNT(c.id_hecho) AS total_registros,
    SUM(c.valor_usd) AS valor_total_usd,
    SUM(c.cantidad_pares) AS cantidad_total_pares,
    ROUND(SUM(c.valor_usd) / NULLIF(SUM(c.cantidad_pares), 0), 2) AS valor_usd_por_par_ponderado
FROM fact_comercio c
JOIN dim_socio s ON c.id_socio = s.id_socio
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
GROUP BY s.socio_comercial, s.tipo_socio, f.flujo_comercial
ORDER BY valor_total_usd DESC;


-- 4. Vista: Indicadores por Categoría de Calzado (Valor vs Cantidad)
CREATE OR REPLACE VIEW vw_kpis_por_categoria AS
SELECT 
    pr.codigo_sa6,
    pr.categoria_calzado,
    f.flujo_comercial,
    p.anio,
    COUNT(c.id_hecho) AS total_registros,
    SUM(c.valor_usd) AS valor_total_usd,
    SUM(c.cantidad_pares) AS cantidad_total_pares,
    ROUND(SUM(c.valor_usd) / NULLIF(SUM(c.cantidad_pares), 0), 2) AS valor_usd_por_par_ponderado
FROM fact_comercio c
JOIN dim_producto pr ON c.id_producto = pr.id_producto
JOIN dim_flujo f ON c.id_flujo = f.id_flujo
JOIN dim_periodo p ON c.id_periodo = p.id_periodo
GROUP BY pr.codigo_sa6, pr.categoria_calzado, f.flujo_comercial, p.anio
ORDER BY p.anio, valor_total_usd DESC;
