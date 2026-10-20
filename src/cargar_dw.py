"""
cargar_dw.py
Módulo para la carga transaccional e idempotente del Data Warehouse manaco_dw en PostgreSQL.
Cumple estrictamente con las reglas:
- Actualización transaccional completa (dimensiones y hechos). Reversión ante cualquier error.
- No utiliza DROP TABLE ni CASCADE en la carga habitual.
- No afecta tablas ajenas a las 6 del proyecto.
- Sincroniza secuencias SERIAL y BIGSERIAL tras insertar IDs explícitos.
"""

from pathlib import Path
import os
import sys
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Cargar configuración desde .env
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"

# Configuración de conexión (sin mostrar contraseñas en logs)
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "manaco_dw")


def obtener_conexion():
    """Establece conexión a la base de datos manaco_dw."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5
        )
        return conn
    except Exception as e:
        print(f"[ERROR DE CONEXION]: No se pudo conectar a PostgreSQL ({DB_HOST}:{DB_PORT}/{DB_NAME}).")
        print(f"Detalle técnico: {e}")
        print("\nInstrucciones para resolverlo:")
        print("1. Verifica que el servicio de PostgreSQL esté iniciado (ej. postgresql-x64-18).")
        print("2. Asegúrate de que exista la base de datos 'manaco_dw'.")
        print("3. Revisa las credenciales en el archivo '.env'.")
        sys.exit(1)


def asegurar_esquema(conn):
    """Ejecuta el script DDL no destructivo (CREATE TABLE IF NOT EXISTS)."""
    ddl_path = SQL_DIR / "01_crear_tablas.sql"
    print(f"-> Verificando estructura del esquema ({ddl_path.name})...")
    with conn.cursor() as cur:
        with open(ddl_path, "r", encoding="utf-8") as f:
            ddl_sql = f.read()
        cur.execute(ddl_sql)
    conn.commit()


def sincronizar_secuencias(cur):
    """Sincroniza las secuencias de las columnas SERIAL / BIGSERIAL."""
    secuencias = [
        ("dim_producto", "id_producto", "dim_producto_id_producto_seq"),
        ("dim_reportante", "id_reportante", "dim_reportante_id_reportante_seq"),
        ("dim_socio", "id_socio", "dim_socio_id_socio_seq"),
        ("dim_flujo", "id_flujo", "dim_flujo_id_flujo_seq"),
        ("fact_comercio", "id_hecho", "fact_comercio_id_hecho_seq")
    ]
    for tabla, columna, secuencia in secuencias:
        sql = f"SELECT setval('{secuencia}', COALESCE((SELECT MAX({columna}) FROM {tabla}), 1));"
        cur.execute(sql)
    print("-> Secuencias SERIAL/BIGSERIAL sincronizadas exitosamente.")


def carga_transaccional(conn):
    """
    Ejecuta el ciclo completo de carga dentro de una única transacción:
    1. Vacía las 6 tablas específicas del proyecto respetando dependencias.
    2. Carga dimensiones y hechos desde los archivos procesados.
    3. Sincroniza secuencias.
    4. Confirma la transacción (COMMIT) o revierte completamente (ROLLBACK).
    """
    tablas_orden = [
        ("dim_periodo.csv", "dim_periodo", ["id_periodo", "anio"]),
        ("dim_producto.csv", "dim_producto", ["id_producto", "codigo_sa6", "categoria_calzado"]),
        ("dim_reportante.csv", "dim_reportante", ["id_reportante", "pais_reportante"]),
        ("dim_socio.csv", "dim_socio", ["id_socio", "socio_comercial", "tipo_socio"]),
        ("dim_flujo.csv", "dim_flujo", ["id_flujo", "flujo_comercial"]),
        ("fact_comercio.csv", "fact_comercio", [
            "id_hecho", "id_periodo", "id_producto", "id_reportante", "id_socio", "id_flujo",
            "valor_usd", "cantidad_pares", "valor_usd_por_par", "valor_miles_usd"
        ])
    ]

    print("\n[INICIO] Carga transaccional del Data Warehouse...")
    try:
        with conn.cursor() as cur:
            # 1. Vaciar exclusivamente las 6 tablas del DW sin DROP ni CASCADE general
            print("-> Vaciando tablas del proyecto para actualización consistente...")
            cur.execute("""
                TRUNCATE TABLE 
                    fact_comercio, 
                    dim_flujo, 
                    dim_socio, 
                    dim_reportante, 
                    dim_producto, 
                    dim_periodo 
                RESTART IDENTITY;
            """)

            # 2. Cargar cada archivo CSV respetando integridad
            for archivo_csv, nombre_tabla, columnas_esperadas in tablas_orden:
                ruta_csv = PROCESSED_DIR / archivo_csv
                if not ruta_csv.exists():
                    raise FileNotFoundError(f"Archivo requerido no encontrado: {ruta_csv}")
                
                df = pd.read_csv(ruta_csv)
                # Reordenar y asegurar columnas exactas
                df = df[columnas_esperadas]
                
                print(f"-> Insertando {len(df)} filas en '{nombre_tabla}'...")
                
                # Construir consulta de inserción parametrizada
                columnas_str = ", ".join(columnas_esperadas)
                placeholders = ", ".join(["%s"] * len(columnas_esperadas))
                insert_query = f"INSERT INTO {nombre_tabla} ({columnas_str}) VALUES ({placeholders})"
                
                # Convertir NaN a None para inserción como NULL en Postgres
                valores = [
                    tuple(None if pd.isna(x) else x for x in row)
                    for row in df.itertuples(index=False)
                ]
                
                cur.executemany(insert_query, valores)

            # 3. Sincronizar secuencias tras inserción de claves explícitas
            sincronizar_secuencias(cur)

        # Confirmación atómica
        conn.commit()
        print("[EXITO] Transacción confirmada (COMMIT). Todas las tablas quedaron consistentes.")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR EN LA CARGA] Se revirtió la transacción (ROLLBACK).")
        print(f"Detalle del error: {e}")
        raise e


def asegurar_vistas(conn):
    """Crea o actualiza las vistas analíticas (sql/02_vistas_indicadores.sql)."""
    vistas_path = SQL_DIR / "02_vistas_indicadores.sql"
    print(f"\n-> Aplicando vistas analíticas ({vistas_path.name})...")
    with conn.cursor() as cur:
        with open(vistas_path, "r", encoding="utf-8") as f:
            vistas_sql = f.read()
        cur.execute(vistas_sql)
    conn.commit()
    print("-> Vistas analíticas creadas/actualizadas con éxito.")


def main():
    print("=" * 60)
    print("CARGADOR DEL DATA WAREHOUSE MANACO_DW")
    print("=" * 60)
    
    conn = obtener_conexion()
    try:
        asegurar_esquema(conn)
        carga_transaccional(conn)
        asegurar_vistas(conn)
        print("\nCarga finalizada con éxito.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
