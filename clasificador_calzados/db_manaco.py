"""
db_manaco.py
Capa de persistencia y base de datos para el ecosistema Manaco BI y Visión Artificial.
Soporta PostgreSQL (Data Warehouse manaco_dw) con fallback inteligente a SQLite local,
asegurando alta disponibilidad y cero interrupciones.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from config import MAPEO_DB, ARCHIVO_SQLITE, CLASES, NOMBRES_CLASES

# Cargar variables de entorno desde la raíz de manaco_bi
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "manaco_dw")


class DatabaseManaco:
    def __init__(self):
        self.motor = "postgresql"
        self._inicializar_esquema()

    def _conectar_pg(self):
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                connect_timeout=3
            )
            return conn
        except Exception:
            return None

    def _conectar_sqlite(self):
        conn = sqlite3.connect(ARCHIVO_SQLITE, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def obtener_conexion(self):
        """Retorna una conexión activa priorizando PostgreSQL, con fallback a SQLite."""
        pg_conn = self._conectar_pg()
        if pg_conn:
            self.motor = "postgresql"
            return pg_conn
        self.motor = "sqlite"
        return self._conectar_sqlite()

    def _inicializar_esquema(self):
        """Asegura que las tablas operativas de inventario y trazabilidad existan sin depender del DW."""
        conn = self.obtener_conexion()
        try:
            if self.motor == "postgresql":
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS inventario_calzado (
                            id_producto INT PRIMARY KEY,
                            codigo_sa6 VARCHAR(20) NOT NULL,
                            categoria_calzado VARCHAR(255) NOT NULL,
                            categoria_corta VARCHAR(100) NOT NULL,
                            stock_actual INT NOT NULL DEFAULT 0,
                            stock_minimo INT NOT NULL DEFAULT 25,
                            capacidad_maxima INT NOT NULL DEFAULT 200,
                            precio_unitario_bs NUMERIC(10, 2) NOT NULL DEFAULT 199.00,
                            precio_unitario_usd NUMERIC(10, 2) NOT NULL DEFAULT 28.50,
                            ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS registro_vision (
                            id_registro SERIAL PRIMARY KEY,
                            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            id_producto INT REFERENCES inventario_calzado(id_producto),
                            categoria_nombre VARCHAR(100) NOT NULL,
                            accion VARCHAR(50) NOT NULL,
                            cantidad INT NOT NULL DEFAULT 1,
                            confianza NUMERIC(6, 4) NOT NULL,
                            origen VARCHAR(50) DEFAULT 'web_camara',
                            responsable VARCHAR(50) DEFAULT 'Sistema IA Manaco'
                        );
                        
                        INSERT INTO inventario_calzado (id_producto, codigo_sa6, categoria_calzado, categoria_corta, stock_actual, stock_minimo, capacidad_maxima, precio_unitario_bs, precio_unitario_usd)
                        VALUES 
                            (1, '640411', 'Calzado deportivo con suela de caucho/plástico', 'Calzado Deportivo', 30, 30, 250, 240.00, 34.50),
                            (2, '640399', 'Calzado con suela de caucho/plástico y parte superior de cuero', 'Calzado Casual Cuero', 30, 25, 200, 290.00, 41.60),
                            (3, '640420', 'Calzado con suela de cuero y parte superior de cuero/material similar', 'Calzado Formal Vestir', 30, 20, 150, 350.00, 50.30)
                        ON CONFLICT (id_producto) DO NOTHING;
                    """)
                    conn.commit()
            else:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS inventario_calzado (
                        id_producto INTEGER PRIMARY KEY,
                        codigo_sa6 TEXT NOT NULL,
                        categoria_calzado TEXT NOT NULL,
                        categoria_corta TEXT NOT NULL,
                        stock_actual INTEGER NOT NULL DEFAULT 0,
                        stock_minimo INTEGER NOT NULL DEFAULT 25,
                        capacidad_maxima INTEGER NOT NULL DEFAULT 200,
                        precio_unitario_bs REAL NOT NULL DEFAULT 199.00,
                        precio_unitario_usd REAL NOT NULL DEFAULT 28.50,
                        ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS registro_vision (
                        id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        id_producto INTEGER,
                        categoria_nombre TEXT NOT NULL,
                        accion TEXT NOT NULL,
                        cantidad INTEGER NOT NULL DEFAULT 1,
                        confianza REAL NOT NULL,
                        origen TEXT DEFAULT 'web_camara',
                        responsable TEXT DEFAULT 'Sistema IA Manaco',
                        FOREIGN KEY (id_producto) REFERENCES inventario_calzado(id_producto)
                    );
                """)
                cur.execute("SELECT COUNT(*) FROM inventario_calzado")
                if cur.fetchone()[0] == 0:
                    cur.executemany("INSERT INTO inventario_calzado VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))", [
                        (1, '640411', 'Calzado deportivo con suela de caucho/plástico', 'Calzado Deportivo', 30, 30, 250, 240.00, 34.50),
                        (2, '640399', 'Calzado con suela de caucho/plástico y parte superior de cuero', 'Calzado Casual Cuero', 30, 25, 200, 290.00, 41.60),
                        (3, '640420', 'Calzado con suela de cuero y parte superior de cuero/material similar', 'Calzado Formal Vestir', 30, 20, 150, 350.00, 50.30)
                    ])
                conn.commit()
        finally:
            conn.close()

    def obtener_inventario(self):
        """Retorna lista de productos con su stock, precios y estado de inventario directamente."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    id_producto,
                    codigo_sa6,
                    categoria_calzado,
                    categoria_corta,
                    stock_actual,
                    stock_minimo,
                    capacidad_maxima,
                    precio_unitario_bs,
                    precio_unitario_usd,
                    ultima_actualizacion
                FROM inventario_calzado
                ORDER BY id_producto;
            """)
            filas = cur.fetchall()
            productos = []
            for f in filas:
                p = {
                    "id_producto": f[0],
                    "codigo_sa6": f[1],
                    "categoria_calzado": f[2],
                    "categoria_corta": f[3],
                    "stock_actual": int(f[4]),
                    "stock_minimo": int(f[5]),
                    "capacidad_maxima": int(f[6]),
                    "precio_unitario_bs": float(f[7]),
                    "precio_unitario_usd": float(f[8]),
                    "ultima_actualizacion": str(f[9]) if f[9] else "",
                    "alerta_stock": int(f[4]) <= int(f[5]),
                    "porcentaje_capacidad": round((int(f[4]) / max(1, int(f[6]))) * 100, 1)
                }
                productos.append(p)
            return productos
        finally:
            conn.close()

    def registrar_calzado_ia(self, clase_nombre, confianza=0.90, origen="camara_web", responsable="Operador IA Manaco"):
        """Registra un nuevo zapato reconocido por Visión Artificial y suma +1 al inventario."""
        if clase_nombre not in MAPEO_DB:
            return {"exito": False, "mensaje": f"Clase desconocida: {clase_nombre}"}

        info = MAPEO_DB[clase_nombre]
        id_prod = info["id_producto"]
        nombre_legible = NOMBRES_CLASES.get(clase_nombre, clase_nombre)

        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            ahora = datetime.now()
            
            # 1. Aumentar stock
            if self.motor == "postgresql":
                cur.execute("""
                    UPDATE inventario_calzado
                    SET stock_actual = stock_actual + 1,
                        ultima_actualizacion = %s
                    WHERE id_producto = %s
                    RETURNING stock_actual;
                """, (ahora, id_prod))
                nuevo_stock = cur.fetchone()[0]
                
                # 2. Registrar log
                cur.execute("""
                    INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, accion, cantidad, confianza, origen, responsable)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id_registro;
                """, (ahora, id_prod, nombre_legible, "INGRESO_IA", 1, confianza, origen, responsable))
                id_reg = cur.fetchone()[0]
            else:
                cur.execute("""
                    UPDATE inventario_calzado
                    SET stock_actual = stock_actual + 1,
                        ultima_actualizacion = ?
                    WHERE id_producto = ?
                """, (ahora.isoformat(), id_prod))
                cur.execute("SELECT stock_actual FROM inventario_calzado WHERE id_producto = ?", (id_prod,))
                nuevo_stock = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, accion, cantidad, confianza, origen, responsable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (ahora.isoformat(), id_prod, nombre_legible, "INGRESO_IA", 1, confianza, origen, responsable))
                id_reg = cur.lastrowid

            conn.commit()
            return {
                "exito": True,
                "id_registro": id_reg,
                "id_producto": id_prod,
                "categoria": nombre_legible,
                "clase": clase_nombre,
                "nuevo_stock": nuevo_stock,
                "confianza": round(float(confianza), 3),
                "timestamp": ahora.strftime("%H:%M:%S")
            }
        except Exception as e:
            conn.rollback()
            return {"exito": False, "error": str(e)}
        finally:
            conn.close()

    def deshacer_ultimo_registro(self):
        """Deshace el último registro ingresado por visión o simulador."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            if self.motor == "postgresql":
                cur.execute("""
                    SELECT id_registro, id_producto, categoria_nombre, accion, cantidad
                    FROM registro_vision
                    ORDER BY id_registro DESC
                    LIMIT 1;
                """)
            else:
                cur.execute("""
                    SELECT id_registro, id_producto, categoria_nombre, accion, cantidad
                    FROM registro_vision
                    ORDER BY id_registro DESC
                    LIMIT 1;
                """)
            fila = cur.fetchone()
            if not fila:
                return {"exito": False, "mensaje": "No hay movimientos para deshacer."}

            id_reg, id_prod, cat_nombre, accion, cant = fila
            if accion in ("INGRESO_IA", "INGRESO_SIMULADO"):
                # Restar stock
                if self.motor == "postgresql":
                    cur.execute("UPDATE inventario_calzado SET stock_actual = GREATEST(0, stock_actual - %s) WHERE id_producto = %s", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = %s", (id_reg,))
                else:
                    cur.execute("UPDATE inventario_calzado SET stock_actual = MAX(0, stock_actual - ?) WHERE id_producto = ?", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = ?", (id_reg,))
                conn.commit()
                return {"exito": True, "mensaje": f"Se revirtió ingreso de {cat_nombre} (Reg #{id_reg})"}
            elif accion == "VENTA_SIMULADA":
                # Devolver stock
                if self.motor == "postgresql":
                    cur.execute("UPDATE inventario_calzado SET stock_actual = stock_actual + %s WHERE id_producto = %s", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = %s", (id_reg,))
                else:
                    cur.execute("UPDATE inventario_calzado SET stock_actual = stock_actual + ? WHERE id_producto = ?", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = ?", (id_reg,))
                conn.commit()
                return {"exito": True, "mensaje": f"Se revirtió venta de {cat_nombre} (Reg #{id_reg})"}
            return {"exito": False, "mensaje": "Acción no reversible."}
        finally:
            conn.close()

    def reiniciar_inventario(self, stock_base=30):
        """Reinicia el inventario a valores basales estándar para pruebas limpias."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            if self.motor == "postgresql":
                cur.execute("UPDATE inventario_calzado SET stock_actual = %s, ultima_actualizacion = CURRENT_TIMESTAMP", (stock_base,))
                cur.execute("DELETE FROM registro_vision")
            else:
                cur.execute("UPDATE inventario_calzado SET stock_actual = ?, ultima_actualizacion = datetime('now')", (stock_base,))
                cur.execute("DELETE FROM registro_vision")
            conn.commit()
            return {"exito": True, "mensaje": f"Inventario reiniciado a {stock_base} unidades por categoría."}
        finally:
            conn.close()

    def obtener_movimientos(self, limite=25):
        """Retorna los últimos registros de visión y transacciones."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    id_registro,
                    fecha_hora,
                    id_producto,
                    categoria_nombre,
                    accion,
                    cantidad,
                    confianza,
                    origen,
                    responsable
                FROM registro_vision
                ORDER BY id_registro DESC
                LIMIT %s;
            """ if self.motor == "postgresql" else """
                SELECT 
                    id_registro,
                    fecha_hora,
                    id_producto,
                    categoria_nombre,
                    accion,
                    cantidad,
                    confianza,
                    origen,
                    responsable
                FROM registro_vision
                ORDER BY id_registro DESC
                LIMIT ?;
            """, (limite,))
            filas = cur.fetchall()
            movs = []
            for f in filas:
                movs.append({
                    "id_registro": f[0],
                    "fecha_hora": str(f[1])[:19] if f[1] else "",
                    "id_producto": f[2],
                    "categoria": f[3],
                    "accion": f[4],
                    "cantidad": f[5],
                    "confianza": round(float(f[6]), 3) if f[6] is not None else 1.0,
                    "origen": f[7],
                    "responsable": f[8]
                })
            return movs
        finally:
            conn.close()

    def simular_datos(self, cantidad=30):
        """Genera datos sintéticos realistas de entradas por visión y salidas por ventas."""
        categorias_sim = [
            ("calzado_deportivo", 1, "Calzado Deportivo (Sneakers/Tenis)", 240.00),
            ("calzado_casual", 2, "Calzado Casual Cuero (Mocasines/Botines)", 290.00),
            ("calzado_formal", 3, "Calzado Formal de Vestir (Cuero)", 350.00)
        ]
        tiendas = ["Tienda Central Cochabamba", "Sucursal El Prado La Paz", "Manaco Ventura Mall Santa Cruz", "Línea Ensamblaje Planta Quillacollo"]
        acciones = ["INGRESO_IA", "INGRESO_IA", "INGRESO_SIMULADO", "VENTA_SIMULADA"]

        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            ahora = datetime.now()
            registros_generados = 0

            for i in range(cantidad):
                clase_cod, id_prod, cat_nombre, precio = random.choice(categorias_sim)
                accion = random.choice(acciones)
                cant = random.randint(1, 3)
                confianza = round(random.uniform(0.82, 0.99), 3) if "IA" in accion else 1.00
                origen = random.choice(tiendas)
                
                # Distribuir fechas en las últimas 72 horas para graficar tendencias
                minutos_atras = random.randint(5, 72 * 60)
                fecha_reg = ahora - timedelta(minutes=minutos_atras)

                if accion.startswith("INGRESO"):
                    delta_stock = cant
                else:
                    delta_stock = -cant

                # Actualizar stock
                if self.motor == "postgresql":
                    cur.execute("""
                        UPDATE inventario_calzado
                        SET stock_actual = GREATEST(0, stock_actual + %s),
                            ultima_actualizacion = %s
                        WHERE id_producto = %s;
                    """, (delta_stock, fecha_reg, id_prod))

                    cur.execute("""
                        INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, accion, cantidad, confianza, origen, responsable)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """, (fecha_reg, id_prod, cat_nombre, accion, cant, confianza, origen, "Simulador BI Manaco"))
                else:
                    cur.execute("""
                        UPDATE inventario_calzado
                        SET stock_actual = MAX(0, stock_actual + ?),
                            ultima_actualizacion = ?
                        WHERE id_producto = ?;
                    """, (delta_stock, fecha_reg.isoformat(), id_prod))

                    cur.execute("""
                        INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, accion, cantidad, confianza, origen, responsable)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (fecha_reg.isoformat(), id_prod, cat_nombre, accion, cant, confianza, origen, "Simulador BI Manaco"))

                registros_generados += 1

            conn.commit()
            return {"exito": True, "registros_generados": registros_generados, "mensaje": f"Se simularon {registros_generados} movimientos exitosamente."}
        except Exception as e:
            conn.rollback()
            return {"exito": False, "error": str(e)}
        finally:
            conn.close()

    def obtener_kpis(self):
        """Calcula métricas e indicadores de alto nivel para el Dashboard BI."""
        inv = self.obtener_inventario()
        total_pares = sum(item["stock_actual"] for item in inv)
        total_valor_bs = sum(item["stock_actual"] * item["precio_unitario_bs"] for item in inv)
        total_valor_usd = sum(item["stock_actual"] * item["precio_unitario_usd"] for item in inv)
        capacidad_total = sum(item["capacidad_maxima"] for item in inv)
        ocupacion_pct = round((total_pares / max(1, capacidad_total)) * 100, 1)

        # Categoría con mayor inventario
        cat_lider = max(inv, key=lambda x: x["stock_actual"]) if inv else {"categoria_corta": "N/D", "stock_actual": 0}

        # Conteo de detecciones IA registradas en registro_vision
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    COUNT(id_registro),
                    AVG(confianza)
                FROM registro_vision
                WHERE accion = 'INGRESO_IA';
            """)
            fila = cur.fetchone()
            total_ia = fila[0] if fila else 0
            confianza_prom = round(float(fila[1]) * 100, 1) if (fila and fila[1] is not None) else None
        finally:
            conn.close()

        return {
            "total_pares": total_pares,
            "total_valor_bs": f"{total_valor_bs:,.2f}",
            "total_valor_usd": f"{total_valor_usd:,.2f}",
            "capacidad_ocupada_pct": ocupacion_pct,
            "categoria_lider": cat_lider["categoria_corta"],
            "stock_lider": cat_lider["stock_actual"],
            "total_ingresos_ia": total_ia,
            "confianza_promedio_ia": f"{confianza_prom}%" if confianza_prom is not None else "Sin escaneos",
            "motor_db": self.motor.upper()
        }

    def obtener_datos_graficos(self):
        """Genera datasets estructurados para los gráficos interactivos de Chart.js."""
        inv = self.obtener_inventario()
        kpis = self.obtener_kpis()

        # 1. Gráfico de Barras: Stock Actual vs Mínimo
        labels_cats = [item["categoria_corta"] for item in inv]
        stock_actual = [item["stock_actual"] for item in inv]
        stock_minimo = [item["stock_minimo"] for item in inv]
        capacidad_max = [item["capacidad_maxima"] for item in inv]

        # 2. Gráfico de Dona: Distribución porcentual
        # Colores temáticos: Deportivo -> Cyan, Casual -> Ámbar, Formal -> Carmesí
        colores_dona = ["#06b6d4", "#f59e0b", "#e11d48"]

        # 3. Gráfico de Evolución Temporal (Últimos días / horas)
        conn = self.obtener_conexion()
        serie_fechas = []
        serie_ingresos = []
        serie_ventas = []
        try:
            cur = conn.cursor()
            # Agrupar por fecha/día
            if self.motor == "postgresql":
                cur.execute("""
                    SELECT 
                        TO_CHAR(fecha_hora, 'DD/MM HH24h') as periodo,
                        SUM(CASE WHEN accion LIKE 'INGRESO%%' THEN cantidad ELSE 0 END) as ingresos,
                        SUM(CASE WHEN accion LIKE 'VENTA%%' THEN cantidad ELSE 0 END) as ventas
                    FROM registro_vision
                    GROUP BY TO_CHAR(fecha_hora, 'DD/MM HH24h'), DATE_TRUNC('hour', fecha_hora)
                    ORDER BY DATE_TRUNC('hour', fecha_hora) DESC
                    LIMIT 10;
                """)
            else:
                cur.execute("""
                    SELECT 
                        strftime('%d/%m %Hh', fecha_hora) as periodo,
                        SUM(CASE WHEN accion LIKE 'INGRESO%' THEN cantidad ELSE 0 END) as ingresos,
                        SUM(CASE WHEN accion LIKE 'VENTA%' THEN cantidad ELSE 0 END) as ventas
                    FROM registro_vision
                    GROUP BY strftime('%d/%m %Hh', fecha_hora)
                    ORDER BY fecha_hora DESC
                    LIMIT 10;
                """)
            filas = cur.fetchall()
            for r in reversed(filas):
                serie_fechas.append(r[0])
                serie_ingresos.append(int(r[1] or 0))
                serie_ventas.append(int(r[2] or 0))
        finally:
            conn.close()

        # 4. Datos del Analisis Comercial directo de Excel (Registros de España)
        comercio_excel = self._obtener_datos_comercio_excel()

        return {
            "categorias": labels_cats,
            "stock_actual": stock_actual,
            "stock_minimo": stock_minimo,
            "capacidad_max": capacidad_max,
            "colores": colores_dona,
            "serie_fechas": serie_fechas,
            "serie_ingresos": serie_ingresos,
            "serie_ventas": serie_ventas,
            "dw_comercio": comercio_excel,
            "kpis": kpis
        }

    def _obtener_datos_comercio_excel(self):
        """Consulta estadísticas de comercio directamente del Excel BDatos_MANACO.xlsx."""
        try:
            from analisis_comercial import calcular_metricas_comerciales
            imp = calcular_metricas_comerciales(flujo="Importación", anio=None)
            exp = calcular_metricas_comerciales(flujo="Exportación", anio=None)

            anios = imp["serie_temporal"]["anios"]
            imp_pares = imp["serie_temporal"]["cantidades_pares"]
            exp_pares = exp["serie_temporal"]["cantidades_pares"]
            ratios_usd_par = imp["serie_temporal"]["ratios_usd_par"]

            return {
                "disponible": True,
                "anios": anios,
                "importacion_pares": [float(p) for p in imp_pares],
                "exportacion_pares": [float(p) for p in exp_pares],
                "valor_usd_por_par": [float(r) for r in ratios_usd_par],
                "fuente": "Registros de comercio exterior reportados por España (BDatos_MANACO.xlsx)"
            }
        except Exception as e:
            return {
                "disponible": False,
                "error": str(e),
                "anios": [],
                "importacion_pares": [],
                "exportacion_pares": [],
                "valor_usd_por_par": []
            }

    def actualizar_precio_producto(self, id_producto: int, nuevo_precio_bs: float, nuevo_precio_usd: float, responsable: str = "Operador Manaco"):
        """Actualiza explícitamente el precio de un calzado en el inventario activo."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            ahora = datetime.now()
            if self.motor == "postgresql":
                cur.execute("""
                    UPDATE inventario_calzado
                    SET precio_unitario_bs = %s,
                        precio_unitario_usd = %s,
                        ultima_actualizacion = %s
                    WHERE id_producto = %s;
                """, (nuevo_precio_bs, nuevo_precio_usd, ahora, id_producto))
                cur.execute("""
                    INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, accion, cantidad, confianza, origen, responsable)
                    SELECT %s, id_producto, categoria_corta, 'AJUSTE_PRECIO', 0, 1.0, 'modulo_precios', %s
                    FROM inventario_calzado WHERE id_producto = %s;
                """, (ahora, responsable, id_producto))
            else:
                cur.execute("""
                    UPDATE inventario_calzado
                    SET precio_unitario_bs = ?,
                        precio_unitario_usd = ?,
                        ultima_actualizacion = ?
                    WHERE id_producto = ?;
                """, (nuevo_precio_bs, nuevo_precio_usd, ahora.isoformat(), id_producto))
                cur.execute("""
                    INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, accion, cantidad, confianza, origen, responsable)
                    SELECT ?, id_producto, categoria_corta, 'AJUSTE_PRECIO', 0, 1.0, 'modulo_precios', ?
                    FROM inventario_calzado WHERE id_producto = ?;
                """, (ahora.isoformat(), responsable, id_producto))
            conn.commit()
            return {
                "exito": True,
                "mensaje": f"Precio del producto ID #{id_producto} actualizado a Bs. {nuevo_precio_bs:,.2f} ($us. {nuevo_precio_usd:,.2f})",
                "id_producto": id_producto,
                "nuevo_precio_bs": nuevo_precio_bs,
                "nuevo_precio_usd": nuevo_precio_usd
            }
        except Exception as e:
            conn.rollback()
            return {"exito": False, "error": str(e)}
        finally:
            conn.close()


# Instancia única accesible
db_manaco = DatabaseManaco()
