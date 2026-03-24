from datetime import date

import pandas as pd
import streamlit as st

from utils.db import execute_query
from utils.exports import df_to_excel, df_to_pdf
from utils.auth import get_current_user


def _get_workers():
    return execute_query(
        """
        SELECT
            t.id,
            t.nombre_completo,
            t.sueldo_base,
                        COALESCE(cfg.fecha_inicio, cp.fecha_inicio, t.fecha_inicio_planilla, CURRENT_DATE) AS fecha_inicio_planilla
        FROM trabajadores t
                LEFT JOIN cuenta_final_periodos cp
                    ON cp.id = %s
        LEFT JOIN trabajador_planilla_periodo_config cfg
          ON cfg.trabajador_id = t.id
         AND cfg.periodo_id = %s
        WHERE t.activo = TRUE
        ORDER BY t.nombre_completo
        """
        ,
                (st.session_state.get("periodo_sistema_id"), st.session_state.get("periodo_sistema_id")),
    )


def _count_paid_days(worker_id, fi, ff):
    rows = execute_query(
        """
        SELECT COUNT(*) AS cnt
        FROM planilla
        WHERE trabajador_id = %s
          AND fecha BETWEEN %s AND %s
                    AND periodo_sistema_id = %s
          AND estado IN ('presente', 'permiso')
        """,
                (worker_id, fi, ff, st.session_state.get("periodo_sistema_id")),
    )
    return int(rows[0]["cnt"]) if rows else 0


def _sum_adelantos(worker_id, fi, ff):
    rows = execute_query(
        """
        SELECT COALESCE(SUM(monto), 0) AS total
        FROM adelantos
        WHERE trabajador_id = %s
          AND fecha BETWEEN %s AND %s
                    AND (
                                periodo_sistema_id = %s
                                OR (periodo_sistema_id IS NULL AND fecha BETWEEN %s AND %s)
                            )
        """,
                (
                        worker_id,
                        fi,
                        ff,
                        st.session_state.get("periodo_sistema_id"),
                        fi,
                        ff,
                ),
    )
    return float(rows[0]["total"]) if rows else 0.0


def render():
    st.title("💵 Sueldo de Trabajadores")

    user = get_current_user()
    if user.get("rol") == "pensionista":
        st.error("Acceso no autorizado")
        st.stop()

    periodo_id = st.session_state.get("periodo_sistema_id")
    if not periodo_id:
        st.warning("Selecciona un periodo activo en el sidebar para ver sueldos.")
        return

    periodo_rows = execute_query(
        "SELECT fecha_inicio, fecha_fin FROM cuenta_final_periodos WHERE id = %s LIMIT 1",
        (periodo_id,),
    )
    if not periodo_rows:
        st.warning("El periodo activo del sidebar no existe.")
        return
    periodo = dict(periodo_rows[0])
    fi = periodo["fecha_inicio"]
    ff = periodo["fecha_fin"] or date.today()
    st.info(f"Periodo activo: {fi} -> {periodo['fecha_fin'] or 'Abierto'}")

    workers = _get_workers() or []
    rows = []
    total_neto_a_pagar = 0.0
    total_deuda = 0.0

    for w in workers:
        inicio_conf = w.get("fecha_inicio_planilla") or fi
        inicio_calc = max(fi, inicio_conf) if fi else inicio_conf

        if inicio_calc > ff:
            dias_pagados = 0
            subtotal = 0.0
            adelantos = 0.0
            neto = 0.0
        else:
            dias_pagados = _count_paid_days(w["id"], inicio_calc, ff)
            sueldo_dia = float(w.get("sueldo_base") or 0)
            subtotal = dias_pagados * sueldo_dia
            adelantos = _sum_adelantos(w["id"], inicio_calc, ff)
            neto = subtotal - adelantos

        if neto < 0:
            estado = "🔴 Debe dinero"
            neto_a_pagar = 0.0
            deuda = abs(neto)
        else:
            estado = "🟢 Cobrar"
            neto_a_pagar = neto
            deuda = 0.0

        total_neto_a_pagar += neto_a_pagar
        total_deuda += deuda
        rows.append(
            {
                "Trabajador": w["nombre_completo"],
                "Inicio configurado": inicio_conf,
                "Inicio calculo": inicio_calc,
                "Fin calculo": ff,
                "Dias pagados": dias_pagados,
                "Sueldo diario": float(w.get("sueldo_base") or 0),
                "Subtotal": round(subtotal, 2),
                "Adelantos": round(adelantos, 2),
                "Estado": estado,
                "Neto a pagar": round(neto_a_pagar, 2),
                "Deuda trabajador": round(deuda, 2),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric("Total sueldos netos a pagar", f"S/ {total_neto_a_pagar:,.2f}")
    c2.metric("Total deuda de trabajadores", f"S/ {total_deuda:,.2f}")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📥 Excel",
            df_to_excel(df, "Sueldos"),
            file_name=f"sueldos_{fi}_{ff}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with c2:
        st.download_button(
            "📥 PDF",
            df_to_pdf(df, "Sueldos de Trabajadores", f"{fi} al {ff}"),
            file_name=f"sueldos_{fi}_{ff}.pdf",
            mime="application/pdf",
        )
