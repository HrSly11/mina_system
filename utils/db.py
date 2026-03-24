import os
import time
import threading
from pathlib import Path
import psycopg2
import psycopg2.extras
import psycopg2.pool
import streamlit as st
from dotenv import load_dotenv

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:
    get_script_run_ctx = None

load_dotenv()

_QUERY_CACHE = {}
_QUERY_CACHE_LOCK = threading.Lock()
_QUERY_CACHE_MAX_ITEMS = int(os.getenv("DB_QUERY_CACHE_MAX_ITEMS", "500"))
_QUERY_CACHE_TTL_SECONDS = int(os.getenv("DB_QUERY_CACHE_TTL_SECONDS", "12"))


def _cache_key(query, params):
    return (query, repr(params))


def _is_cacheable_select(query, fetch):
    if not fetch:
        return False
    q = (query or "").lstrip().lower()
    return q.startswith("select")


def _cache_get(query, params):
    key = _cache_key(query, params)
    now = time.time()
    with _QUERY_CACHE_LOCK:
        item = _QUERY_CACHE.get(key)
        if not item:
            return None
        expires_at, payload = item
        if expires_at < now:
            _QUERY_CACHE.pop(key, None)
            return None
        # Retorna copia para evitar mutaciones externas sobre la cache.
        return [dict(r) for r in payload]


def _cache_set(query, params, rows):
    key = _cache_key(query, params)
    now = time.time()
    payload = [dict(r) for r in (rows or [])]
    with _QUERY_CACHE_LOCK:
        if len(_QUERY_CACHE) >= _QUERY_CACHE_MAX_ITEMS:
            # Evicción simple por expiración y luego FIFO aproximado.
            expired_keys = [k for k, (exp, _) in _QUERY_CACHE.items() if exp < now]
            for k in expired_keys:
                _QUERY_CACHE.pop(k, None)
            if len(_QUERY_CACHE) >= _QUERY_CACHE_MAX_ITEMS:
                first_key = next(iter(_QUERY_CACHE), None)
                if first_key is not None:
                    _QUERY_CACHE.pop(first_key, None)

        _QUERY_CACHE[key] = (now + _QUERY_CACHE_TTL_SECONDS, payload)


def _cache_clear_all():
    with _QUERY_CACHE_LOCK:
        _QUERY_CACHE.clear()


def _resolve_db_url():
    """Resuelve la URL de BD priorizando secrets de Streamlit y luego .env."""
    db_url = None

    secrets_paths = [
        os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
        os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml"),
    ]
    has_secrets_file = any(os.path.exists(p) for p in secrets_paths)

    has_streamlit_ctx = False
    if get_script_run_ctx is not None:
        try:
            has_streamlit_ctx = get_script_run_ctx() is not None
        except Exception:
            has_streamlit_ctx = False

    if has_secrets_file and has_streamlit_ctx:
        try:
            db_url = st.secrets["database"]["url"]
        except Exception:
            db_url = None

    if not db_url:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost:5432/mina_db")

    return db_url


@st.cache_resource(show_spinner=False)
def _get_connection_pool(db_url: str):
    """Crea un pool de conexiones reutilizable para reducir latencia por handshake."""
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=12,
        dsn=db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _acquire_connection():
    db_url = _resolve_db_url()
    try:
        pool = _get_connection_pool(db_url)
        return pool.getconn(), pool
    except Exception:
        # Fallback seguro si el pool no puede inicializarse.
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn, None


def _release_connection(conn, pool):
    if conn is None:
        return
    if pool is not None:
        try:
            pool.putconn(conn)
            return
        except Exception:
            pass
    try:
        conn.close()
    except Exception:
        pass

def get_connection():
    """Obtiene conexión a la base de datos.
    Primero intenta Streamlit secrets, luego .env"""
    conn, _ = _acquire_connection()
    return conn

def execute_query(query, params=None, fetch=True):
    """Ejecuta una query y retorna resultados."""
    if _is_cacheable_select(query, fetch):
        cached = _cache_get(query, params)
        if cached is not None:
            return cached

    conn, pool = _acquire_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch:
                    rows = cur.fetchall()
                    if _is_cacheable_select(query, fetch):
                        _cache_set(query, params, rows)
                        return [dict(r) for r in rows]
                    return rows
                return None
    finally:
        _release_connection(conn, pool)

def execute_insert(query, params=None, fetch=True):
    """Ejecuta INSERT/UPDATE/DELETE y opcionalmente retorna el primer row."""
    conn, pool = _acquire_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                # Cualquier escritura invalida cache de lecturas.
                _cache_clear_all()
                if not fetch:
                    return None
                try:
                    return cur.fetchone()
                except Exception:
                    return None
    finally:
        _release_connection(conn, pool)

def run_migrations():
    """Ejecuta migraciones SQL en orden (001, 002, 003...)."""
    migrations_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "migrations"
    if not migrations_dir.exists():
        return False

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        return False

    # Evita que dos sesiones de Streamlit intenten migrar al mismo tiempo.
    lock_key = 9412026
    conn, pool = _acquire_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        filename TEXT PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )

                for migration_file in migration_files:
                    filename = migration_file.name
                    cur.execute(
                        "SELECT 1 FROM schema_migrations WHERE filename = %s",
                        (filename,),
                    )
                    if cur.fetchone():
                        continue

                    with open(migration_file, "r", encoding="utf-8") as f:
                        sql = f.read()

                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (filename,),
                    )
                cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
        return True
    except Exception as e:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
        except Exception:
            pass
        st.error(f"Error en migración: {e}")
        return False
    finally:
        _release_connection(conn, pool)
