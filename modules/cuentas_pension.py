from datetime import date

import pandas as pd
import streamlit as st

from utils.db import execute_insert, execute_query
from utils.exports import df_to_excel, df_to_pdf
from utils.historial import registrar_accion
from utils.auth import get_current_user

DEFAULT_MONTO_DIA = 28.0


def _ensure_pension_config_table():
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

def _ensure_worker_period_config_tables():
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


def _get_monto_dia():
    _ensure_pension_config_table()
    rows = execute_query("SELECT monto_dia FROM pension_config WHERE id = 1")
    if rows:
        return float(rows[0]["monto_dia"])

    execute_insert(
        "INSERT INTO pension_config (id, monto_dia) VALUES (1, %s) ON CONFLICT (id) DO NOTHING",
        (DEFAULT_MONTO_DIA,),
        fetch=False,
    )
    return DEFAULT_MONTO_DIA


def _save_monto_dia(monto_dia):
    _ensure_pension_config_table()
    user = get_current_user()
    execute_insert(
        """
        INSERT INTO pension_config (id, monto_dia, updated_by)
        VALUES (1, %s, %s)
        ON CONFLICT (id)
        DO UPDATE SET
            monto_dia = EXCLUDED.monto_dia,
            updated_at = NOW(),
            updated_by = EXCLUDED.updated_by
        """,
        (monto_dia, user.get("id")),
        fetch=False,
    )
    registrar_accion(
        user.get("id"),
        user.get("nombre_completo"),
        f"Actualizo monto diario pension a S/{monto_dia}",
        "cuentas_pension",
    )


def _get_workers_with_ranges():
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
        ORDER BY nombre_completo
        """,
        (periodo_id, periodo_id),
    )


def _count_pension_days(worker_id, fi, ff):
    rows = execute_query(
        """
        SELECT COUNT(*) AS cnt
        FROM pension
        WHERE trabajador_id = %s
          AND fecha BETWEEN %s AND %s
                    AND periodo_sistema_id = %s
          AND estado = 'si'
        """,
                (worker_id, fi, ff, st.session_state.get("periodo_sistema_id")),
    )
    return int(rows[0]["cnt"]) if rows else 0


def _calc_rows(monto_dia):
    periodo_id = st.session_state.get("periodo_sistema_id")
    periodo_rows = execute_query(
        "SELECT fecha_inicio, fecha_fin FROM cuenta_final_periodos WHERE id = %s LIMIT 1",
        (periodo_id,),
    )
    if not periodo_rows:
        return [], 0.0
    periodo = dict(periodo_rows[0])
    fi_periodo = periodo["fecha_inicio"]
    ff_periodo = periodo["fecha_fin"] or date.today()

    workers = _get_workers_with_ranges() or []

    data = []
    total_general = 0.0

    for w in workers:
        fi_cfg = w.get("fecha_inicio_pension") or fi_periodo
        ff_cfg = w.get("fecha_fin_pension")

        fi = max(fi_periodo, fi_cfg)
        ff = ff_periodo if not ff_cfg else min(ff_periodo, ff_cfg)

        if fi > ff:
            dias_si = 0
            total = 0.0
            estado = "Fuera de rango"
        else:
            dias_si = _count_pension_days(w["id"], fi, ff)
            total = float(dias_si) * float(monto_dia)
            estado = "Calculado"

        total_general += total
        data.append(
            {
                "Trabajador": w["nombre_completo"],
                "Inicio pension": fi,
                "Fin pension": ff,
                "Dias con pension (SI)": dias_si,
                "Monto por dia (S/)": round(float(monto_dia), 2),
                "Total pension (S/)": round(total, 2),
                "Estado": estado,
            }
        )

    return data, total_general


def render():
    st.title("🍽️ Cuentas - Pensión")
    st.caption("Calculo por trabajador segun rango configurado en pension y monto diario editable.")
    _ensure_worker_period_config_tables()

    if not st.session_state.get("periodo_sistema_id"):
        st.warning("Selecciona un periodo activo en el sidebar para calcular Cuentas - Pensión.")
        return

    p_rows = execute_query(
        "SELECT fecha_inicio, fecha_fin FROM cuenta_final_periodos WHERE id = %s LIMIT 1",
        (st.session_state.get("periodo_sistema_id"),),
    )
    if p_rows:
        p = dict(p_rows[0])
        st.caption(f"Periodo activo: {p['fecha_inicio']} -> {p['fecha_fin'] or 'Abierto'}")

    monto_actual = _get_monto_dia()

    c1, c2 = st.columns([2, 1])
    with c1:
        monto_dia = st.number_input(
            "Monto por dia (S/)",
            min_value=0.0,
            step=0.5,
            value=float(monto_actual),
            key="cp_monto_dia",
        )
    with c2:
        if st.button("💾 Guardar monto", key="cp_save_monto", use_container_width=True):
            _save_monto_dia(float(monto_dia))
            st.success("Monto diario actualizado")
            st.rerun()

    data, total_general = _calc_rows(float(monto_dia))

    if not data:
        st.info("No hay trabajadores activos para calcular pensiones.")
        return

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    st.metric("Total general pension", f"S/ {total_general:,.2f}")

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.download_button(
            "📥 Excel",
            df_to_excel(df, "Cuentas Pension"),
            file_name=f"cuentas_pension_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_e2:
        st.download_button(
            "📥 PDF",
            df_to_pdf(df, "Cuentas - Pension", f"Actualizado al {date.today()}"),
            file_name=f"cuentas_pension_{date.today()}.pdf",
            mime="application/pdf",
        )
