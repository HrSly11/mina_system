from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import get_current_user
from utils.db import execute_insert, execute_query
from utils.exports import df_to_excel, df_to_pdf
from utils.historial import registrar_accion


def _get_trabajadores_activos():
    return execute_query(
        """
        SELECT id, nombre_completo
        FROM trabajadores
        WHERE activo = TRUE
        ORDER BY nombre_completo
        """
    )


def _ensure_alquiler_tables():
    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS alquiler_cuarto (
            id SERIAL PRIMARY KEY,
            periodo_carga_id INTEGER REFERENCES cargas(id),
            tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('individual', 'compartido', 'sin_pago')),
            referencia VARCHAR(120),
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE NOT NULL,
            monto_total NUMERIC(10,2) NOT NULL DEFAULT 0,
            sin_pago BOOLEAN NOT NULL DEFAULT FALSE,
            observacion TEXT,
            registrado_por INTEGER REFERENCES usuarios(id),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE alquiler_cuarto ADD COLUMN IF NOT EXISTS pagado BOOLEAN NOT NULL DEFAULT FALSE",
        fetch=False,
    )
    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS alquiler_cuarto_trabajadores (
            id SERIAL PRIMARY KEY,
            alquiler_id INTEGER NOT NULL REFERENCES alquiler_cuarto(id) ON DELETE CASCADE,
            trabajador_id INTEGER NOT NULL REFERENCES trabajadores(id) ON DELETE CASCADE,
            UNIQUE(alquiler_id, trabajador_id)
        )
        """,
        fetch=False,
    )


def _save_alquiler(periodo_id, tipo, referencia, fi, ff, monto_total, sin_pago, observacion, trabajador_ids, pagado=False):
    user = get_current_user()
    monto_final = 0.0 if sin_pago else float(monto_total or 0)

    row = execute_insert(
        """
        INSERT INTO alquiler_cuarto (
            periodo_carga_id, tipo, referencia, fecha_inicio, fecha_fin,
            monto_total, sin_pago, observacion, pagado, registrado_por
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (periodo_id, tipo, referencia, fi, ff, monto_final, sin_pago, observacion, pagado, user.get("id")),
    )
    alquiler_id = row["id"] if row else None

    for trabajador_id in trabajador_ids:
        execute_insert(
            """
            INSERT INTO alquiler_cuarto_trabajadores (alquiler_id, trabajador_id)
            VALUES (%s, %s)
            ON CONFLICT (alquiler_id, trabajador_id) DO NOTHING
            """,
            (alquiler_id, trabajador_id),
            fetch=False,
        )

    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Registro alquiler cuarto tipo={tipo} periodo_id={periodo_id} monto=S/{monto_final} pagado={bool(pagado)}",
        "alquiler_cuarto",
    )


def _get_alquiler_by_id(alquiler_id):
    rows = execute_query(
        """
        SELECT *
        FROM alquiler_cuarto
        WHERE id = %s
        LIMIT 1
        """,
        (alquiler_id,),
    )
    return dict(rows[0]) if rows else None


def _get_alquiler_trabajador_ids(alquiler_id):
    rows = execute_query(
        """
        SELECT trabajador_id
        FROM alquiler_cuarto_trabajadores
        WHERE alquiler_id = %s
        ORDER BY trabajador_id
        """,
        (alquiler_id,),
    )
    return [int(r["trabajador_id"]) for r in rows] if rows else []


def _update_alquiler(
    alquiler_id,
    periodo_id,
    tipo,
    referencia,
    fi,
    ff,
    monto_total,
    sin_pago,
    observacion,
    trabajador_ids,
    pagado=False,
):
    user = get_current_user()
    monto_final = 0.0 if sin_pago else float(monto_total or 0)

    execute_insert(
        """
        UPDATE alquiler_cuarto
        SET periodo_carga_id=%s,
            tipo=%s,
            referencia=%s,
            fecha_inicio=%s,
            fecha_fin=%s,
            monto_total=%s,
            sin_pago=%s,
            observacion=%s,
            pagado=%s,
            registrado_por=%s
        WHERE id=%s
        """,
        (periodo_id, tipo, referencia, fi, ff, monto_final, sin_pago, observacion, pagado, user.get("id"), alquiler_id),
        fetch=False,
    )

    execute_insert(
        "DELETE FROM alquiler_cuarto_trabajadores WHERE alquiler_id = %s",
        (alquiler_id,),
        fetch=False,
    )
    for trabajador_id in trabajador_ids:
        execute_insert(
            """
            INSERT INTO alquiler_cuarto_trabajadores (alquiler_id, trabajador_id)
            VALUES (%s, %s)
            ON CONFLICT (alquiler_id, trabajador_id) DO NOTHING
            """,
            (alquiler_id, trabajador_id),
            fetch=False,
        )

    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Edito alquiler cuarto id={alquiler_id} tipo={tipo} periodo_id={periodo_id} monto=S/{monto_final} pagado={bool(pagado)}",
        "alquiler_cuarto",
    )


def _delete_alquiler(alquiler_id):
    user = get_current_user()
    execute_insert("DELETE FROM alquiler_cuarto WHERE id = %s", (alquiler_id,), fetch=False)
    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Elimino alquiler cuarto id={alquiler_id}",
        "alquiler_cuarto",
    )


def _get_historial(periodo_ids=None):
    _ensure_alquiler_tables()
    query = """
        SELECT
            a.id,
            a.periodo_carga_id,
            a.tipo,
            a.referencia,
            a.fecha_inicio,
            a.fecha_fin,
            a.monto_total,
            a.sin_pago,
            a.pagado,
            a.observacion,
            STRING_AGG(t.nombre_completo, ', ' ORDER BY t.nombre_completo) AS trabajadores
        FROM alquiler_cuarto a
        LEFT JOIN alquiler_cuarto_trabajadores act ON act.alquiler_id = a.id
        LEFT JOIN trabajadores t ON t.id = act.trabajador_id
    """
    params = []
    if periodo_ids:
        query += " WHERE a.periodo_carga_id = ANY(%s)"
        params.append(periodo_ids)

    query += """
        GROUP BY a.id, a.periodo_carga_id, a.tipo, a.referencia,
                 a.fecha_inicio, a.fecha_fin, a.monto_total, a.sin_pago, a.pagado, a.observacion
        ORDER BY a.fecha_inicio DESC, a.id DESC
    """
    return execute_query(query, params if params else None)


def _get_resumen_por_trabajador(periodo_ids=None):
    _ensure_alquiler_tables()
    query = """
        WITH participantes AS (
            SELECT act.alquiler_id, COUNT(*)::numeric AS cant
            FROM alquiler_cuarto_trabajadores act
            GROUP BY act.alquiler_id
        )
        SELECT
            t.id,
            t.nombre_completo AS trabajador,
            COALESCE(SUM(
                CASE
                    WHEN a.sin_pago THEN 0
                    WHEN a.tipo = 'compartido' THEN a.monto_total / NULLIF(p.cant, 0)
                    ELSE a.monto_total
                END
            ), 0) AS total_periodo,
            COUNT(DISTINCT a.id) AS registros
        FROM trabajadores t
        LEFT JOIN alquiler_cuarto_trabajadores act ON act.trabajador_id = t.id
        LEFT JOIN alquiler_cuarto a ON a.id = act.alquiler_id
        LEFT JOIN participantes p ON p.alquiler_id = a.id
        WHERE t.activo = TRUE
    """
    params = []
    if periodo_ids:
        query += " AND a.periodo_carga_id = ANY(%s)"
        params.append(periodo_ids)

    query += """
        GROUP BY t.id, t.nombre_completo
        ORDER BY t.nombre_completo
    """
    return execute_query(query, params if params else None)


def render():
    st.title("🛏️ Alquiler de Cuarto")

    user = get_current_user()
    if user.get("rol") not in ("admin", "socio"):
        st.error("Acceso no autorizado")
        st.stop()

    _ensure_alquiler_tables()
    periodo_id = None

    trabajadores = _get_trabajadores_activos() or []
    opciones_trab = {t["nombre_completo"]: t["id"] for t in trabajadores}

    st.subheader("Registrar alquiler")
    tipo_ui = st.radio(
        "Modalidad",
        ["Individual", "Compartido", "Sin pago (propio)"],
        horizontal=True,
        key="alq_tipo",
    )

    tipo = "individual"
    if tipo_ui == "Compartido":
        tipo = "compartido"
    elif tipo_ui == "Sin pago (propio)":
        tipo = "sin_pago"

    if tipo == "individual":
        nombre = st.selectbox("Trabajador", list(opciones_trab.keys()), key="alq_trab_ind")
        trabajadores_sel_ids = [opciones_trab[nombre]] if nombre else []
    else:
        nombres = st.multiselect("Trabajadores", list(opciones_trab.keys()), key="alq_trab_multi")
        trabajadores_sel_ids = [opciones_trab[n] for n in nombres]

    c1, c2, c3 = st.columns(3)
    with c1:
        fi = st.date_input("Fecha inicio", value=date.today(), key="alq_fi")
    with c2:
        ff = st.date_input("Fecha fin", value=date.today(), key="alq_ff")
    with c3:
        monto = st.number_input(
            "Monto total (S/)",
            min_value=0.0,
            step=0.01,
            value=0.0,
            disabled=(tipo == "sin_pago"),
            key="alq_monto",
        )

    referencia = st.text_input("Cuarto / referencia", key="alq_ref", placeholder="Ejemplo: Cuarto A")
    observacion = st.text_input("Observacion", key="alq_obs")
    pagado = st.checkbox("PAGADO", value=False, key="alq_pagado")

    if st.button("💾 Guardar alquiler", key="alq_save", type="primary"):
        if fi > ff:
            st.error("La fecha inicio no puede ser mayor a la fecha fin.")
        elif not trabajadores_sel_ids:
            st.error("Selecciona al menos un trabajador.")
        elif tipo == "individual" and len(trabajadores_sel_ids) != 1:
            st.error("En alquiler individual solo debe haber un trabajador.")
        else:
            _save_alquiler(
                periodo_id,
                tipo,
                referencia,
                fi,
                ff,
                monto,
                tipo == "sin_pago",
                observacion,
                trabajadores_sel_ids,
                pagado,
            )
            st.success("Alquiler guardado correctamente.")
            st.rerun()

    st.markdown("---")
    st.subheader("Historial")
    rows = _get_historial() or []
    if not rows:
        st.info("No hay registros de alquiler.")
        return

    data = []
    for r in rows:
        rr = dict(r)
        estado_pago = "Pendiente"
        if rr.get("sin_pago"):
            estado_pago = "Sin pago"
        elif rr.get("pagado"):
            estado_pago = "Pagado"

        data.append(
            {
                "ID": rr.get("id"),
                "Tipo": rr.get("tipo"),
                "Trabajadores": rr.get("trabajadores") or "",
                "Referencia": rr.get("referencia") or "",
                "Inicio": rr.get("fecha_inicio"),
                "Fin": rr.get("fecha_fin"),
                "Monto (S/)": float(rr.get("monto_total") or 0),
                "Estado": estado_pago,
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
        key="alq_historial_select",
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
    row_edit = _get_alquiler_by_id(selected_id) if selected_id else None

    if row_edit:
        tipo_value = row_edit.get("tipo") or "individual"
        tipo_ui_default = "Individual"
        if tipo_value == "compartido":
            tipo_ui_default = "Compartido"
        elif tipo_value == "sin_pago":
            tipo_ui_default = "Sin pago (propio)"

        idx_tipo = ["Individual", "Compartido", "Sin pago (propio)"].index(tipo_ui_default)
        edit_tipo_ui = st.radio(
            "Modalidad (edicion)",
            ["Individual", "Compartido", "Sin pago (propio)"],
            index=idx_tipo,
            horizontal=True,
            key="alq_edit_tipo",
        )

        edit_tipo = "individual"
        if edit_tipo_ui == "Compartido":
            edit_tipo = "compartido"
        elif edit_tipo_ui == "Sin pago (propio)":
            edit_tipo = "sin_pago"

        selected_trab_ids = _get_alquiler_trabajador_ids(selected_id)
        id_to_nombre = {v: k for k, v in opciones_trab.items()}
        default_nombres = [id_to_nombre[i] for i in selected_trab_ids if i in id_to_nombre]

        if edit_tipo == "individual":
            default_nombre = default_nombres[0] if default_nombres else list(opciones_trab.keys())[0]
            edit_nombre = st.selectbox(
                "Trabajador (edicion)", list(opciones_trab.keys()),
                index=list(opciones_trab.keys()).index(default_nombre), key="alq_edit_trab_ind"
            )
            edit_trab_ids = [opciones_trab[edit_nombre]] if edit_nombre else []
        else:
            edit_nombres = st.multiselect(
                "Trabajadores (edicion)", list(opciones_trab.keys()),
                default=default_nombres, key="alq_edit_trab_multi"
            )
            edit_trab_ids = [opciones_trab[n] for n in edit_nombres]

        e1, e2, e3 = st.columns(3)
        with e1:
            edit_fi = st.date_input("Fecha inicio (edicion)", value=row_edit.get("fecha_inicio"), key="alq_edit_fi")
        with e2:
            edit_ff = st.date_input("Fecha fin (edicion)", value=row_edit.get("fecha_fin"), key="alq_edit_ff")
        with e3:
            edit_monto = st.number_input(
                "Monto total (S/) (edicion)",
                min_value=0.0,
                step=0.01,
                value=float(row_edit.get("monto_total") or 0),
                disabled=(edit_tipo == "sin_pago"),
                key="alq_edit_monto",
            )

        edit_ref = st.text_input(
            "Cuarto / referencia (edicion)", value=row_edit.get("referencia") or "", key="alq_edit_ref"
        )
        edit_obs = st.text_input(
            "Observacion (edicion)", value=row_edit.get("observacion") or "", key="alq_edit_obs"
        )
        edit_pagado = st.checkbox("PAGADO (edicion)", value=bool(row_edit.get("pagado")), key="alq_edit_pagado")

        if st.button("✏️ Guardar cambios", key="alq_edit_btn", type="secondary"):
            if edit_fi > edit_ff:
                st.error("La fecha inicio no puede ser mayor a la fecha fin.")
            elif not edit_trab_ids:
                st.error("Selecciona al menos un trabajador.")
            elif edit_tipo == "individual" and len(edit_trab_ids) != 1:
                st.error("En alquiler individual solo debe haber un trabajador.")
            else:
                _update_alquiler(
                    selected_id,
                    row_edit.get("periodo_carga_id"),
                    edit_tipo,
                    edit_ref,
                    edit_fi,
                    edit_ff,
                    edit_monto,
                    edit_tipo == "sin_pago",
                    edit_obs,
                    edit_trab_ids,
                    edit_pagado,
                )
                st.success("Registro actualizado correctamente.")
                st.rerun()
    else:
        st.caption("Marca una casilla de la tabla para editar.")

    st.markdown("---")
    st.subheader("Resumen por trabajador")
    resumen_rows = _get_resumen_por_trabajador() or []
    resumen_data = []
    total_general = 0.0
    for r in resumen_rows:
        rr = dict(r)
        total_t = float(rr.get("total_periodo") or 0)
        total_general += total_t
        resumen_data.append(
            {
                "Trabajador": rr.get("trabajador", ""),
                "Registros": int(rr.get("registros") or 0),
                "Total alquiler periodo (S/)": round(total_t, 2),
            }
        )

    df_resumen = pd.DataFrame(resumen_data)
    st.dataframe(df_resumen, use_container_width=True)
    st.metric("Total general alquiler", f"S/ {total_general:,.2f}")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📥 Excel",
            df_to_excel(df_resumen, "Alquiler Cuarto Resumen"),
            file_name="alquiler_cuarto.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with c2:
        st.download_button(
            "📥 PDF",
            df_to_pdf(df_resumen, "Alquiler de Cuarto - Resumen por trabajador"),
            file_name="alquiler_cuarto.pdf",
            mime="application/pdf",
        )

    st.markdown("### Eliminar registro seleccionado")
    if st.button("🗑️ Eliminar", key="alq_del_btn"):
        if not selected_id:
            st.error("Selecciona una fila para eliminar.")
        else:
            _delete_alquiler(selected_id)
            st.success("Registro eliminado.")
            st.rerun()
