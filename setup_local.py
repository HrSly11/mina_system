#!/usr/bin/env python3
"""
Script de configuración local para el Sistema Minero.
Ejecutar una vez antes de iniciar la app.
"""
import subprocess
import sys
import os
from pathlib import Path

def check_python_deps():
    print("📦 Instalando dependencias Python...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Dependencias instaladas\n")

def setup_env():
    if not os.path.exists(".env"):
        import shutil
        shutil.copy(".env.example", ".env")
        print("✅ Archivo .env creado desde .env.example")
        print("   Por defecto usa: postgresql://postgres:12345@localhost:5432/mina_db\n")
    else:
        print("ℹ️ .env ya existe, no se sobreescribe\n")

def create_database():
    print("🗄️ Creando base de datos 'mina_db'...")
    try:
        import psycopg2
        # Conectar a postgres por defecto
        conn = psycopg2.connect(
            host="localhost", port=5432,
            database="postgres",
            user="postgres", password="12345"
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'mina_db'")
        if cur.fetchone():
            print("ℹ️ Base de datos 'mina_db' ya existe\n")
        else:
            cur.execute("CREATE DATABASE mina_db")
            print("✅ Base de datos 'mina_db' creada\n")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ No se pudo crear la BD automáticamente: {e}")
        print("   Crea manualmente: CREATE DATABASE mina_db;\n")

def run_migrations():
    print("🔄 Ejecutando migraciones...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", port=5432,
            database="mina_db",
            user="postgres", password="12345"
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)

        migrations_dir = Path("migrations")
        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            filename = migration_file.name
            cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,))
            if cur.fetchone():
                continue

            with open(migration_file, "r", encoding="utf-8") as f:
                sql = f.read()
            cur.execute(sql)
            cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,))

        cur.close()
        conn.close()
        print("✅ Migraciones ejecutadas correctamente\n")
    except Exception as e:
        print(f"❌ Error en migraciones: {e}\n")

def main():
    print("=" * 50)
    print("  SETUP - SISTEMA MINERO")
    print("=" * 50 + "\n")

    check_python_deps()
    setup_env()
    create_database()
    run_migrations()

    print("=" * 50)
    print("✅ Setup completado!")
    print("\nPara iniciar la app ejecuta:")
    print("  streamlit run app.py")
    print("\nCredenciales iniciales:")
    print("  Usuario: admin")
    print("  Contraseña: 12345")
    print("=" * 50)

if __name__ == "__main__":
    main()
