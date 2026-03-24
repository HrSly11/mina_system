import streamlit as st
import pandas as pd
from datetime import date
from utils.db import execute_query, execute_insert
from utils.historial import registrar_accion
from utils.auth import get_current_user

def ensure_cargas_periodo_schema():
    if st.session_state.get("_schema_cargas_ready"):
        return

    execute_insert(
        "ALTER TABLE cargas ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id)",
        fetch=False,
    )
    execute_insert(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_cargas_periodo_single
        ON cargas(periodo_sistema_id)
        WHERE periodo_sistema_id IS NOT NULL
        """,
        fetch=False,
    )
    st.session_state["_schema_cargas_ready"] = True


def get_carga_por_periodo(periodo_id):
    rows = execute_query(
        """
        SELECT *
        FROM cargas
        WHERE periodo_sistema_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (periodo_id,),
    )
    return dict(rows[0]) if rows else None


def upsert_carga_por_periodo(periodo_id, toneladas, observacion=""):
    user = get_current_user()
    actual = get_carga_por_periodo(periodo_id)

    if actual:
        execute_insert(
            """
            UPDATE cargas
            SET fecha = %s,
                toneladas = %s,
                observacion = %s,
                registrado_por = %s
            WHERE id = %s
            """,
            (date.today(), toneladas, observacion, user.get("id"), actual["id"]),
            fetch=False,
        )
        registrar_accion(
            user.get("id"),
            user.get("nombre_completo"),
            f"Actualizó carga periodo={periodo_id} toneladas={toneladas}",
            "cargas",
        )
        return actual["id"], "actualizada"

    row = execute_insert(
        """
        INSERT INTO cargas (fecha, toneladas, bajada, observacion, registrado_por, periodo_sistema_id)
        VALUES (%s, %s, FALSE, %s, %s, %s)
        RETURNING id
        """,
        (date.today(), toneladas, observacion, user.get("id"), periodo_id),
    )
    nuevo_id = row["id"] if row else None
    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Creó carga periodo={periodo_id} toneladas={toneladas}",
        "cargas",
    )
    return nuevo_id, "creada"


def delete_carga_por_periodo(periodo_id):
    user = get_current_user()
    actual = get_carga_por_periodo(periodo_id)
    if not actual:
        return False

    execute_insert("DELETE FROM cargas WHERE id = %s", (actual["id"],), fetch=False)
    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Eliminó carga periodo={periodo_id} id={actual['id']}",
        "cargas",
    )
    return True

def render():
    st.title("⛏️ Cargas")
    user = get_current_user()
    can_edit = user.get("rol") in ("admin", "socio")
    ensure_cargas_periodo_schema()

    periodo_id = st.session_state.get("periodo_sistema_id")
    if not periodo_id:
        st.warning("Selecciona un periodo activo en el sidebar para gestionar cargas.")
        return

    carga_actual = get_carga_por_periodo(periodo_id)
    toneladas_actual = float(carga_actual.get("toneladas") or 0) if carga_actual else 0.0
    obs_actual = (carga_actual.get("observacion") or "") if carga_actual else ""

    st.info("Registro informativo por periodo activo (no acumulado global).")
    st.metric("Toneladas del periodo activo", f"{toneladas_actual:.2f} ton")

    if can_edit:
        with st.expander("✏️ Registrar / Editar carga del periodo", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                toneladas_c = st.number_input(
                    "Toneladas del periodo",
                    min_value=0.0,
                    value=toneladas_actual,
                    step=0.1,
                    key=f"carga_ton_periodo_{periodo_id}",
                )
            with col2:
                obs_c = st.text_area("Observación", value=obs_actual, key=f"carga_obs_periodo_{periodo_id}")

            cbtn1, cbtn2 = st.columns(2)
            with cbtn1:
                if st.button("💾 Guardar carga del periodo", key=f"carga_save_{periodo_id}", use_container_width=True):
                    _, accion = upsert_carga_por_periodo(periodo_id, toneladas_c, obs_c)
                    st.success("Registro actualizado." if accion == "actualizada" else "Registro creado.")
                    st.rerun()
            with cbtn2:
                if st.button("🗑️ Eliminar carga del periodo", key=f"carga_delete_{periodo_id}", use_container_width=True):
                    ok = delete_carga_por_periodo(periodo_id)
                    if ok:
                        st.success("Registro eliminado. Este periodo quedó en 0.")
                    else:
                        st.warning("No hay registro para eliminar en este periodo.")
                    st.rerun()

    if carga_actual:
        df_view = pd.DataFrame(
            [
                {
                    "ID": carga_actual.get("id"),
                    "Periodo": periodo_id,
                    "Fecha": carga_actual.get("fecha"),
                    "Toneladas": float(carga_actual.get("toneladas") or 0),
                    "Observacion": carga_actual.get("observacion") or "",
                    "Registrado": carga_actual.get("created_at"),
                }
            ]
        )
        st.dataframe(df_view, use_container_width=True)
    else:
        st.info("No hay carga registrada para el periodo activo. Se muestra en cero.")
