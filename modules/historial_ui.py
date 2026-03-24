import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.historial import get_historial
from utils.db import execute_insert
from utils.auth import get_current_user

MODULOS = ["Todos", "planilla", "pension", "sacar_cuentas", "cuenta_final", "permisos", "cargas"]

def render():
    st.title("📜 Historial de Acciones")
    user = get_current_user()

    if user.get("rol") in ("admin", "socio"):
        with st.expander("🗑️ Limpiar historial antiguo", expanded=False):
            qty = st.selectbox(
                "Eliminar los más antiguos",
                [10, 20, 50, 100],
                key="hist_del_qty",
            )
            confirm = st.text_input("Escribe BORRAR para confirmar", key="hist_del_confirm")
            if st.button("Eliminar registros antiguos", key="hist_del_btn"):
                if confirm != "BORRAR":
                    st.error("Debes escribir BORRAR para confirmar.")
                else:
                    execute_insert(
                        """
                        DELETE FROM historial
                        WHERE id IN (
                            SELECT id FROM historial
                            ORDER BY fecha_hora ASC
                            LIMIT %s
                        )
                        """,
                        (qty,),
                    )
                    st.success(f"Se eliminaron {qty} registros más antiguos del historial.")
                    st.rerun()

            st.markdown("---")
            st.caption("⚠️ Acción crítica: borra por completo el historial de la base de datos.")
            confirm_total_1 = st.text_input(
                "Confirmación 1: escribe ELIMINAR TODO",
                key="hist_del_all_confirm_1",
            )
            confirm_total_2 = st.text_input(
                "Confirmación 2: escribe SI, ELIMINAR HISTORIAL",
                key="hist_del_all_confirm_2",
            )
            if st.button("🛑 Borrar todo el historial", key="hist_del_all_btn", type="primary"):
                ok_1 = confirm_total_1.strip() == "ELIMINAR TODO"
                ok_2 = confirm_total_2.strip() == "SI, ELIMINAR HISTORIAL"
                if not (ok_1 and ok_2):
                    st.error("Faltan confirmaciones correctas para borrar todo el historial.")
                else:
                    execute_insert("DELETE FROM historial")
                    st.success("Se eliminó todo el historial correctamente.")
                    st.rerun()
        st.markdown("---")

    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1:
        search = st.text_input("🔍 Buscar (nombre o acción)", key="hist_search")
    with col2:
        modulo = st.selectbox("Módulo", MODULOS, key="hist_modulo")
    with col3:
        filtro_fecha = st.selectbox("Filtro de tiempo", ["Todos", "Hoy", "Esta semana", "Este mes", "Personalizado"], key="hist_filtro")

    fi, ff = None, None
    if filtro_fecha == "Hoy":
        fi = ff = date.today()
    elif filtro_fecha == "Esta semana":
        fi = date.today() - timedelta(days=date.today().weekday())
        ff = date.today()
    elif filtro_fecha == "Este mes":
        fi = date.today().replace(day=1)
        ff = date.today()
    elif filtro_fecha == "Personalizado":
        c1, c2 = st.columns(2)
        with c1:
            fi = st.date_input("Desde", value=date.today().replace(day=1), key="hist_fi")
        with c2:
            ff = st.date_input("Hasta", value=date.today(), key="hist_ff")

    modulo_val = modulo if modulo != "Todos" else ""
    registros = get_historial(search=search, modulo=modulo_val, fecha_inicio=fi, fecha_fin=ff)

    if registros:
        data = []
        for r in registros:
            row = dict(r)
            data.append({
                "Fecha/Hora": row["fecha_hora"].strftime("%d/%m/%Y %H:%M:%S") if row.get("fecha_hora") else "",
                "Usuario": row.get("nombre_usuario", ""),
                "Acción": row.get("accion", ""),
                "Módulo": row.get("modulo", ""),
                "Detalle": row.get("detalle", ""),
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, height=500)
        st.caption(f"{len(data)} registros encontrados")
    else:
        st.info("No se encontraron registros con los filtros aplicados.")
