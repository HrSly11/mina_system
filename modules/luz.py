from datetime import date

import pandas as pd
import streamlit as st

from modules.cargas import get_periodos_carga
from utils.auth import get_current_user
from utils.db import execute_insert, execute_query
from utils.exports import df_to_excel, df_to_pdf
from utils.historial import registrar_accion


def _ensure_luz_table():
    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS luz_mensual (
            id SERIAL PRIMARY KEY,
            periodo_carga_id INTEGER REFERENCES cargas(id),
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE NOT NULL,
            monto NUMERIC(10,2) NOT NULL DEFAULT 0,
            observacion TEXT,
            registrado_por INTEGER REFERENCES usuarios(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE luz_mensual ADD COLUMN IF NOT EXISTS pagado BOOLEAN NOT NULL DEFAULT FALSE",
        fetch=False,
    )


def _get_luz_by_periodo(periodo_id):
    rows = execute_query(
        """
        SELECT *
        FROM luz_mensual
        WHERE periodo_carga_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (periodo_id,),
    )
    return dict(rows[0]) if rows else None


def _get_luz_by_id(luz_id):
    rows = execute_query(
        """
        SELECT *
        FROM luz_mensual
        WHERE id = %s
        LIMIT 1
        """,
        (luz_id,),
    )
    return dict(rows[0]) if rows else None


def _save_luz(periodo_id, fecha_inicio, fecha_fin, monto, observacion="", pagado=False):
    user = get_current_user()
    execute_insert(
        """
        INSERT INTO luz_mensual (periodo_carga_id, fecha_inicio, fecha_fin, monto, observacion, pagado, registrado_por)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (periodo_id, fecha_inicio, fecha_fin, monto, observacion, pagado, user.get("id")),
        fetch=False,
    )
    accion = f"Registro luz periodo_id={periodo_id} monto=S/{monto} pagado={bool(pagado)}"

    registrar_accion(user.get("id"), user.get("nombre_completo"), accion, "luz")


def _update_luz(luz_id, periodo_id, fecha_inicio, fecha_fin, monto, observacion="", pagado=False):
    user = get_current_user()
    execute_insert(
        """
        UPDATE luz_mensual
        SET periodo_carga_id=%s,
            fecha_inicio=%s,
            fecha_fin=%s,
            monto=%s,
            observacion=%s,
            pagado=%s,
            registrado_por=%s,
            updated_at=NOW()
        WHERE id=%s
        """,
        (periodo_id, fecha_inicio, fecha_fin, monto, observacion, pagado, user.get("id"), luz_id),
        fetch=False,
    )
    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Edito luz id={luz_id} periodo_id={periodo_id} monto=S/{monto} pagado={bool(pagado)}",
        "luz",
    )


def _get_historial_luz():
    return execute_query(
        """
        SELECT l.*, c.fecha AS fecha_carga_inicio, c.fecha_bajada, c.toneladas
        FROM luz_mensual l
        LEFT JOIN cargas c ON c.id = l.periodo_carga_id
        ORDER BY l.fecha_inicio DESC, l.id DESC
        """
    )


def _delete_luz(luz_id):
    user = get_current_user()
    execute_insert("DELETE FROM luz_mensual WHERE id = %s", (luz_id,), fetch=False)
    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Elimino luz id={luz_id}",
        "luz",
    )


def render():
    st.title("⚡ Luz")
    user = get_current_user()
    if user.get("rol") not in ("admin", "socio"):
        st.error("Acceso no autorizado")
        st.stop()

    _ensure_luz_table()

    periodos = get_periodos_carga()
    if not periodos:
        st.info("No hay periodos de carga registrados.")
        return

    labels = [p["label"] for p in periodos]
    selected = st.selectbox("Periodo de carga", labels, key="luz_periodo")
    periodo = next(p for p in periodos if p["label"] == selected)
    periodo_id = periodo["id"]

    fi_default = periodo.get("fecha_inicio")
    ff_default = periodo.get("fecha_fin")
    monto_default = 0.0
    obs_default = ""

    st.markdown("### Registrar / editar cobro de luz")
    with st.form("luz_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha_inicio = st.date_input("Fecha inicio", value=fi_default, key="luz_fi")
        with c2:
            fecha_fin = st.date_input("Fecha fin", value=ff_default, key="luz_ff")
        with c3:
            monto = st.number_input("Monto (S/)", min_value=0.0, step=0.01, value=monto_default, key="luz_monto")

        observacion = st.text_input("Observacion", value=obs_default, key="luz_obs")
        pagado = st.checkbox("PAGADO", value=False, key="luz_pagado")
        submitted = st.form_submit_button("💾 Guardar Luz", type="primary")

    if submitted:
        if fecha_inicio > fecha_fin:
            st.error("La fecha inicio no puede ser mayor a la fecha fin.")
        else:
            _save_luz(periodo_id, fecha_inicio, fecha_fin, monto, observacion, pagado)
            st.success("Luz guardada correctamente.")
            st.rerun()

    st.markdown("---")
    st.subheader("Historial de cobros de luz")
    rows = _get_historial_luz() or []
    if not rows:
        st.info("No hay registros de luz.")
        return

    data = []
    for r in rows:
        rr = dict(r)
        data.append(
            {
                "ID": rr.get("id"),
                "Periodo carga": rr.get("periodo_carga_id"),
                "Inicio": rr.get("fecha_inicio"),
                "Fin": rr.get("fecha_fin"),
                "Monto (S/)": float(rr.get("monto") or 0),
                "Pagado": "Si" if rr.get("pagado") else "No",
                "Observacion": rr.get("observacion") or "",
            }
        )

    df = pd.DataFrame(data)
    df_sel = df.copy()
    df_sel.insert(0, "Seleccionar", False)
    edited_df = st.data_editor(
        df_sel,
        use_container_width=True,
        hide_index=True,
        key="luz_historial_select",
        column_config={"Seleccionar": st.column_config.CheckboxColumn("Seleccionar")},
        disabled=[c for c in df_sel.columns if c != "Seleccionar"],
    )

    selected_rows = edited_df[edited_df["Seleccionar"] == True]
    selected_id = None
    if len(selected_rows) > 1:
        st.warning("Selecciona solo una fila para editar o eliminar.")
    elif len(selected_rows) == 1:
        selected_id = int(selected_rows.iloc[0]["ID"])

    st.markdown("### Editar registro seleccionado")
    row_edit = _get_luz_by_id(selected_id) if selected_id else None

    if row_edit:
        period_map = {p["label"]: p["id"] for p in periodos}
        inv_period_map = {v: k for k, v in period_map.items()}
        default_label = inv_period_map.get(row_edit.get("periodo_carga_id"), labels[0])

        ec1, ec2 = st.columns(2)
        with ec1:
            edit_period_label = st.selectbox(
                "Periodo (edicion)", labels, index=labels.index(default_label), key="luz_edit_periodo"
            )
            edit_fi = st.date_input("Fecha inicio (edicion)", value=row_edit.get("fecha_inicio"), key="luz_edit_fi")
        with ec2:
            edit_monto = st.number_input(
                "Monto (S/) (edicion)",
                min_value=0.0,
                step=0.01,
                value=float(row_edit.get("monto") or 0),
                key="luz_edit_monto",
            )
            edit_ff = st.date_input("Fecha fin (edicion)", value=row_edit.get("fecha_fin"), key="luz_edit_ff")

        edit_obs = st.text_input(
            "Observacion (edicion)", value=row_edit.get("observacion") or "", key="luz_edit_obs"
        )
        edit_pagado = st.checkbox("PAGADO (edicion)", value=bool(row_edit.get("pagado")), key="luz_edit_pagado")

        if st.button("✏️ Guardar cambios", key="luz_edit_btn", type="secondary"):
            if edit_fi > edit_ff:
                st.error("La fecha inicio no puede ser mayor a la fecha fin.")
            else:
                _update_luz(
                    selected_id,
                    period_map[edit_period_label],
                    edit_fi,
                    edit_ff,
                    edit_monto,
                    edit_obs,
                    edit_pagado,
                )
                st.success("Registro actualizado correctamente.")
                st.rerun()
    else:
        st.caption("Marca una casilla de la tabla para editar.")

    st.markdown("### Eliminar registro seleccionado")
    if st.button("🗑️ Eliminar registro", key="luz_del_btn"):
        if not selected_id:
            st.error("Selecciona una fila para eliminar.")
        else:
            _delete_luz(selected_id)
            st.success("Registro eliminado.")
            st.rerun()

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.download_button(
            "📥 Excel",
            df_to_excel(df, "Luz"),
            file_name="luz_historial.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_e2:
        st.download_button(
            "📥 PDF",
            df_to_pdf(df, "Historial de Luz"),
            file_name="luz_historial.pdf",
            mime="application/pdf",
        )
