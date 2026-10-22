-- =====================================================================
-- 04_inventario_vision.sql
-- Módulo de Inventario en Tiempo Real y Visión Artificial para Manaco
-- =====================================================================

-- 1. Tabla de Stock e Inventario Actual por Categoría de Calzado
CREATE TABLE IF NOT EXISTS inventario_calzado (
    id_producto INT PRIMARY KEY REFERENCES dim_producto(id_producto),
    categoria_corta VARCHAR(50) NOT NULL,
    stock_actual INT NOT NULL DEFAULT 0,
    stock_minimo INT NOT NULL DEFAULT 25,
    capacidad_maxima INT NOT NULL DEFAULT 200,
    precio_unitario_bs NUMERIC(10, 2) NOT NULL DEFAULT 199.00,
    precio_unitario_usd NUMERIC(10, 2) NOT NULL DEFAULT 28.50,
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Movimientos y Registros por Visión Artificial
CREATE TABLE IF NOT EXISTS registro_vision (
    id_registro SERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_producto INT REFERENCES dim_producto(id_producto),
    categoria_nombre VARCHAR(100) NOT NULL,
    accion VARCHAR(50) NOT NULL, -- 'INGRESO_IA', 'VENTA_SIMULADA', 'AJUSTE_MANUAL', 'DESHACER'
    cantidad INT NOT NULL DEFAULT 1,
    confianza NUMERIC(6, 4) NOT NULL,
    origen VARCHAR(50) DEFAULT 'web_camara',
    responsable VARCHAR(50) DEFAULT 'Sistema IA Manaco'
);

-- 3. Índices para acelerar consultas analíticas
CREATE INDEX IF NOT EXISTS idx_reg_vision_fecha ON registro_vision(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_reg_vision_prod ON registro_vision(id_producto);
CREATE INDEX IF NOT EXISTS idx_reg_vision_accion ON registro_vision(accion);

-- 4. Inicializar inventario para los 3 productos base si no existen registros
INSERT INTO inventario_calzado (id_producto, categoria_corta, stock_actual, stock_minimo, capacidad_maxima, precio_unitario_bs, precio_unitario_usd)
VALUES 
    (1, 'Calzado Deportivo', 45, 30, 250, 240.00, 34.50),
    (2, 'Calzado Casual Cuero', 60, 25, 200, 290.00, 41.60),
    (3, 'Calzado Formal Vestir', 35, 20, 150, 350.00, 50.30)
ON CONFLICT (id_producto) DO NOTHING;
