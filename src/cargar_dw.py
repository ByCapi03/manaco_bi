"""
cargar_dw.py
Módulo para cargar el modelo dimensional y la tabla de hechos en PostgreSQL (Data Warehouse manaco_dw).
"""

from pathlib import Path
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env si existe
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"

# Configuración de conexión a PostgreSQL
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "manaco_dw")

DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def obtener_motor():
    """Crea la conexión SQLAlchemy."""
    print(f"Conectando a PostgreSQL en {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    return create_engine(DB_URI)


def ejecutar_script_sql(engine, ruta_sql: Path):
    """Ejecuta un archivo .sql (ej. creación de tablas o vistas)."""
    print(f"Ejecutando script SQL: {ruta_sql.name}...")
    with engine.connect() as conn:
        with open(ruta_sql, "r", encoding="utf-8") as f:
            query = f.read()
        conn.execute(text(query))
        conn.commit()
    print(f"Script {ruta_sql.name} ejecutado con éxito.")


def cargar_tablas(engine):
    """Carga los CSVs procesados en el orden correcto para respetar foreign keys."""
    tablas_orden = [
        ("dim_periodo.csv", "dim_periodo"),
        ("dim_producto.csv", "dim_producto"),
        ("dim_reportante.csv", "dim_reportante"),
        ("dim_socio.csv", "dim_socio"),
        ("dim_flujo.csv", "dim_flujo"),
        ("fact_comercio.csv", "fact_comercio"),
    ]
    
    with engine.connect() as conn:
        for archivo_csv, nombre_tabla in tablas_orden:
            ruta_csv = PROCESSED_DIR / archivo_csv
            if not ruta_csv.exists():
                print(f"Advertencia: No se encontró {archivo_csv}. Ejecute primero 'src/limpiar_datos.py'.")
                continue
            
            df = pd.read_csv(ruta_csv)
            print(f"Cargando {len(df)} registros en '{nombre_tabla}'...")
            
            # Cargar datos en la tabla existente creada por 01_crear_tablas.sql
            df.to_sql(nombre_tabla, con=engine, if_exists="append", index=False)
            print(f"Tabla '{nombre_tabla}' cargada exitosamente.")


def main():
    print("=" * 60)
    print("Iniciando carga de datos al Data Warehouse (manaco_dw)")
    print("=" * 60)
    
    try:
        engine = obtener_motor()
        
        # 1. Crear tablas si no existen
        ejecutar_script_sql(engine, SQL_DIR / "01_crear_tablas.sql")
        
        # 2. Cargar datos desde data/processed
        cargar_tablas(engine)
        
        # 3. Crear vistas analíticas de KPIs
        ejecutar_script_sql(engine, SQL_DIR / "02_vistas_indicadores.sql")
        
        print("\n¡Proceso de carga completado con éxito!")
        print("La base de datos está lista para ser consumida en Power BI.")
        
    except Exception as e:
        print(f"\n[Error de Conexión o Carga]: {e}")
        print("\nConsejo:")
        print("1. Verifica que el servicio de PostgreSQL esté iniciado.")
        print("2. Crea la base de datos 'manaco_dw' en pgAdmin o DBeaver.")
        print("3. Si tu contraseña de postgres es distinta, ajusta DB_PASSWORD o define un archivo .env.")


if __name__ == "__main__":
    main()
