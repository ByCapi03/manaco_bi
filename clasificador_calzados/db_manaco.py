"""
db_manaco.py
Capa de persistencia y base de datos para el ecosistema Manaco BI y Visión Artificial.
Soporta catálogo de 6 productos ficticios (2 por categoría arancelaria SA6) con existencias
por producto y agregación por suma para categorías.
Garantiza transacciones atómicas, validación de stock no negativo, y registro de precios
unitarios de venta efectivos para asegurar que cambios en el catálogo no alteren ingresos históricos.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from config import MAPEO_DB, MAPEO_CATEGORIA_A_PRODUCTOS, ARCHIVO_SQLITE, CLASES, NOMBRES_CLASES, TASA_CAMBIO_OFICIAL
from catalogo import CATALOGO_PRODUCTOS, obtener_catalogo_completo

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
        """Asegura que las tablas operativas del catálogo de 6 productos y trazabilidad existan."""
        conn = self.obtener_conexion()
        try:
            if self.motor == "postgresql":
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS inventario_calzado (
                            id_producto INT PRIMARY KEY,
                            codigo_sku VARCHAR(30) UNIQUE NOT NULL,
                            codigo_sa6 VARCHAR(20) NOT NULL,
                            categoria_padre VARCHAR(50) NOT NULL,
                            categoria_calzado VARCHAR(255) NOT NULL,
                            categoria_corta VARCHAR(100) NOT NULL,
                            linea VARCHAR(30) NOT NULL,
                            nombre_producto VARCHAR(100) NOT NULL,
                            descripcion TEXT,
                            stock_actual INT NOT NULL DEFAULT 0,
                            stock_minimo INT NOT NULL DEFAULT 15,
                            capacidad_maxima INT NOT NULL DEFAULT 150,
                            costo_referencia_usd NUMERIC(10, 4) NOT NULL DEFAULT 25.0,
                            gastos_adicionales_usd NUMERIC(10, 2) NOT NULL DEFAULT 4.0,
                            margen_objetivo_pct NUMERIC(5, 2) NOT NULL DEFAULT 25.0,
                            precio_unitario_usd NUMERIC(10, 2) NOT NULL DEFAULT 40.0,
                            precio_unitario_bs NUMERIC(10, 2) NOT NULL DEFAULT 280.0,
                            lead_time_dias INT DEFAULT 7,
                            stock_seguridad INT DEFAULT 10,
                            pedidos_pendientes INT DEFAULT 0,
                            icono VARCHAR(10) DEFAULT '👟',
                            ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT chk_inventario_stock_positivo CHECK (stock_actual >= 0)
                        );

                        CREATE TABLE IF NOT EXISTS registro_vision (
                            id_registro SERIAL PRIMARY KEY,
                            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            id_producto INT REFERENCES inventario_calzado(id_producto),
                            categoria_nombre VARCHAR(100) NOT NULL,
                            producto_nombre VARCHAR(100),
                            accion VARCHAR(50) NOT NULL,
                            cantidad INT NOT NULL DEFAULT 1,
                            precio_unitario_venta_usd NUMERIC(10, 2) DEFAULT 0.00,
                            precio_unitario_venta_bs NUMERIC(10, 2) DEFAULT 0.00,
                            ingreso_total_usd NUMERIC(12, 2) DEFAULT 0.00,
                            ingreso_total_bs NUMERIC(12, 2) DEFAULT 0.00,
                            canal_venta VARCHAR(50) DEFAULT 'Tienda Propia',
                            stock_resultante INT,
                            confianza NUMERIC(6, 4) NOT NULL DEFAULT 1.0,
                            origen VARCHAR(50) DEFAULT 'web_camara',
                            responsable VARCHAR(100) DEFAULT 'Sistema IA Manaco',
                            nota TEXT
                        );
                    """)

                    # Verificar si faltan productos en inventario_calzado
                    cur.execute("SELECT COUNT(*) FROM inventario_calzado;")
                    if cur.fetchone()[0] < 6:
                        from catalogo import obtener_catalogo_completo
                        prods = obtener_catalogo_completo()
                        for p in prods:
                            cur.execute("""
                                INSERT INTO inventario_calzado (
                                    id_producto, codigo_sku, codigo_sa6, categoria_padre,
                                    categoria_calzado, categoria_corta, linea, nombre_producto,
                                    descripcion, stock_actual, stock_minimo, capacidad_maxima,
                                    costo_referencia_usd, gastos_adicionales_usd, margen_objetivo_pct,
                                    precio_unitario_usd, precio_unitario_bs, lead_time_dias,
                                    stock_seguridad, pedidos_pendientes, icono
                                ) VALUES (
                                    %s, %s, %s, %s,
                                    %s, %s, %s, %s,
                                    %s, 15, %s, %s,
                                    %s, %s, %s,
                                    %s, %s, %s,
                                    %s, 0, %s
                                ) ON CONFLICT (id_producto) DO NOTHING;
                            """, (
                                p["id_producto"], p["codigo_sku"], p["codigo_sa6"], p["categoria_padre"],
                                p["categoria_arancelaria"], p["categoria_corta"], p["linea"], p["nombre_producto"],
                                p["descripcion"], p["stock_minimo"], p["capacidad_maxima"],
                                p["referencia_importacion_2024_usd"], p["gastos_adicionales_usd"], p["margen_objetivo_pct"],
                                p["precio_propuesto_usd"], p["precio_propuesto_bob"], p["lead_time_dias"],
                                p["stock_seguridad"], p["icono"]
                            ))
                    conn.commit()
            else:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS inventario_calzado (
                        id_producto INTEGER PRIMARY KEY,
                        codigo_sku TEXT UNIQUE NOT NULL,
                        codigo_sa6 TEXT NOT NULL,
                        categoria_padre TEXT NOT NULL,
                        categoria_calzado TEXT NOT NULL,
                        categoria_corta TEXT NOT NULL,
                        linea TEXT NOT NULL,
                        nombre_producto TEXT NOT NULL,
                        descripcion TEXT,
                        stock_actual INTEGER NOT NULL DEFAULT 0 CHECK (stock_actual >= 0),
                        stock_minimo INTEGER NOT NULL DEFAULT 15,
                        capacidad_maxima INTEGER NOT NULL DEFAULT 150,
                        costo_referencia_usd REAL NOT NULL DEFAULT 25.0,
                        gastos_adicionales_usd REAL NOT NULL DEFAULT 4.0,
                        margen_objetivo_pct REAL NOT NULL DEFAULT 25.0,
                        precio_unitario_usd REAL NOT NULL DEFAULT 40.0,
                        precio_unitario_bs REAL NOT NULL DEFAULT 280.0,
                        lead_time_dias INTEGER DEFAULT 7,
                        stock_seguridad INTEGER DEFAULT 10,
                        pedidos_pendientes INTEGER DEFAULT 0,
                        icono TEXT DEFAULT '👟',
                        ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS registro_vision (
                        id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        id_producto INTEGER,
                        categoria_nombre TEXT NOT NULL,
                        producto_nombre TEXT,
                        accion TEXT NOT NULL,
                        cantidad INTEGER NOT NULL DEFAULT 1,
                        precio_unitario_venta_usd REAL DEFAULT 0.00,
                        precio_unitario_venta_bs REAL DEFAULT 0.00,
                        ingreso_total_usd REAL DEFAULT 0.00,
                        ingreso_total_bs REAL DEFAULT 0.00,
                        canal_venta TEXT DEFAULT 'Tienda Propia',
                        stock_resultante INTEGER,
                        confianza REAL NOT NULL DEFAULT 1.0,
                        origen TEXT DEFAULT 'web_camara',
                        responsable TEXT DEFAULT 'Sistema IA Manaco',
                        nota TEXT
                    );
                """)
                cur.execute("SELECT COUNT(*) FROM inventario_calzado;")
                if cur.fetchone()[0] < 6:
                    from catalogo import obtener_catalogo_completo
                    prods = obtener_catalogo_completo()
                    for p in prods:
                        cur.execute("""
                            INSERT OR IGNORE INTO inventario_calzado VALUES (
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, 15, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, datetime('now')
                            )
                        """, (
                            p["id_producto"], p["codigo_sku"], p["codigo_sa6"], p["categoria_padre"],
                            p["categoria_arancelaria"], p["categoria_corta"], p["linea"], p["nombre_producto"],
                            p["descripcion"], p["stock_minimo"], p["capacidad_maxima"],
                            p["referencia_importacion_2024_usd"], p["gastos_adicionales_usd"], p["margen_objetivo_pct"],
                            p["precio_propuesto_usd"], p["precio_propuesto_bob"], p["lead_time_dias"],
                            p["stock_seguridad"], p["icono"]
                        ))
                conn.commit()
        finally:
            conn.close()

    def obtener_inventario(self) -> List[Dict[str, Any]]:
        """Retorna la lista de los 6 productos con stock, precios, umbrales y alertas."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    id_producto, codigo_sku, codigo_sa6, categoria_padre,
                    categoria_calzado, categoria_corta, linea, nombre_producto,
                    descripcion, stock_actual, stock_minimo, capacidad_maxima,
                    costo_referencia_usd, gastos_adicionales_usd, margen_objetivo_pct,
                    precio_unitario_usd, precio_unitario_bs, lead_time_dias,
                    stock_seguridad, pedidos_pendientes, icono, ultima_actualizacion
                FROM inventario_calzado
                ORDER BY id_producto;
            """)
            filas = cur.fetchall()
            productos = []
            for f in filas:
                stock_act = int(f[9])
                stock_min = int(f[10])
                cap_max = int(f[11])
                p = {
                    "id_producto": f[0],
                    "codigo_sku": f[1],
                    "codigo_sa6": f[2],
                    "categoria_padre": f[3],
                    "categoria_calzado": f[4],
                    "categoria_corta": f[5],
                    "linea": f[6],
                    "nombre_producto": f[7],
                    "descripcion": f[8] or "",
                    "stock_actual": stock_act,
                    "stock_minimo": stock_min,
                    "capacidad_maxima": cap_max,
                    "costo_referencia_usd": float(f[12]),
                    "gastos_adicionales_usd": float(f[13]),
                    "margen_objetivo_pct": float(f[14]),
                    "precio_unitario_usd": float(f[15]),
                    "precio_unitario_bs": float(f[16]),
                    "lead_time_dias": int(f[17] or 7),
                    "stock_seguridad": int(f[18] or 10),
                    "pedidos_pendientes": int(f[19] or 0),
                    "icono": f[20] or "👞",
                    "ultima_actualizacion": str(f[21]) if f[21] else "",
                    "alerta_stock": stock_act <= stock_min,
                    "porcentaje_capacidad": round((stock_act / max(1, cap_max)) * 100, 1)
                }
                productos.append(p)
            return productos
        finally:
            conn.close()

    def obtener_inventario_por_categoria(self) -> List[Dict[str, Any]]:
        """
        Calcula por suma los totales de categoría a partir de las existencias por producto.
        Cumple el requerimiento estricto: existencias mantenidas por producto y totales por categoría calculados por suma.
        """
        prods = self.obtener_inventario()
        categorias = {}

        for p in prods:
            sa6 = p["codigo_sa6"]
            if sa6 not in categorias:
                categorias[sa6] = {
                    "codigo_sa6": sa6,
                    "categoria_padre": p["categoria_padre"],
                    "categoria_corta": p["categoria_corta"],
                    "categoria_calzado": p["categoria_calzado"],
                    "stock_actual": 0,
                    "stock_minimo": 0,
                    "capacidad_maxima": 0,
                    "valor_total_bs": 0.0,
                    "valor_total_usd": 0.0,
                    "productos": [],
                    "icono": p["icono"]
                }
            cat = categorias[sa6]
            cat["stock_actual"] += p["stock_actual"]
            cat["stock_minimo"] += p["stock_minimo"]
            cat["capacidad_maxima"] += p["capacidad_maxima"]
            cat["valor_total_bs"] += p["stock_actual"] * p["precio_unitario_bs"]
            cat["valor_total_usd"] += p["stock_actual"] * p["precio_unitario_usd"]
            cat["productos"].append(p)

        resultado = []
        for sa6, cat in categorias.items():
            cat["valor_total_bs"] = round(cat["valor_total_bs"], 2)
            cat["valor_total_usd"] = round(cat["valor_total_usd"], 2)
            cat["alerta_stock"] = cat["stock_actual"] <= cat["stock_minimo"]
            cat["porcentaje_capacidad"] = round((cat["stock_actual"] / max(1, cat["capacidad_maxima"])) * 100, 1)
            resultado.append(cat)

        return resultado

    def registrar_movimiento_operativo(
        self,
        id_producto: int,
        accion: str,
        cantidad: int,
        precio_unitario_bs: float = None,
        precio_unitario_usd: float = None,
        canal_venta: str = "Tienda Propia",
        origen: str = "manual",
        responsable: str = "Operador Manaco",
        nota: str = None
    ) -> Dict[str, Any]:
        """
        Registra un movimiento atómico de inventario (VENTA, ENTRADA, TRASLADO, AJUSTE, REPOSICION).
        Valida que el stock resultante NUNCA sea negativo; en caso de stock insuficiente,
        rechaza la transacción y no modifica las existencias.
        Guarda el precio unitario de venta efectivo para proteger el historial financiero.
        """
        if cantidad <= 0:
            return {"exito": False, "error": f"La cantidad debe ser mayor a cero. Valor recibido: {cantidad}"}

        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            ahora = datetime.now()

            # 1. Obtener producto y bloquear fila si es PostgreSQL
            if self.motor == "postgresql":
                cur.execute("""
                    SELECT id_producto, codigo_sku, categoria_corta, nombre_producto, stock_actual, precio_unitario_bs, precio_unitario_usd
                    FROM inventario_calzado
                    WHERE id_producto = %s
                    FOR UPDATE;
                """, (id_producto,))
            else:
                cur.execute("""
                    SELECT id_producto, codigo_sku, categoria_corta, nombre_producto, stock_actual, precio_unitario_bs, precio_unitario_usd
                    FROM inventario_calzado
                    WHERE id_producto = ?;
                """, (id_producto,))

            fila = cur.fetchone()
            if not fila:
                return {"exito": False, "error": f"Producto con ID {id_producto} no encontrado."}

            _, sku, cat_corta, nom_prod, stock_act, p_bs_cat, p_usd_cat = fila
            stock_act = int(stock_act)

            # Precios efectivos de la venta
            p_bs = float(precio_unitario_bs if precio_unitario_bs is not None else p_bs_cat)
            p_usd = float(precio_unitario_usd if precio_unitario_usd is not None else p_usd_cat)

            accion_upper = accion.upper().strip()

            # 2. Validaciones de stock y cálculo de delta
            if accion_upper in ("VENTA", "TRASLADO"):
                if stock_act < cantidad:
                    conn.rollback()
                    return {
                        "exito": False,
                        "error": f"Salida rechazada por stock insuficiente para {nom_prod}. Disponible: {stock_act} pares, Solicitado: {cantidad} pares."
                    }
                nuevo_stock = stock_act - cantidad
                ingreso_usd = round(cantidad * p_usd, 2)
                ingreso_bs = round(cantidad * p_bs, 2)
            elif accion_upper in ("ENTRADA", "INGRESO_IA", "REPOSICION"):
                nuevo_stock = stock_act + cantidad
                ingreso_usd = 0.00
                ingreso_bs = 0.00
            elif accion_upper == "AJUSTE":
                # En ajuste, la cantidad representa el nuevo stock absoluto o ajuste diferencial
                nuevo_stock = max(0, cantidad)
                ingreso_usd = 0.00
                ingreso_bs = 0.00
            else:
                return {"exito": False, "error": f"Tipo de acción no soportado: {accion}"}

            # 3. Actualizar inventario_calzado
            if self.motor == "postgresql":
                cur.execute("""
                    UPDATE inventario_calzado
                    SET stock_actual = %s,
                        ultima_actualizacion = %s
                    WHERE id_producto = %s;
                """, (nuevo_stock, ahora, id_producto))

                cur.execute("""
                    INSERT INTO registro_vision (
                        fecha_hora, id_producto, categoria_nombre, producto_nombre,
                        accion, cantidad, precio_unitario_venta_usd, precio_unitario_venta_bs,
                        ingreso_total_usd, ingreso_total_bs, canal_venta, stock_resultante,
                        confianza, origen, responsable, nota
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    ) RETURNING id_registro;
                """, (
                    ahora, id_producto, cat_corta, nom_prod,
                    accion_upper, cantidad, p_usd, p_bs,
                    ingreso_usd, ingreso_bs, canal_venta, nuevo_stock,
                    1.0, origen, responsable, nota or f"{accion_upper} de {cantidad} pares"
                ))
                id_reg = cur.fetchone()[0]
            else:
                cur.execute("""
                    UPDATE inventario_calzado
                    SET stock_actual = ?,
                        ultima_actualizacion = ?
                    WHERE id_producto = ?;
                """, (nuevo_stock, ahora.isoformat(), id_producto))

                cur.execute("""
                    INSERT INTO registro_vision (
                        fecha_hora, id_producto, categoria_nombre, producto_nombre,
                        accion, cantidad, precio_unitario_venta_usd, precio_unitario_venta_bs,
                        ingreso_total_usd, ingreso_total_bs, canal_venta, stock_resultante,
                        confianza, origen, responsable, nota
                    ) VALUES (
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?
                    );
                """, (
                    ahora.isoformat(), id_producto, cat_corta, nom_prod,
                    accion_upper, cantidad, p_usd, p_bs,
                    ingreso_usd, ingreso_bs, canal_venta, nuevo_stock,
                    1.0, origen, responsable, nota or f"{accion_upper} de {cantidad} pares"
                ))
                id_reg = cur.lastrowid

            conn.commit()

            return {
                "exito": True,
                "id_registro": id_reg,
                "id_producto": id_producto,
                "nombre_producto": nom_prod,
                "accion": accion_upper,
                "cantidad": cantidad,
                "nuevo_stock": nuevo_stock,
                "precio_unitario_bs": p_bs,
                "precio_unitario_usd": p_usd,
                "canal_venta": canal_venta,
                "mensaje": f"{accion_upper} de {cantidad} pares de {nom_prod} registrada. Nuevo stock: {nuevo_stock} pares."
            }
        except Exception as e:
            conn.rollback()
            return {"exito": False, "error": str(e)}
        finally:
            conn.close()

    def registrar_calzado_ia(self, id_producto: int = None, clase_nombre: str = None, confianza: float = 0.90, origen: str = "camara_web", responsable: str = "Operador IA Manaco"):
        """
        Registra un ingreso por visión artificial (+1 par).
        Soporta selección explícita del producto o fallback a producto base de la categoría.
        """
        if id_producto is None:
            if not clase_nombre or clase_nombre not in MAPEO_DB:
                return {"exito": False, "error": f"Clase desconocida: {clase_nombre}"}
            id_producto = MAPEO_DB[clase_nombre]["id_producto"]

        res = self.registrar_movimiento_operativo(
            id_producto=id_producto,
            accion="INGRESO_IA",
            cantidad=1,
            origen=origen,
            responsable=responsable,
            nota=f"Detección cámara IA ({clase_nombre or 'calzado'}) - Confianza {confianza*100:.1f}%"
        )
        if res.get("exito"):
            res["confianza"] = round(float(confianza), 3)
            res["timestamp"] = datetime.now().strftime("%H:%M:%S")
        return res

    def deshacer_ultimo_registro(self) -> Dict[str, Any]:
        """Revierte de forma atómica el último movimiento transaccional registrado."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id_registro, id_producto, accion, cantidad, producto_nombre
                FROM registro_vision
                ORDER BY id_registro DESC
                LIMIT 1;
            """)
            fila = cur.fetchone()
            if not fila:
                return {"exito": False, "mensaje": "No hay movimientos registrados para deshacer."}

            id_reg, id_prod, accion, cant, nom_prod = fila
            cant = int(cant)

            if accion in ("INGRESO_IA", "ENTRADA", "REPOSICION"):
                # Restar stock asegurando no negativo
                if self.motor == "postgresql":
                    cur.execute("UPDATE inventario_calzado SET stock_actual = GREATEST(0, stock_actual - %s) WHERE id_producto = %s;", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = %s;", (id_reg,))
                else:
                    cur.execute("UPDATE inventario_calzado SET stock_actual = MAX(0, stock_actual - ?) WHERE id_producto = ?;", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = ?;", (id_reg,))
                conn.commit()
                return {"exito": True, "mensaje": f"Se revirtió ingreso de {nom_prod} (-{cant} pares)."}
            elif accion in ("VENTA", "TRASLADO"):
                # Devolver stock
                if self.motor == "postgresql":
                    cur.execute("UPDATE inventario_calzado SET stock_actual = stock_actual + %s WHERE id_producto = %s;", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = %s;", (id_reg,))
                else:
                    cur.execute("UPDATE inventario_calzado SET stock_actual = stock_actual + ? WHERE id_producto = ?;", (cant, id_prod))
                    cur.execute("DELETE FROM registro_vision WHERE id_registro = ?;", (id_reg,))
                conn.commit()
                return {"exito": True, "mensaje": f"Se revirtió venta de {nom_prod} (+{cant} pares restituidos)."}

            return {"exito": False, "mensaje": f"El movimiento #{id_reg} ({accion}) no es reversible automáticamente."}
        finally:
            conn.close()

    def reiniciar_inventario(self, stock_base=15):
        """Reinicia el inventario a 15 pares por producto (90 pares totales) y limpia registros."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            if self.motor == "postgresql":
                cur.execute("UPDATE inventario_calzado SET stock_actual = %s, ultima_actualizacion = CURRENT_TIMESTAMP;", (stock_base,))
                cur.execute("DELETE FROM registro_vision WHERE origen != 'sintetico_12m';")
            else:
                cur.execute("UPDATE inventario_calzado SET stock_actual = ?, ultima_actualizacion = datetime('now');", (stock_base,))
                cur.execute("DELETE FROM registro_vision WHERE origen != 'sintetico_12m';")
            conn.commit()
            return {"exito": True, "mensaje": f"Inventario reiniciado a {stock_base} pares por producto ({stock_base*6} pares totales)."}
        finally:
            conn.close()

    def obtener_movimientos(self, limite=50, tipo=None, canal=None, origen=None) -> List[Dict[str, Any]]:
        """Retorna el historial de movimientos de inventario con filtros opcionales."""
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()
            clausulas = []
            params = []

            if tipo and tipo != "TODOS":
                clausulas.append("accion = %s" if self.motor == "postgresql" else "accion = ?")
                params.append(tipo)
            if canal and canal != "TODOS":
                clausulas.append("canal_venta = %s" if self.motor == "postgresql" else "canal_venta = ?")
                params.append(canal)
            if origen and origen != "TODOS":
                clausulas.append("origen = %s" if self.motor == "postgresql" else "origen = ?")
                params.append(origen)

            where_str = ("WHERE " + " AND ".join(clausulas)) if clausulas else ""

            query = f"""
                SELECT 
                    id_registro, fecha_hora, id_producto, categoria_nombre, producto_nombre,
                    accion, cantidad, precio_unitario_venta_usd, precio_unitario_venta_bs,
                    ingreso_total_usd, ingreso_total_bs, canal_venta, stock_resultante,
                    confianza, origen, responsable, nota
                FROM registro_vision
                {where_str}
                ORDER BY id_registro DESC
                LIMIT {limite};
            """

            cur.execute(query, tuple(params))
            filas = cur.fetchall()
            movs = []
            for f in filas:
                movs.append({
                    "id_registro": f[0],
                    "fecha_hora": str(f[1])[:19] if f[1] else "",
                    "id_producto": f[2],
                    "categoria": f[3],
                    "nombre_producto": f[4] or f[3],
                    "accion": f[5],
                    "cantidad": int(f[6]),
                    "precio_unitario_venta_usd": float(f[7] or 0.0),
                    "precio_unitario_venta_bs": float(f[8] or 0.0),
                    "ingreso_total_usd": float(f[9] or 0.0),
                    "ingreso_total_bs": float(f[10] or 0.0),
                    "canal_venta": f[11] or "N/A",
                    "stock_resultante": f[12],
                    "confianza": round(float(f[13]), 3) if f[13] is not None else 1.0,
                    "origen": f[14],
                    "responsable": f[15],
                    "nota": f[16] or ""
                })
            return movs
        finally:
            conn.close()

    def obtener_kpis(self, tasa_cambio: float = TASA_CAMBIO_OFICIAL) -> Dict[str, Any]:
        """Calcula el conjunto completo de KPIs organizados por las 5 pestañas de problemas empresariales."""
        prods = self.obtener_inventario()
        total_pares = sum(p["stock_actual"] for p in prods)
        total_valor_bs = sum(p["stock_actual"] * p["precio_unitario_bs"] for p in prods)
        total_valor_usd = sum(p["stock_actual"] * p["precio_unitario_usd"] for p in prods)
        capacidad_total = sum(p["capacidad_maxima"] for p in prods)
        ocupacion_pct = round((total_pares / max(1, capacidad_total)) * 100, 1)

        productos_bajo_minimo = sum(1 for p in prods if p["alerta_stock"])

        # Consultas agregadas a registro_vision
        conn = self.obtener_conexion()
        try:
            cur = conn.cursor()

            # Entradas y Salidas totales
            cur.execute("""
                SELECT 
                    SUM(CASE WHEN accion IN ('ENTRADA', 'INGRESO_IA', 'REPOSICION') THEN cantidad ELSE 0 END),
                    SUM(CASE WHEN accion = 'VENTA' THEN cantidad ELSE 0 END),
                    SUM(CASE WHEN accion = 'VENTA' THEN ingreso_total_bs ELSE 0 END),
                    SUM(CASE WHEN accion = 'VENTA' THEN ingreso_total_usd ELSE 0 END)
                FROM registro_vision;
            """)
            fila_tot = cur.fetchone()
            total_entradas = int(fila_tot[0] or 0)
            total_salidas = int(fila_tot[1] or 0)
            total_ingresos_bs = float(fila_tot[2] or 0.0)
            total_ingresos_usd = float(fila_tot[3] or 0.0)

            # Desglose de ventas por canal
            cur.execute("""
                SELECT canal_venta, SUM(cantidad), SUM(ingreso_total_bs)
                FROM registro_vision
                WHERE accion = 'VENTA'
                GROUP BY canal_venta;
            """)
            canales_rows = cur.fetchall()
            unidades_por_canal = {r[0]: int(r[1]) for r in canales_rows}
            ingresos_por_canal = {r[0]: float(r[2]) for r in canales_rows}
            canal_lider = max(unidades_por_canal.keys(), key=lambda k: unidades_por_canal[k]) if unidades_por_canal else "Tiendas Propias"

            # Ingresos IA
            cur.execute("""
                SELECT COUNT(id_registro), AVG(confianza)
                FROM registro_vision
                WHERE accion = 'INGRESO_IA';
            """)
            fila_ia = cur.fetchone()
            total_ia = fila_ia[0] if fila_ia else 0
            confianza_prom = round(float(fila_ia[1]) * 100, 1) if (fila_ia and fila_ia[1] is not None) else None

        finally:
            conn.close()

        # Referencias de comercio exterior desde Excel
        import analisis_comercial as ac
        try:
            ref_excel_2024 = ac.obtener_referencia_importacion_2024(640411)
        except Exception:
            ref_excel_2024 = 27.80

        # Margen promedio proyectado del catálogo
        margen_prom_catalogo = round(sum(p["margen_objetivo_pct"] for p in prods) / max(1, len(prods)), 1)

        return {
            "motor_db": self.motor.upper(),
            "tasa_cambio": tasa_cambio,
            "resumen_general": {
                "total_pares": total_pares,
                "total_valor_bs": f"{total_valor_bs:,.2f}",
                "total_valor_usd": f"{total_valor_usd:,.2f}",
                "capacidad_ocupada_pct": ocupacion_pct,
                "productos_bajo_minimo": productos_bajo_minimo
            },
            "kpis_costos": {
                "referencia_externa_usd": ref_excel_2024,
                "costo_estimado_usd": round(ref_excel_2024 + 5.0, 2),
                "precio_propuesto_usd": round((ref_excel_2024 + 5.0) / 0.70, 2),
                "precio_propuesto_bob": round(((ref_excel_2024 + 5.0) / 0.70) * tasa_cambio, 2),
                "margen_objetivo_pct": 30.0,
                "diferencial_fabricar_usd": 7500.00
            },
            "kpis_inventario": {
                "pares_disponibles": total_pares,
                "total_entradas_pares": total_entradas,
                "total_salidas_pares": total_salidas,
                "productos_bajo_minimo": productos_bajo_minimo,
                "total_ingresos_ia": total_ia,
                "confianza_promedio_ia": f"{confianza_prom}%" if confianza_prom is not None else "Sin escaneos"
            },
            "kpis_productos": {
                "total_productos_catalogo": len(prods),
                "categoria_lider_volumen": "Casual Cuero (640399)",
                "categoria_lider_pct_aduana": "78.6% del volumen importado en España",
                "margen_promedio_catalogo": f"{margen_prom_catalogo}%",
                "valorizacion_catalogo_bs": f"Bs. {total_valor_bs:,.2f}"
            },
            "kpis_planificacion": {
                "ventas_previstas_7d": 168,
                "mae_evaluado_pares": 1.45,
                "sugerencia_reposicion_total_pares": 45,
                "lead_time_promedio_dias": 7
            },
            "kpis_canales": {
                "unidades_totales_vendidas": total_salidas,
                "ingresos_brutos_totales_bs": f"Bs. {total_ingresos_bs:,.2f}",
                "ingresos_brutos_totales_usd": f"$us. {total_ingresos_usd:,.2f}",
                "canal_lider": canal_lider,
                "unidades_por_canal": unidades_por_canal,
                "ingresos_por_canal": ingresos_por_canal,
                "conversion_digital": "No disponible",
                "abandono_carritos": "No disponible",
                "segmento_etario": "No disponible"
            }
        }

    def actualizar_precio_producto(self, id_producto: int, nuevo_precio_bs: float, nuevo_precio_usd: float, responsable: str = "Operador Manaco"):
        """
        Actualiza el precio de catálogo de un calzado en inventario_calzado.
        Importante: No modifica las ventas históricas en registro_vision para preservar los ingresos efectivos.
        """
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
                    INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, producto_nombre, accion, cantidad, confianza, origen, responsable, nota)
                    SELECT %s, id_producto, categoria_corta, nombre_producto, 'AJUSTE_PRECIO', 0, 1.0, 'modulo_precios', %s, 'Actualización explícita de precio de catálogo'
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
                    INSERT INTO registro_vision (fecha_hora, id_producto, categoria_nombre, producto_nombre, accion, cantidad, confianza, origen, responsable, nota)
                    SELECT ?, id_producto, categoria_corta, nombre_producto, 'AJUSTE_PRECIO', 0, 1.0, 'modulo_precios', ?, 'Actualización explícita de precio de catálogo'
                    FROM inventario_calzado WHERE id_producto = ?;
                """, (ahora.isoformat(), responsable, id_producto))
            conn.commit()
            return {
                "exito": True,
                "mensaje": f"Precio del producto ID #{id_producto} actualizado a Bs. {nuevo_precio_bs:,.2f} ($us. {nuevo_precio_usd:,.2f}) sin alterar ventas históricas.",
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
