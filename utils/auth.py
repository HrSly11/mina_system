import bcrypt
import streamlit as st
from utils.db import execute_query, execute_insert
from utils.historial import registrar_accion

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def login(username: str, password: str):
    rows = execute_query(
        "SELECT * FROM usuarios WHERE username = %s AND activo = TRUE",
        (username,)
    )
    if rows:
        user = dict(rows[0])
        if verify_password(password, user["password_hash"]):
            return user
    return None

def logout():
    for key in ["user", "user_id", "user_rol", "user_nombre"]:
        st.session_state.pop(key, None)
    st.rerun()

def require_login():
    if "user" not in st.session_state:
        st.stop()

def is_admin():
    return st.session_state.get("user", {}).get("rol") == "admin"

def is_socio():
    return st.session_state.get("user", {}).get("rol") == "socio"

def is_pensionista():
    return st.session_state.get("user", {}).get("rol") == "pensionista"

def get_current_user():
    return st.session_state.get("user", {})

def get_all_socios():
    return execute_query("SELECT * FROM usuarios WHERE rol = 'socio' AND activo = TRUE ORDER BY id")

def create_user(username, nombre_completo, password, rol):
    ph = hash_password(password)
    result = execute_insert(
        "INSERT INTO usuarios (username, nombre_completo, password_hash, rol) VALUES (%s,%s,%s,%s) RETURNING id",
        (username, nombre_completo, ph, rol)
    )
    if result:
        registrar_accion(
            st.session_state.get("user", {}).get("id"),
            st.session_state.get("user", {}).get("nombre_completo", "Admin"),
            f"Creó usuario '{username}' con rol '{rol}'",
            "permisos"
        )
    return result


def update_user_basic(user_id, username, nombre_completo, rol):
    try:
        execute_insert(
            """
            UPDATE usuarios
            SET username = %s,
                nombre_completo = %s,
                rol = %s
            WHERE id = %s
            """,
            (username, nombre_completo, rol, user_id),
            fetch=False,
        )

        registrar_accion(
            st.session_state.get("user", {}).get("id"),
            st.session_state.get("user", {}).get("nombre_completo", "Admin"),
            f"Actualizó usuario id={user_id} (@{username}) con rol '{rol}'",
            "permisos",
        )
        return True
    except Exception:
        return False

def update_user_password(user_id, new_password):
    ph = hash_password(new_password)
    execute_insert(
        "UPDATE usuarios SET password_hash = %s WHERE id = %s",
        (ph, user_id)
    )

def toggle_user_active(user_id, activo):
    execute_insert("UPDATE usuarios SET activo = %s WHERE id = %s", (activo, user_id))

def get_all_users():
    return execute_query("SELECT id, username, nombre_completo, rol, activo, created_at FROM usuarios ORDER BY id")
