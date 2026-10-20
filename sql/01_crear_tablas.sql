-- =====================================================================
-- 01_crear_tablas.sql
-- Data Warehouse: manaco_dw
-- Modelo Dimensional (Esquema Estrella) para Comercio Exterior de Calzado
-- =====================================================================

-- Eliminar tablas previas si existen (respetando restricciones de claves foráneas)
DROP TABLE IF EXISTS fact_comercio CASCADE;
DROP TABLE IF EXISTS dim_periodo CASCADE;
DROP TABLE IF EXISTS dim_producto CASCADE;
DROP TABLE IF EXISTS dim_reportante CASCADE;
DROP TABLE IF EXISTS dim_socio CASCADE;
DROP TABLE IF EXISTS dim_flujo CASCADE;

-- 1. Dimensión Período / Año
CREATE TABLE dim_periodo (
    id_periodo INT PRIMARY KEY,
    anio INT NOT NULL UNIQUE
);

-- 2. Dimensión Producto
CREATE TABLE dim_producto (
    id_producto SERIAL PRIMARY KEY,
    codigo_sa6 VARCHAR(20) NOT NULL UNIQUE,
    categoria_calzado VARCHAR(255) NOT NULL
);

-- 3. Dimensión Reportante (País que reporta)
CREATE TABLE dim_reportante (
    id_reportante SERIAL PRIMARY KEY,
    pais_reportante VARCHAR(100) NOT NULL UNIQUE
);

-- 4. Dimensión Socio Comercial
-- Incluye la clasificación 'Mundo' vs 'País' para evitar doble conteo
CREATE TABLE dim_socio (
    id_socio SERIAL PRIMARY KEY,
    socio_comercial VARCHAR(100) NOT NULL UNIQUE,
    tipo_socio VARCHAR(20) DEFAULT 'País' -- 'País' o 'Mundo'
);

-- 5. Dimensión Flujo Comercial
CREATE TABLE dim_flujo (
    id_flujo SERIAL PRIMARY KEY,
    flujo_comercial VARCHAR(50) NOT NULL UNIQUE -- 'Importación' o 'Exportación'
);

-- 6. Tabla de Hechos: Comercio Exterior
CREATE TABLE fact_comercio (
    id_hecho BIGSERIAL PRIMARY KEY,
    id_periodo INT NOT NULL REFERENCES dim_periodo(id_periodo),
    id_producto INT NOT NULL REFERENCES dim_producto(id_producto),
    id_reportante INT NOT NULL REFERENCES dim_reportante(id_reportante),
    id_socio INT NOT NULL REFERENCES dim_socio(id_socio),
    id_flujo INT NOT NULL REFERENCES dim_flujo(id_flujo),
    valor_usd NUMERIC(18, 4) NOT NULL,
    cantidad_pares NUMERIC(18, 2), -- Puede ser NULL (desconocido), NO convertir a cero
    valor_usd_por_par NUMERIC(14, 4),
    valor_miles_usd NUMERIC(16, 4)
);

-- Índices recomendados para optimizar consultas de Power BI
CREATE INDEX idx_fact_periodo ON fact_comercio(id_periodo);
CREATE INDEX idx_fact_producto ON fact_comercio(id_producto);
CREATE INDEX idx_fact_reportante ON fact_comercio(id_reportante);
CREATE INDEX idx_fact_socio ON fact_comercio(id_socio);
CREATE INDEX idx_fact_flujo ON fact_comercio(id_flujo);
