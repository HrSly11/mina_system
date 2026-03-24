import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.db import execute_query, execute_insert
from utils.historial import registrar_accion
from utils.exports import df_to_excel, df_to_pdf
from utils.auth import get_current_user

# ─── Helpers ────────────────────────────────────────────────────────────────

ESTADO_COLORS = {
    "presente": "🟢",
    "falta": "🔴",
    "permiso": "🟡",
    "pendiente": "⚪",
}

DIAS_ES = [
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"
]


def format_fecha_es(fecha):
    return f"{fecha.strftime('%d/%m/%Y')} ({DIAS_ES[fecha.weekday()]})"


def add_one_month(fecha_base):
    y = fecha_base.year
    m = fecha_base.month + 1
    if m == 13:
        y += 1
        m = 1
    try:
        return fecha_base.replace(year=y, month=m)
    except ValueError:
        # Ajusta para meses con menos dias (ej. 31 -> 30/28).
        d = min(fecha_base.day, 28)
        return fecha_base.replace(year=y, month=m, day=d)


def ensure_planilla_worker_columns():
    if st.session_state.get("_schema_planilla_ready"):
        return

    execute_insert("ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_inicio_planilla DATE DEFAULT CURRENT_DATE")
    execute_insert("ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_fin_planilla DATE")
    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS trabajador_planilla_periodo_config (
            id SERIAL PRIMARY KEY,
            trabajador_id INTEGER NOT NULL REFERENCES trabajadores(id) ON DELETE CASCADE,
            periodo_id INTEGER NOT NULL REFERENCES cuenta_final_periodos(id) ON DELETE CASCADE,
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(trabajador_id, periodo_id)
        )
        """,
        fetch=False,
    )
    st.session_state["_schema_planilla_ready"] = True


def en_rango_planilla(fecha_eval, fi_trab, ff_trab):
    if fecha_eval < fi_trab:
        return False
    if ff_trab and fecha_eval > ff_trab:
        return False
    return True


def save_worker_planilla_range(trabajador_id, periodo_id, fecha_inicio, fecha_fin):
    return execute_insert(
        """
        INSERT INTO trabajador_planilla_periodo_config (trabajador_id, periodo_id, fecha_inicio, fecha_fin, updated_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (trabajador_id, periodo_id)
        DO UPDATE SET
            fecha_inicio = EXCLUDED.fecha_inicio,
            fecha_fin = EXCLUDED.fecha_fin,
            updated_at = NOW()
        RETURNING trabajador_id, fecha_inicio, fecha_fin
        """,
        (trabajador_id, periodo_id, fecha_inicio, fecha_fin),
    )

def get_trabajadores_activos(periodo_id=None):
    pid = periodo_id or st.session_state.get("periodo_sistema_id")
    return execute_query(
        """
        SELECT
            t.*,
                        COALESCE(cfg.fecha_inicio, cp.fecha_inicio, t.fecha_inicio_planilla, CURRENT_DATE) AS fecha_inicio_planilla,
                        COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_planilla) AS fecha_fin_planilla
        FROM trabajadores t
                LEFT JOIN cuenta_final_periodos cp
                    ON cp.id = %s
        LEFT JOIN trabajador_planilla_periodo_config cfg
          ON cfg.trabajador_id = t.id
         AND cfg.periodo_id = %s
        WHERE t.activo = TRUE
        ORDER BY t.nombre_completo
        """,
                (pid, pid),
    )

def get_planilla_periodo(trabajador_id, fecha_inicio, fecha_fin):
    return execute_query("""
        SELECT p.*, t.nombre_completo
        FROM planilla p
        JOIN trabajadores t ON p.trabajador_id = t.id
        WHERE p.trabajador_id = %s AND p.fecha BETWEEN %s AND %s AND p.periodo_sistema_id = %s
        ORDER BY p.fecha
    """, (trabajador_id, fecha_inicio, fecha_fin, st.session_state.get("periodo_sistema_id")))

def get_planilla_todos_periodo(fecha_inicio, fecha_fin):
    return execute_query("""
        SELECT p.fecha, t.nombre_completo, p.estado, p.motivo, p.detalle
        FROM planilla p
        JOIN trabajadores t ON p.trabajador_id = t.id
        WHERE p.fecha BETWEEN %s AND %s AND p.periodo_sistema_id = %s
        ORDER BY t.nombre_completo, p.fecha
    """, (fecha_inicio, fecha_fin, st.session_state.get("periodo_sistema_id")))

def upsert_planilla(trabajador_id, fecha, estado, motivo="", detalle=""):
    user = get_current_user()
    periodo_id = st.session_state.get("periodo_sistema_id")
    existente = execute_query(
        """
        SELECT id FROM planilla
        WHERE trabajador_id = %s AND fecha = %s AND periodo_sistema_id = %s
        LIMIT 1
        """,
        (trabajador_id, fecha, periodo_id),
    )
    if existente:
        execute_insert(
            """
            UPDATE planilla
            SET estado = %s,
                motivo = %s,
                detalle = %s,
                registrado_por = %s
            WHERE id = %s
            """,
            (estado, motivo, detalle, user.get("id"), existente[0]["id"]),
            fetch=False,
        )
    else:
        execute_insert(
            """
            INSERT INTO planilla (trabajador_id, fecha, estado, motivo, detalle, registrado_por, periodo_sistema_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (trabajador_id, fecha, estado, motivo, detalle, user.get("id"), periodo_id),
            fetch=False,
        )
    registrar_accion(
        user.get("id"), user.get("nombre_completo"),
        f"Registró planilla: trabajador_id={trabajador_id} fecha={fecha} estado={estado}",
        "planilla"
    )

def get_dias_periodo(fecha_inicio, fecha_fin):
    """Retorna todos los dias del rango (incluye domingos)."""
    dias = []
    current = fecha_inicio
    while current <= fecha_fin:
        dias.append(current)
        current += timedelta(days=1)
    return dias


def _render_registro_hoy(can_edit, trabajadores, hoy):
    st.subheader(f"Hoy: {format_fecha_es(hoy)}")

    if can_edit:
        if st.button("✅ Marcar 'Presente' a todos para HOY"):
            for t in trabajadores:
                t_id = t["id"]
                activo_hoy = en_rango_planilla(hoy, t.get("fecha_inicio_planilla") or hoy, t.get("fecha_fin_planilla"))
                if activo_hoy:
                    upsert_planilla(t_id, hoy, "presente", "", "")
            st.success("Se marcó asistencia a todos los trabajadores activos hoy.")
            st.rerun()
        st.markdown("---")
    registros_hoy = get_planilla_todos_periodo(hoy, hoy)
    reg_map = {dict(r)["nombre_completo"]: dict(r) for r in registros_hoy}

    presentes = 0
    faltas = 0
    permisos = 0

    for t in trabajadores:
        t = dict(t)
        nombre = t["nombre_completo"]
        activo_hoy = en_rango_planilla(hoy, t.get("fecha_inicio_planilla") or hoy, t.get("fecha_fin_planilla"))
        reg = reg_map.get(nombre, {})
        estado_actual = reg.get("estado", "pendiente")
        motivo_actual = reg.get("motivo", "") or ""
        detalle_actual = reg.get("detalle", "") or ""

        if estado_actual == "presente":
            presentes += 1
        elif estado_actual == "falta":
            faltas += 1
        elif estado_actual == "permiso":
            permisos += 1

        col1, col2, col3 = st.columns([2.5, 2.5, 1.2])
        with col1:
            st.write(f"**{nombre}**")
            st.caption(f"Rango: {t.get('fecha_inicio_planilla') or '-'} -> {t.get('fecha_fin_planilla') or 'activo'}")
        with col2:
            color_map = {
                "presente": "green", "falta": "red", "permiso": "orange", "pendiente": "gray"
            }
            c = color_map.get(estado_actual, "gray")
            st.markdown(
                f"<span style='color:{c};font-weight:bold'>{estado_actual.upper()}</span>",
                unsafe_allow_html=True,
            )
        with col3:
            if not can_edit:
                st.caption("Solo lectura")

        if can_edit and activo_hoy:
            colf1, colf2, colf3 = st.columns([2, 2, 1])
            with colf1:
                opciones = ["presente", "falta", "permiso"]
                idx = opciones.index(estado_actual) if estado_actual in opciones else 0
                nuevo_estado = st.selectbox(
                    f"Estado - {nombre}",
                    opciones,
                    index=idx,
                    key=f"quick_estado_{t['id']}",
                    label_visibility="collapsed",
                )
            with colf2:
                if nuevo_estado in ("falta", "permiso"):
                    motivo_nuevo = st.text_input(
                        f"Motivo - {nombre}",
                        value=motivo_actual,
                        key=f"quick_motivo_{t['id']}",
                        placeholder="Motivo",
                        label_visibility="collapsed",
                    )
                else:
                    motivo_nuevo = ""

                detalle_nuevo = st.text_input(
                    f"Detalle - {nombre}",
                    value=detalle_actual,
                    key=f"quick_det_{t['id']}",
                    placeholder="Detalle opcional",
                    label_visibility="collapsed",
                )
            with colf3:
                if st.button("💾 Guardar", key=f"quick_btn_{t['id']}", type="primary", use_container_width=True):
                    upsert_planilla(t["id"], hoy, nuevo_estado, motivo_nuevo, detalle_nuevo)
                    st.success(f"Guardado: {nombre}")
                    st.rerun()
        elif can_edit and not activo_hoy:
            st.caption("Fuera de rango de planilla")

        st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trabajadores", len(trabajadores))
    c2.metric("🟢 Presentes", presentes)
    c3.metric("🔴 Faltas", faltas)
    c4.metric("🟡 Permisos", permisos)


def render_asistencia_hoy():
    ensure_planilla_worker_columns()

    st.title("🗓️ Asistencia")
    user = get_current_user()
    can_edit = user.get("rol") in ("admin", "pensionista")

    trabajadores = get_trabajadores_activos()
    if not trabajadores:
        st.warning("No hay trabajadores registrados. Ve a Permisos → Trabajadores para agregar.")
        return

    if not st.session_state.get("periodo_sistema_id"):
        st.warning("Selecciona un periodo activo en el sidebar para registrar asistencia de planilla.")
        return

    hoy = date.today()
    _render_registro_hoy(can_edit, trabajadores, hoy)

# ─── UI ─────────────────────────────────────────────────────────────────────

def render():
    ensure_planilla_worker_columns()

    st.title("📋 Planilla de Trabajadores")
    user = get_current_user()
    can_edit = user.get("rol") in ("admin", "pensionista")

    trabajadores = get_trabajadores_activos()
    if not trabajadores:
        st.warning("No hay trabajadores registrados. Ve a Permisos → Trabajadores para agregar.")
        return

    periodo_id = st.session_state.get("periodo_sistema_id")
    if not periodo_id:
        st.warning("Selecciona un periodo activo en el sidebar para gestionar planilla.")
        return

    periodo_rows = execute_query(
        "SELECT fecha_inicio, fecha_fin FROM cuenta_final_periodos WHERE id = %s LIMIT 1",
        (periodo_id,),
    )
    if not periodo_rows:
        st.warning("El periodo activo del sidebar no existe.")
        return
    periodo_activo = dict(periodo_rows[0])
    periodo_inicio = periodo_activo["fecha_inicio"]
    periodo_fin = periodo_activo["fecha_fin"] or date.today()
    st.info(f"Periodo activo: {periodo_inicio} -> {periodo_activo['fecha_fin'] or 'Abierto'}")
    
    with st.expander("⚙️ Configurar rango de planilla por trabajador", expanded=False):
        for t in trabajadores:
            t = dict(t)
            st.write(f"**{t['nombre_completo']}**")
            c1, c2, c3 = st.columns([2, 2, 1.2])
            with c1:
                fi_cfg = st.date_input(
                    "Inicio planilla",
                    value=t.get("fecha_inicio_planilla") or date.today(),
                    key=f"pla_cfg_fi_{t['id']}",
                )
            with c2:
                fin_tipo = st.radio(
                    "Fecha fin",
                    ["Sin fin", "Con fecha fin"],
                    index=1 if t.get("fecha_fin_planilla") else 0,
                    key=f"pla_cfg_fin_tipo_{t['id']}",
                    horizontal=True,
                )
                ff_cfg = None
                if fin_tipo == "Con fecha fin":
                    ff_cfg = st.date_input(
                        "Fin planilla",
                        value=t.get("fecha_fin_planilla") or date.today(),
                        key=f"pla_cfg_ff_{t['id']}",
                    )
            with c3:
                if st.button("💾 Guardar rango", key=f"pla_cfg_save_{t['id']}", type="primary", use_container_width=True):
                    if ff_cfg and ff_cfg < fi_cfg:
                        st.error("La fecha fin no puede ser menor que la fecha inicio.")
                    else:
                        res = save_worker_planilla_range(t["id"], periodo_id, fi_cfg, ff_cfg)
                        if res:
                            st.success(
                                f"Guardado ({periodo_inicio} -> {periodo_activo['fecha_fin'] or 'Abierto'}): {t['nombre_completo']} | Inicio: {fi_cfg} | Fin: {ff_cfg or 'activo'}"
                            )
                        else:
                            st.error("No se pudo guardar el rango para este trabajador.")
                        st.rerun()
            st.markdown("---")

        st.caption("Valores actualmente guardados en base de datos")
        st.dataframe(
            pd.DataFrame([
                {
                    "Trabajador": dict(w)["nombre_completo"],
                    "Inicio planilla": dict(w).get("fecha_inicio_planilla"),
                    "Fin planilla": dict(w).get("fecha_fin_planilla") or "Sin fin (activo)",
                }
                for w in (get_trabajadores_activos() or [])
            ]),
            use_container_width=True,
        )

    hoy = date.today()
    # ── Selector de trabajador ────────────────────────────────────────
    nombres = [dict(t)["nombre_completo"] for t in trabajadores]
    trabajador_sel = st.selectbox("Trabajador", nombres, key="plan_trab")
    trabajador = next(dict(t) for t in trabajadores if dict(t)["nombre_completo"] == trabajador_sel)

    # ── Selector de periodo ───────────────────────────────────────────
    st.subheader("Seleccionar Periodo")
    fecha_inicio = periodo_inicio
    fecha_fin = periodo_fin
    st.caption(f"Rango fijo del periodo activo: {fecha_inicio} -> {fecha_fin}")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la de fin.")
        return

    dias = get_dias_periodo(fecha_inicio, fecha_fin)

    fi_trab = trabajador.get("fecha_inicio_planilla") or fecha_inicio
    ff_trab = trabajador.get("fecha_fin_planilla")
    fecha_inicio_real = max(fecha_inicio, fi_trab)
    fecha_fin_real = min(fecha_fin, ff_trab) if ff_trab else fecha_fin

    if fecha_inicio_real > fecha_fin_real:
        st.warning("El trabajador no tiene planilla activa en ese rango.")
        return

    # ── Cargar registros existentes ───────────────────────────────────
    registros = get_planilla_periodo(trabajador["id"], fecha_inicio_real, fecha_fin_real)
    reg_map = {str(dict(r)["fecha"]): dict(r) for r in registros}

    # ── Tabla de planilla ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"Planilla: {trabajador_sel}")
    st.caption(f"Rango aplicado: {fecha_inicio_real} -> {fecha_fin_real}")

    tabla_data = []
    dias_filtrados = [d for d in dias if fecha_inicio_real <= d <= fecha_fin_real]

    for dia in dias_filtrados:
            dia_str = str(dia)
            reg = reg_map.get(dia_str, {})
            es_domingo = dia.weekday() == 6
            estado = "no_laborable" if es_domingo else reg.get("estado", "pendiente")
            icono = "🔴" if es_domingo else ESTADO_COLORS.get(estado, "⚪")
            futuro = dia > hoy
            tabla_data.append({
                "Fecha": format_fecha_es(dia),
                "Estado": f"{icono} {'No laborable (domingo)' if es_domingo else estado.capitalize()}",
                "Motivo": reg.get("motivo", ""),
                "Detalle": reg.get("detalle", ""),
                "Editable": (not futuro) and (not es_domingo),
                "EsDomingo": es_domingo,
                "_fecha": dia_str,
                "_estado": estado,
            })

    for row in tabla_data:
            col_fecha, col_estado, col_acciones = st.columns([2, 1.5, 3])
            with col_fecha:
                st.write(row["Fecha"])
            with col_estado:
                color_map = {
                    "presente": "green", "falta": "red",
                    "permiso": "orange", "pendiente": "gray", "no_laborable": "red"
                }
                c = color_map.get(row["_estado"], "gray")
                st.markdown(f"<span style='color:{c};font-weight:bold'>{row['Estado']}</span>",
                            unsafe_allow_html=True)
            with col_acciones:
                if row.get("EsDomingo"):
                    st.caption("🚫 Domingo no editable")
                elif not row["Editable"]:
                    st.caption("⏳ Día futuro")
                elif can_edit:
                    with st.expander("Editar", expanded=False):
                        key_prefix = f"plan_{trabajador['id']}_{row['_fecha']}"
                        opciones = ["presente", "falta", "permiso"]
                        idx = opciones.index(row["_estado"]) if row["_estado"] in opciones else 0
                        nuevo_estado = st.selectbox("Estado", opciones, index=idx, key=f"{key_prefix}_est")
                        motivo_val = row["Motivo"]
                        detalle_val = row["Detalle"]
                        if nuevo_estado in ("falta", "permiso"):
                            motivo_val = st.text_input("Motivo", value=motivo_val, key=f"{key_prefix}_mot")
                        detalle_val = st.text_input("Detalle adicional", value=detalle_val, key=f"{key_prefix}_det")
                        if st.button("💾 Guardar", key=f"{key_prefix}_btn"):
                            upsert_planilla(trabajador["id"], row["_fecha"], nuevo_estado, motivo_val, detalle_val)
                            st.success("Guardado")
                            st.rerun()
                else:
                    st.caption("Solo lectura")

    st.markdown("---")
    total_dias = len(dias_filtrados)
    presentes = sum(1 for r in tabla_data if r["_estado"] == "presente")
    faltas = sum(1 for r in tabla_data if r["_estado"] == "falta")
    permisos = sum(1 for r in tabla_data if r["_estado"] == "permiso")
    domingos = sum(1 for r in tabla_data if r.get("EsDomingo"))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total días", total_dias)
    c2.metric("🟢 Presentes", presentes)
    c3.metric("🔴 Faltas", faltas)
    c4.metric("🟡 Permisos", permisos)
    c5.metric("🔴 Domingos", domingos)

    st.markdown("---")
    st.subheader("Exportar Planilla")
    export_todos = st.checkbox("Exportar todos los trabajadores", key="plan_export_todos")

    if export_todos:
        df_export = pd.DataFrame([
            {
                "Fecha": dict(r)["fecha"],
                "Trabajador": dict(r)["nombre_completo"],
                "Estado": dict(r)["estado"],
                "Tipo dia": "No laborable" if dict(r)["fecha"].weekday() == 6 else "Laborable",
                "Motivo": dict(r)["motivo"] or "",
                "Detalle": dict(r)["detalle"] or "",
            }
            for r in get_planilla_todos_periodo(fecha_inicio, fecha_fin)
        ])
    else:
        df_export = pd.DataFrame([
            {
                "Fecha": row["_fecha"],
                "Trabajador": trabajador_sel,
                "Estado": row["_estado"],
                "Tipo dia": "No laborable" if row.get("EsDomingo") else "Laborable",
                "Motivo": row["Motivo"],
                "Detalle": row["Detalle"],
            }
            for row in tabla_data
        ])

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.download_button(
            "📥 Descargar Excel",
            data=df_to_excel(df_export, "Planilla"),
            file_name=f"planilla_{fecha_inicio}_{fecha_fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col_e2:
        st.download_button(
            "📥 Descargar PDF",
            data=df_to_pdf(df_export, "Planilla de Asistencia", f"{fecha_inicio} al {fecha_fin}"),
            file_name=f"planilla_{fecha_inicio}_{fecha_fin}.pdf",
            mime="application/pdf"
        )
