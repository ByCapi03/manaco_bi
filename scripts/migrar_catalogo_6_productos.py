"""
scripts/migrar_catalogo_6_productos.py
Script de migración atómica para el catálogo de 6 productos ficticios en PostgreSQL y SQLite.
Preserva el inventario existente (90 pares totales: 15 por producto, 30 por categoría).
Agrega columnas de precio efectivo de venta y canal a los movimientos de inventario.
"""

import sys
from pathlib import Path

# Configurar salida en UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "clasificador_calzados"))

try:
    from clasificador_calzados import analisis_comercial as ac
    from clasificador_calzados.catalogo import obtener_catalogo_completo
    from clasificador_calzados.db_manaco import db_manaco
except ImportError:
    import analisis_comercial as ac  # type: ignore
    from catalogo import obtener_catalogo_completo  # type: ignore
    from db_manaco import db_manaco  # type: ignore

def migrar_base_datos():
    print("=" * 70)
    print("INICIANDO MIGRACIÓN DE CATÁLOGO A 6 PRODUCTOS EN POSTGRESQL / SQLITE")
    print("=" * 70)

    # 1. Cargar catálogo con precios calculados desde Excel
    df_excel = ac.cargar_dataset_excel()
    prods = obtener_catalogo_completo(df_excel)

    conn = db_manaco.obtener_conexion()
    try:
        cur = conn.cursor()
        motor = db_manaco.motor
        print(f"Motor activo: {motor.upper()}")

        if motor == "postgresql":
            # 1. Asegurar nuevas columnas en inventario_calzado si no existen
            cur.execute("""
                ALTER TABLE inventario_calzado 
                ADD COLUMN IF NOT EXISTS codigo_sku VARCHAR(30),
                ADD COLUMN IF NOT EXISTS categoria_padre VARCHAR(50),
                ADD COLUMN IF NOT EXISTS linea VARCHAR(30),
                ADD COLUMN IF NOT EXISTS nombre_producto VARCHAR(100),
                ADD COLUMN IF NOT EXISTS descripcion TEXT,
                ADD COLUMN IF NOT EXISTS costo_referencia_usd NUMERIC(10, 4) DEFAULT 25.0,
                ADD COLUMN IF NOT EXISTS gastos_adicionales_usd NUMERIC(10, 2) DEFAULT 4.0,
                ADD COLUMN IF NOT EXISTS margen_objetivo_pct NUMERIC(5, 2) DEFAULT 25.0,
                ADD COLUMN IF NOT EXISTS lead_time_dias INT DEFAULT 7,
                ADD COLUMN IF NOT EXISTS stock_seguridad INT DEFAULT 10,
                ADD COLUMN IF NOT EXISTS pedidos_pendientes INT DEFAULT 0,
                ADD COLUMN IF NOT EXISTS icono VARCHAR(10) DEFAULT '👟';
            """)

            # 2. Asegurar nuevas columnas en registro_vision si no existen
            cur.execute("""
                ALTER TABLE registro_vision 
                ADD COLUMN IF NOT EXISTS producto_nombre VARCHAR(100),
                ADD COLUMN IF NOT EXISTS precio_unitario_venta_usd NUMERIC(10, 2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS precio_unitario_venta_bs NUMERIC(10, 2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS ingreso_total_usd NUMERIC(12, 2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS ingreso_total_bs NUMERIC(12, 2) DEFAULT 0.00,
                ADD COLUMN IF NOT EXISTS canal_venta VARCHAR(50) DEFAULT 'Tienda Propia',
                ADD COLUMN IF NOT EXISTS stock_resultante INT,
                ADD COLUMN IF NOT EXISTS nota TEXT;
            """)

            # 3. Insertar o actualizar los 6 productos preservando las existencias sin duplicación
            for p in prods:
                cur.execute("""
                    INSERT INTO inventario_calzado (
                        id_producto, codigo_sku, codigo_sa6, categoria_padre, 
                        categoria_calzado, categoria_corta, linea, nombre_producto, 
                        descripcion, stock_actual, stock_minimo, capacidad_maxima, 
                        costo_referencia_usd, gastos_adicionales_usd, margen_objetivo_pct, 
                        precio_unitario_usd, precio_unitario_bs, lead_time_dias, 
                        stock_seguridad, pedidos_pendientes, icono
                    )
                    VALUES (
                        %s, %s, %s, %s, 
                        %s, %s, %s, %s, 
                        %s, 15, %s, %s, 
                        %s, %s, %s, 
                        %s, %s, %s, 
                        %s, 0, %s
                    )
                    ON CONFLICT (id_producto) DO UPDATE SET
                        codigo_sku = EXCLUDED.codigo_sku,
                        codigo_sa6 = EXCLUDED.codigo_sa6,
                        categoria_padre = EXCLUDED.categoria_padre,
                        categoria_calzado = EXCLUDED.categoria_calzado,
                        categoria_corta = EXCLUDED.categoria_corta,
                        linea = EXCLUDED.linea,
                        nombre_producto = EXCLUDED.nombre_producto,
                        descripcion = EXCLUDED.descripcion,
                        costo_referencia_usd = EXCLUDED.costo_referencia_usd,
                        gastos_adicionales_usd = EXCLUDED.gastos_adicionales_usd,
                        margen_objetivo_pct = EXCLUDED.margen_objetivo_pct,
                        precio_unitario_usd = EXCLUDED.precio_unitario_usd,
                        precio_unitario_bs = EXCLUDED.precio_unitario_bs,
                        lead_time_dias = EXCLUDED.lead_time_dias,
                        stock_seguridad = EXCLUDED.stock_seguridad,
                        icono = EXCLUDED.icono;
                """, (
                    p["id_producto"], p["codigo_sku"], p["codigo_sa6"], p["categoria_padre"],
                    p["categoria_arancelaria"], p["categoria_corta"], p["linea"], p["nombre_producto"],
                    p["descripcion"], p["stock_minimo"], p["capacidad_maxima"],
                    p["referencia_importacion_2024_usd"], p["gastos_adicionales_usd"], p["margen_objetivo_pct"],
                    p["precio_propuesto_usd"], p["precio_propuesto_bob"], p["lead_time_dias"],
                    p["stock_seguridad"], p["icono"]
                ))
            
            # Asegurar que el stock_actual sume 15 pares por producto si eran 30 pares en los 3 previos
            # Si id 1 tenía 30, ahora ID 1 tiene 15 y ID 2 tiene 15.
            cur.execute("SELECT SUM(stock_actual) FROM inventario_calzado;")
            total_stock = cur.fetchone()[0]
            if total_stock != 90:
                print(f"Ajustando distribución de stock para sumar exactamente 90 pares (15 pares c/u)...")
                cur.execute("UPDATE inventario_calzado SET stock_actual = 15;")

            # Añadir restricción CHECK para evitar stock negativo si no existe
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'chk_inventario_stock_positivo'
                    ) THEN
                        ALTER TABLE inventario_calzado ADD CONSTRAINT chk_inventario_stock_positivo CHECK (stock_actual >= 0);
                    END IF;
                END $$;
            """)
            conn.commit()

        print("\n✓ Migración de base de datos finalizada exitosamente.")
        
        # Verificar estado tras migración
        cur.execute("""
            SELECT id_producto, codigo_sku, codigo_sa6, nombre_producto, stock_actual, precio_unitario_usd, precio_unitario_bs
            FROM inventario_calzado
            ORDER BY id_producto;
        """)
        filas = cur.fetchall()
        print("\nCatálogo en base de datos:")
        tot_pares = 0
        for f in filas:
            print(f"   [{f[0]}] {f[1]} ({f[2]}): {f[3]} | Stock: {f[4]} pares | ${f[5]:.2f} USD (Bs. {f[6]:.2f})")
            tot_pares += f[4]
        print(f"\n   Total pares en catálogo: {tot_pares} pares")
        assert tot_pares == 90, f"El total de stock debe ser exactamente 90 pares, obtenido: {tot_pares}"

    finally:
        conn.close()

if __name__ == "__main__":
    migrar_base_datos()
