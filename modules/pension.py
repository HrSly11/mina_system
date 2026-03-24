from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.auth import get_current_user
from utils.db import execute_insert, execute_query
from utils.exports import df_to_excel, df_to_pdf
from utils.historial import registrar_accion

COSTO_DIA = 28.0
DIAS_ES = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


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
        d = min(fecha_base.day, 28)
        return fecha_base.replace(year=y, month=m, day=d)


def get_monto_dia_pension_config():
    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS pension_config (
            id INTEGER PRIMARY KEY,
            monto_dia NUMERIC(10,2) NOT NULL DEFAULT 28.00,
            updated_at TIMESTAMP DEFAULT NOW(),
            updated_by INTEGER REFERENCES usuarios(id)
        )
        """,
        fetch=False,
    )
    rows = execute_query("SELECT monto_dia FROM pension_config WHERE id = 1")
    if rows:
        return float(rows[0]["monto_dia"])
    execute_insert(
        "INSERT INTO pension_config (id, monto_dia) VALUES (1, %s) ON CONFLICT (id) DO NOTHING",
        (COSTO_DIA,),
        fetch=False,
    )
    return COSTO_DIA


def get_trabajadores_pension():
    periodo_id = st.session_state.get("periodo_sistema_id")
    return execute_query(
        """
        SELECT
            t.id,
            t.nombre_completo,
                        COALESCE(cfg.fecha_inicio, cp.fecha_inicio, t.fecha_inicio_pension, CURRENT_DATE) AS fecha_inicio_pension,
                        COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_pension) AS fecha_fin_pension
        FROM trabajadores t
                LEFT JOIN cuenta_final_periodos cp
                    ON cp.id = %s
        LEFT JOIN trabajador_pension_periodo_config cfg
          ON cfg.trabajador_id = t.id
         AND cfg.periodo_id = %s
        WHERE t.activo = TRUE
        ORDER BY t.nombre_completo
        """,
                (periodo_id, periodo_id),
    )


def pension_has_trabajador_column():
    rows = execute_query(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pension'
          AND column_name = 'trabajador_id'
        LIMIT 1
        """
    )
    return bool(rows)


def ensure_pension_worker_columns():
    if st.session_state.get("_schema_pension_ready"):
        return

    # Compatibilidad automática para bases antiguas.
    execute_insert("ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_inicio_pension DATE DEFAULT CURRENT_DATE")
    execute_insert("ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_fin_pension DATE")
    execute_insert("ALTER TABLE pension ADD COLUMN IF NOT EXISTS trabajador_id INTEGER REFERENCES trabajadores(id) ON DELETE CASCADE")
    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS trabajador_pension_periodo_config (
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
    st.session_state["_schema_pension_ready"] = True


def _en_rango_trabajador(fecha_eval, fi_trab, ff_trab):
    if fecha_eval < fi_trab:
        return False
    if ff_trab and fecha_eval > ff_trab:
        return False
    return True


def save_worker_pension_range(trabajador_id, periodo_id, fecha_inicio, fecha_fin):
    return execute_insert(
        """
        INSERT INTO trabajador_pension_periodo_config (trabajador_id, periodo_id, fecha_inicio, fecha_fin, updated_at)
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


def _estado_badge(estado):
    color = {"si": "#147d2f", "no": "#b42318", "pendiente": "#667085"}
    label = {"si": "SI", "no": "NO", "pendiente": "PENDIENTE"}
    return (
        f"<span style='display:inline-block;padding:6px 12px;border-radius:999px;"
        f"background:{color.get(estado, '#667085')};color:white;font-weight:700;font-size:1.05rem;'>"
        f"{label.get(estado, 'PENDIENTE')}</span>"
    )


def get_pension_worker_periodo(trabajador_id, fecha_inicio, fecha_fin):
    if not pension_has_trabajador_column():
        # Compatibilidad con esquema antiguo: pensión global por fecha.
        return execute_query(
            """
            SELECT *, NULL::integer AS trabajador_id FROM pension
                        WHERE fecha BETWEEN %s AND %s
                            AND periodo_sistema_id = %s
            ORDER BY fecha
            """,
                        (fecha_inicio, fecha_fin, st.session_state.get("periodo_sistema_id")),
        )

    return execute_query(
        """
        SELECT * FROM pension
        WHERE trabajador_id = %s
          AND fecha BETWEEN %s AND %s
                    AND periodo_sistema_id = %s
        ORDER BY fecha
        """,
                (trabajador_id, fecha_inicio, fecha_fin, st.session_state.get("periodo_sistema_id")),
    )


def upsert_pension(trabajador_id, fecha, estado, detalle=""):
    user = get_current_user()
    periodo_id = st.session_state.get("periodo_sistema_id")
    if pension_has_trabajador_column():
        # Evita depender de constraint único para ON CONFLICT.
        existente = execute_query(
            "SELECT id FROM pension WHERE trabajador_id = %s AND fecha = %s AND periodo_sistema_id = %s LIMIT 1",
            (trabajador_id, fecha, periodo_id),
        )
        if existente:
            execute_insert(
                """
                UPDATE pension
                SET estado = %s,
                    detalle = %s,
                    registrado_por = %s
                WHERE trabajador_id = %s AND fecha = %s AND periodo_sistema_id = %s
                """,
                (estado, detalle, user.get("id"), trabajador_id, fecha, periodo_id),
            )
        else:
            execute_insert(
                """
                INSERT INTO pension (trabajador_id, fecha, estado, detalle, registrado_por, periodo_sistema_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (trabajador_id, fecha, estado, detalle, user.get("id"), periodo_id),
            )
    else:
        # Esquema antiguo: un único registro por fecha.
        existente = execute_query(
            "SELECT id FROM pension WHERE fecha = %s AND periodo_sistema_id = %s LIMIT 1",
            (fecha, periodo_id),
        )
        if existente:
            execute_insert(
                """
                UPDATE pension
                SET estado = %s,
                    detalle = %s,
                    registrado_por = %s
                WHERE fecha = %s AND periodo_sistema_id = %s
                """,
                (estado, detalle, user.get("id"), fecha, periodo_id),
            )
        else:
            execute_insert(
                """
                INSERT INTO pension (fecha, estado, detalle, registrado_por, periodo_sistema_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (fecha, estado, detalle, user.get("id"), periodo_id),
            )

    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Registró pensión trabajador_id={trabajador_id} fecha={fecha} estado={estado}",
        "pension",
    )


def _render_rapido_hoy(can_edit):
    hoy = date.today()
    st.subheader(f"Registro de hoy: {format_fecha_es(hoy)}")

    trabajadores = get_trabajadores_pension() or []
    if not trabajadores:
        st.info("No hay trabajadores activos.")
        return
        
    if can_edit:
        if st.button("✅ Marcar 'Sí' a todos para HOY"):
            for t in trabajadores:
                activo_hoy = _en_rango_trabajador(hoy, t["fecha_inicio_pension"], t.get("fecha_fin_pension"))
                if activo_hoy:
                    upsert_pension(t["id"], hoy, "si", "")
            st.success("Se marcó asistencia a todos los trabajadores en pensión hoy.")
            st.rerun()
        st.markdown("---")

    registros_hoy = execute_query(
        "SELECT * FROM pension WHERE fecha = %s AND periodo_sistema_id = %s",
        (hoy, st.session_state.get("periodo_sistema_id")),
    )

    if pension_has_trabajador_column():
        map_hoy = {r["trabajador_id"]: r for r in (registros_hoy or []) if r.get("trabajador_id")}
    else:
        map_hoy = {}

    for t in trabajadores:
        activo_hoy = _en_rango_trabajador(hoy, t["fecha_inicio_pension"], t.get("fecha_fin_pension"))
        row = map_hoy.get(t["id"], {})
        estado_actual = row.get("estado", "pendiente")
        detalle_actual = row.get("detalle", "") if row else ""

        c1, c2, c3 = st.columns([2.5, 1.5, 2.5])
        with c1:
            st.write(f"**{t['nombre_completo']}**")
            st.caption(f"Rango: {t['fecha_inicio_pension']} -> {t.get('fecha_fin_pension') or 'activo'}")
        with c2:
            st.markdown(_estado_badge(estado_actual), unsafe_allow_html=True)
        with c3:
            if not activo_hoy:
                st.caption("Fuera de rango de pensión")
                continue
            if not can_edit:
                st.caption("Solo lectura")
                continue

            opts = ["si", "no"]
            idx = opts.index(estado_actual) if estado_actual in opts else 0
            nuevo = st.selectbox(
                f"Estado {t['id']}",
                opts,
                index=idx,
                key=f"penh_est_{t['id']}",
                label_visibility="collapsed",
            )
            det = st.text_input(
                f"Detalle {t['id']}",
                value=detalle_actual or "",
                key=f"penh_det_{t['id']}",
                placeholder="Detalle opcional",
                label_visibility="collapsed",
            )
            if st.button("💾 Guardar", key=f"penh_btn_{t['id']}", type="primary", use_container_width=True):
                upsert_pension(t["id"], hoy, nuevo, det)
                st.success(f"Guardado: {t['nombre_completo']}")
                st.rerun()

        st.markdown("---")


def render_asistencia_hoy():
    ensure_pension_worker_columns()

    st.title("🍽️ Asistencia - Pensión")
    user = get_current_user()
    can_edit = user.get("rol") in ("admin", "pensionista")
    if not st.session_state.get("periodo_sistema_id"):
        st.warning("Selecciona un periodo activo en el sidebar para registrar pensión.")
        return
    _render_rapido_hoy(can_edit)


def _render_por_trabajador(can_edit):
    hoy = date.today()
    st.subheader("Pensión por trabajador y periodo")

    trabajadores = get_trabajadores_pension() or []
    if not trabajadores:
        st.info("No hay trabajadores activos.")
        return

    nombres = [t["nombre_completo"] for t in trabajadores]
    nombre_sel = st.selectbox("Trabajador", nombres, key="pen_trab_sel")
    trab = next(t for t in trabajadores if t["nombre_completo"] == nombre_sel)

    fi_cfg = trab["fecha_inicio_pension"]
    ff_cfg = trab.get("fecha_fin_pension")
    periodo_id = st.session_state.get("periodo_sistema_id")
    periodo_rows = execute_query(
        "SELECT fecha_inicio, fecha_fin FROM cuenta_final_periodos WHERE id = %s LIMIT 1",
        (periodo_id,),
    )
    if not periodo_rows:
        st.warning("El periodo activo del sidebar no existe.")
        return
    periodo = dict(periodo_rows[0])
    ff_sugerido = periodo.get("fecha_fin") or date.today()
    fi_cfg = periodo.get("fecha_inicio")

    fi = fi_cfg
    ff = ff_sugerido
    st.caption(f"Rango fijo del periodo activo: {fi} -> {ff}")

    if fi > ff:
        st.error("Rango inválido")
        return

    registros = get_pension_worker_periodo(trab["id"], fi, ff)
    reg_map = {str(r["fecha"]): r for r in (registros or [])}

    dias = []
    cur = fi
    while cur <= ff:
        dias.append(cur)
        cur += timedelta(days=1)

    rows_ui = []
    for d in dias:
        key = str(d)
        reg = reg_map.get(key, {})
        estado = reg.get("estado", "pendiente")
        detalle = reg.get("detalle", "") if reg else ""
        editable = d <= hoy and _en_rango_trabajador(d, trab["fecha_inicio_pension"], trab.get("fecha_fin_pension"))
        rows_ui.append({
            "fecha": d,
            "estado": estado,
            "detalle": detalle,
            "editable": editable,
        })

    for r in rows_ui:
        c1, c2, c3 = st.columns([2, 1, 3])
        with c1:
            st.write(format_fecha_es(r["fecha"]))
        with c2:
            st.markdown(_estado_badge(r["estado"]), unsafe_allow_html=True)
        with c3:
            if not r["editable"]:
                st.caption("No editable")
            elif can_edit:
                k = f"pent_{trab['id']}_{r['fecha']}"
                opts = ["si", "no"]
                idx = opts.index(r["estado"]) if r["estado"] in opts else 0
                nuevo = st.selectbox("Estado", opts, index=idx, key=f"{k}_est")
                det = st.text_input("Detalle", value=r["detalle"], key=f"{k}_det")
                if st.button("💾 Guardar", key=f"{k}_btn"):
                    upsert_pension(trab["id"], r["fecha"], nuevo, det)
                    st.success("Guardado")
                    st.rerun()
            else:
                st.caption("Solo lectura")

    st.markdown("---")
    dias_si = sum(1 for r in rows_ui if r["estado"] == "si")
    dias_no = sum(1 for r in rows_ui if r["estado"] == "no")
    monto_dia_cfg = get_monto_dia_pension_config()
    total = dias_si * monto_dia_cfg
    m1, m2, m3 = st.columns(3)
    m1.metric("Dias si", dias_si)
    m2.metric("Dias no", dias_no)
    m3.metric("Total", f"S/ {total:,.2f}")

    df = pd.DataFrame(
        [
            {
                "Trabajador": trab["nombre_completo"],
                "Fecha": str(r["fecha"]),
                "Estado": r["estado"],
                "Detalle": r["detalle"],
            }
            for r in rows_ui
        ]
    )
    e1, e2 = st.columns(2)
    with e1:
        st.download_button(
            "📥 Excel",
            df_to_excel(df, "Pension"),
            file_name=f"pension_{trab['nombre_completo']}_{fi}_{ff}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with e2:
        st.download_button(
            "📥 PDF",
            df_to_pdf(df, "Pension por trabajador", f"{fi} al {ff}"),
            file_name=f"pension_{trab['nombre_completo']}_{fi}_{ff}.pdf",
            mime="application/pdf",
        )


def render():
    ensure_pension_worker_columns()

    st.title("🍽️ Pensión")
    user = get_current_user()
    can_edit = user.get("rol") in ("admin", "pensionista")

    if not st.session_state.get("periodo_sistema_id"):
        st.warning("Selecciona un periodo activo en el sidebar para gestionar pensión.")
        return

    with st.expander("⚙️ Configurar rango de pensión por trabajador", expanded=False):
        trabajadores_cfg = get_trabajadores_pension() or []
        if not trabajadores_cfg:
            st.info("No hay trabajadores activos.")
        else:
            for t in trabajadores_cfg:
                st.write(f"**{t['nombre_completo']}**")
                c1, c2, c3 = st.columns([2, 2, 1.2])
                with c1:
                    fi_cfg = st.date_input(
                        "Inicio pensión",
                        value=t.get("fecha_inicio_pension") or date.today(),
                        key=f"pen_cfg_fi_{t['id']}",
                    )
                with c2:
                    fin_tipo = st.radio(
                        "Fecha fin",
                        ["Sin fin", "Con fecha fin"],
                        index=1 if t.get("fecha_fin_pension") else 0,
                        key=f"pen_cfg_fin_tipo_{t['id']}",
                        horizontal=True,
                    )
                    ff_cfg = None
                    if fin_tipo == "Con fecha fin":
                        ff_cfg = st.date_input(
                            "Fin pensión",
                            value=t.get("fecha_fin_pension") or date.today(),
                            key=f"pen_cfg_ff_{t['id']}",
                        )
                with c3:
                    if st.button("💾 Guardar rango", key=f"pen_cfg_save_{t['id']}", type="primary", use_container_width=True):
                        if ff_cfg and ff_cfg < fi_cfg:
                            st.error("La fecha fin no puede ser menor que la fecha inicio.")
                        else:
                            res = save_worker_pension_range(t["id"], st.session_state.get("periodo_sistema_id"), fi_cfg, ff_cfg)
                            if res:
                                st.success(
                                    f"Guardado: {t['nombre_completo']} | Inicio: {fi_cfg} | Fin: {ff_cfg or 'activo'}"
                                )
                            else:
                                st.error("No se pudo guardar el rango para este trabajador.")
                            st.rerun()
                st.markdown("---")

            st.caption("Valores actualmente guardados en base de datos")
            st.dataframe(
                pd.DataFrame([
                    {
                        "Trabajador": w["nombre_completo"],
                        "Inicio pension": w.get("fecha_inicio_pension"),
                        "Fin pension": w.get("fecha_fin_pension") or "Sin fin (activo)",
                    }
                    for w in (get_trabajadores_pension() or [])
                ]),
                use_container_width=True,
            )

    st.info("Las cuentas de pension y monto por dia ahora se gestionan solo en el modulo Cuentas - Pension del sidebar.")

    _render_por_trabajador(can_edit)
