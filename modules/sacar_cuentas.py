import streamlit as st
import pandas as pd
from datetime import date
from utils.db import execute_query, execute_insert
from utils.historial import registrar_accion
from utils.exports import df_to_excel, multiple_sheets_excel, sections_to_pdf
from utils.auth import get_current_user

# ─── Helpers ────────────────────────────────────────────────────────────────

def _normalize_periodo_ids(periodo_ids):
    if periodo_ids is None:
        return []
    if isinstance(periodo_ids, (list, tuple, set)):
        return [int(x) for x in periodo_ids if x is not None]
    return [int(periodo_ids)]


def _fmt_fecha(valor):
    if valor is None or valor == "":
        return ""
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    txt = str(valor)
    return txt[:10] if len(txt) >= 10 else txt


def _txt_corto(valor, max_len=45):
    txt = str(valor or "")
    return txt if len(txt) <= max_len else f"{txt[:max_len-3]}..."

def get_inversiones(socio_id, periodo_ids=None, periodo_fi=None, periodo_ff=None):
    q = "SELECT * FROM inversiones WHERE socio_id = %s"
    p = [socio_id]
    ids = _normalize_periodo_ids(periodo_ids)
    if ids:
        if periodo_fi and periodo_ff:
            q += " AND (periodo_sistema_id = ANY(%s) OR (periodo_sistema_id IS NULL AND fecha BETWEEN %s AND %s))"
            p.extend([ids, periodo_fi, periodo_ff])
        else:
            q += " AND periodo_sistema_id = ANY(%s)"
            p.append(ids)
    q += " ORDER BY fecha DESC"
    return execute_query(q, p)

def add_inversion(socio_id, descripcion, monto, fecha, periodo_id):
    user = get_current_user()
    execute_insert(
        "INSERT INTO inversiones (socio_id,descripcion,monto,fecha,periodo_sistema_id,registrado_por) VALUES (%s,%s,%s,%s,%s,%s)",
        (socio_id, descripcion, monto, fecha, periodo_id, user.get("id"))
    )
    registrar_accion(user.get("id"), user.get("nombre_completo"),
                     f"Registró inversión S/{monto} para socio_id={socio_id}", "sacar_cuentas")

def delete_inversion(inv_id):
    execute_insert("DELETE FROM inversiones WHERE id = %s", (inv_id,))

def get_adelantos(socio_id, periodo_ids=None, periodo_fi=None, periodo_ff=None):
    q = """SELECT a.*, t.nombre_completo as trabajador
           FROM adelantos a
           LEFT JOIN trabajadores t ON a.trabajador_id = t.id
           WHERE a.socio_id = %s"""
    p = [socio_id]
    ids = _normalize_periodo_ids(periodo_ids)
    if ids:
        if periodo_fi and periodo_ff:
            q += " AND (a.periodo_sistema_id = ANY(%s) OR (a.periodo_sistema_id IS NULL AND a.fecha BETWEEN %s AND %s))"
            p.extend([ids, periodo_fi, periodo_ff])
        else:
            q += " AND a.periodo_sistema_id = ANY(%s)"
            p.append(ids)
    q += " ORDER BY a.fecha DESC"
    return execute_query(q, p)

def add_adelanto(socio_id, trabajador_id, descripcion, monto, fecha, periodo_id):
    user = get_current_user()
    execute_insert(
        "INSERT INTO adelantos (socio_id,trabajador_id,descripcion,monto,fecha,periodo_sistema_id,registrado_por) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (socio_id, trabajador_id, descripcion, monto, fecha, periodo_id, user.get("id"))
    )
    registrar_accion(user.get("id"), user.get("nombre_completo"),
                     f"Registró adelanto S/{monto} para socio_id={socio_id}", "sacar_cuentas")

def delete_adelanto(adv_id):
    execute_insert("DELETE FROM adelantos WHERE id = %s", (adv_id,))

def get_recorrido_molienda(socio_id, periodo_ids, periodo_fi=None, periodo_ff=None):
    ids = _normalize_periodo_ids(periodo_ids)
    if not ids:
        return None
    if periodo_fi and periodo_ff:
        rows = execute_query(
            """
            SELECT * FROM molienda
            WHERE socio_id = %s
              AND (periodo_sistema_id = ANY(%s) OR (periodo_sistema_id IS NULL AND fecha BETWEEN %s AND %s))
            ORDER BY id DESC
            LIMIT 1
            """,
            (socio_id, ids, periodo_fi, periodo_ff),
        )
    else:
        rows = execute_query(
            """
            SELECT * FROM molienda
            WHERE socio_id = %s AND periodo_sistema_id = ANY(%s)
            ORDER BY id DESC
            LIMIT 1
            """,
            (socio_id, ids),
        )
    return dict(rows[0]) if rows else None


def save_recorrido_molienda(
    socio_id,
    periodo_id,
    fecha,
    cargadores_monto,
    bolquete_ton,
    bolquete_precio,
    molienda_ton,
    molienda_precio,
):
    user = get_current_user()
    bolquete_total = float(bolquete_ton or 0) * float(bolquete_precio or 0)
    molienda_total = float(molienda_ton or 0) * float(molienda_precio or 0)
    total = float(cargadores_monto or 0) + bolquete_total + molienda_total

    existente = get_recorrido_molienda(socio_id, [periodo_id])
    if existente:
        execute_insert("""
            UPDATE molienda
            SET fecha = %s,
                descripcion = %s,
                monto = %s,
                cargadores_monto = %s,
                bolquete_toneladas = %s,
                bolquete_precio_ton = %s,
                bolquete_total = %s,
                molienda_toneladas = %s,
                molienda_precio_ton = %s,
                molienda_total = %s,
                registrado_por = %s
            WHERE id = %s
        """, (
            fecha,
            "Recorrido molienda",
            total,
            cargadores_monto,
            bolquete_ton,
            bolquete_precio,
            bolquete_total,
            molienda_ton,
            molienda_precio,
            molienda_total,
            user.get("id"),
            existente["id"],
        ))
    else:
        execute_insert("""
            INSERT INTO molienda (
                socio_id, descripcion, monto, fecha, periodo_sistema_id, registrado_por,
                cargadores_monto, bolquete_toneladas, bolquete_precio_ton, bolquete_total,
                molienda_toneladas, molienda_precio_ton, molienda_total
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            socio_id,
            "Recorrido molienda",
            total,
            fecha,
            periodo_id,
            user.get("id"),
            cargadores_monto,
            bolquete_ton,
            bolquete_precio,
            bolquete_total,
            molienda_ton,
            molienda_precio,
            molienda_total,
        ))

    registrar_accion(user.get("id"), user.get("nombre_completo"),
                     f"Guardó recorrido molienda total S/{total} para socio_id={socio_id}", "sacar_cuentas")
    return total

def get_planilla_total(periodo_fi, periodo_ff):
    """Calcula planilla total por trabajador en un periodo."""
    if not periodo_fi or not periodo_ff:
        return []
    rows = execute_query("""
        SELECT t.id, t.nombre_completo, t.sueldo_base,
               COUNT(CASE WHEN p.estado = 'presente' THEN 1 END) as dias_presente,
               COUNT(CASE WHEN p.estado = 'permiso' THEN 1 END) as dias_permiso,
               COUNT(CASE WHEN p.estado = 'falta' THEN 1 END) as dias_falta
        FROM trabajadores t
        LEFT JOIN planilla p ON p.trabajador_id = t.id
            AND p.fecha BETWEEN %s AND %s
        WHERE t.activo = TRUE
        GROUP BY t.id, t.nombre_completo, t.sueldo_base
        ORDER BY t.nombre_completo
    """, (periodo_fi, periodo_ff))
    return rows

def get_adelantos_trabajador(trabajador_id, socio_id, periodo_fi, periodo_ff):
    if not periodo_fi or not periodo_ff:
        return 0.0
    rows = execute_query("""
        SELECT SUM(monto) as total FROM adelantos
        WHERE trabajador_id = %s
          AND socio_id = %s
          AND fecha BETWEEN %s AND %s
    """, (trabajador_id, socio_id, periodo_fi, periodo_ff))
    val = dict(rows[0])["total"] if rows else None
    return float(val) if val else 0.0


def get_adelantos_por_trabajador(socio_id, periodo_fi, periodo_ff):
    if not periodo_fi or not periodo_ff:
        return {}
    rows = execute_query(
        """
        SELECT trabajador_id, COALESCE(SUM(monto), 0) AS total
        FROM adelantos
        WHERE socio_id = %s
          AND fecha BETWEEN %s AND %s
          AND trabajador_id IS NOT NULL
        GROUP BY trabajador_id
        """,
        (socio_id, periodo_fi, periodo_ff),
    )
    out = {}
    for r in (rows or []):
        rr = dict(r)
        out[int(rr["trabajador_id"])] = float(rr.get("total") or 0)
    return out

def get_trabajadores_activos():
    return execute_query("SELECT * FROM trabajadores WHERE activo = TRUE ORDER BY nombre_completo")

# ─── UI de sección ───────────────────────────────────────────────────────────

def render_inversion_section(socio_id, periodo_id, periodo_ids, periodo_fi, periodo_ff, readonly):
    st.subheader("1️⃣ Inversiones")
    inversiones = get_inversiones(socio_id, periodo_ids, periodo_fi, periodo_ff)
    total_inv = sum(float(dict(i)["monto"]) for i in inversiones) if inversiones else 0

    if not readonly:
        with st.expander("➕ Agregar Inversión"):
            with st.form(key=f"inv_form_{socio_id}", clear_on_submit=True):
                desc = st.text_input("Descripción", key=f"inv_desc_{socio_id}")
                monto = st.number_input("Monto (S/)", min_value=0.01, step=0.01, key=f"inv_monto_{socio_id}")
                fecha = st.date_input("Fecha", value=date.today(), key=f"inv_fecha_{socio_id}")
                submitted = st.form_submit_button("💾 Agregar")
            if submitted:
                if desc and monto > 0:
                    add_inversion(socio_id, desc, monto, fecha, periodo_id)
                    st.success("Inversión agregada")
                    st.rerun()
                else:
                    st.warning("Completa todos los campos")

    if inversiones:
        for inv in inversiones:
            i = dict(inv)
            col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 0.8])
            col1.write(i["descripcion"])
            col2.write(i["fecha"].strftime("%d/%m/%Y") if i["fecha"] else "")
            col3.write(f"S/ {float(i['monto']):,.2f}")
            if not readonly:
                if col4.button("🗑️", key=f"del_inv_{i['id']}"):
                    delete_inversion(i["id"])
                    st.rerun()
        st.metric("Total Inversiones", f"S/ {total_inv:,.2f}")
    else:
        st.info("Sin inversiones registradas.")
    return total_inv

def render_adelanto_section(socio_id, periodo_id, periodo_ids, periodo_fi, periodo_ff, readonly):
    st.subheader("2️⃣ Adelantos")
    adelantos = get_adelantos(socio_id, periodo_ids, periodo_fi, periodo_ff)
    total_adv = sum(float(dict(a)["monto"]) for a in adelantos) if adelantos else 0
    trabajadores = get_trabajadores_activos()

    if not readonly:
        with st.expander("➕ Agregar Adelanto"):
            with st.form(key=f"adv_form_{socio_id}", clear_on_submit=True):
                nombres = [dict(t)["nombre_completo"] for t in trabajadores]
                trab_sel = st.selectbox("Trabajador", nombres, key=f"adv_trab_{socio_id}")
                trab_obj = next((dict(t) for t in trabajadores if dict(t)["nombre_completo"] == trab_sel), None)
                desc = st.text_input("Descripción / concepto", key=f"adv_desc_{socio_id}")
                monto = st.number_input("Monto (S/)", min_value=0.01, step=0.01, key=f"adv_monto_{socio_id}")
                fecha = st.date_input("Fecha", value=date.today(), key=f"adv_fecha_{socio_id}")
                submitted = st.form_submit_button("💾 Agregar")
            if submitted:
                if monto > 0 and trab_obj:
                    add_adelanto(socio_id, trab_obj["id"], desc, monto, fecha, periodo_id)
                    st.success("Adelanto registrado")
                    st.rerun()
                else:
                    st.warning("Completa los campos requeridos")

    if adelantos:
        for adv in adelantos:
            a = dict(adv)
            col1, col2, col3, col4, col5 = st.columns([2.5, 1.5, 1.5, 1.5, 0.8])
            col1.write(a.get("trabajador", "-"))
            col2.write(a.get("descripcion", ""))
            col3.write(a["fecha"].strftime("%d/%m/%Y") if a.get("fecha") else "")
            col4.write(f"S/ {float(a['monto']):,.2f}")
            if not readonly:
                if col5.button("🗑️", key=f"del_adv_{a['id']}"):
                    delete_adelanto(a["id"])
                    st.rerun()
        st.metric("Total Adelantos", f"S/ {total_adv:,.2f}")
    else:
        st.info("Sin adelantos registrados.")
    return total_adv

def render_planilla_section(socio_id, periodo_id, periodo_fi, periodo_ff):
    st.subheader("3️⃣ Planilla (Pago a Trabajadores)")
    if not periodo_fi or not periodo_ff:
        st.warning("Selecciona un periodo de carga para ver la planilla.")
        return 0

    trabajadores = get_planilla_total(periodo_fi, periodo_ff)
    adelantos_map = get_adelantos_por_trabajador(socio_id, periodo_fi, periodo_ff)
    total_planilla = 0
    data = []
    for t in trabajadores:
        t = dict(t)
        dias_pagados = (t["dias_presente"] or 0) + (t["dias_permiso"] or 0)
        # Restar adelantos del socio solo dentro del rango real del periodo.
        adelanto = float(adelantos_map.get(int(t["id"]), 0.0))
        sueldo_base = float(t["sueldo_base"] or 0)
        pago_dias = dias_pagados * sueldo_base if sueldo_base > 0 else 0
        neto = pago_dias - adelanto
        total_planilla += max(neto, 0)

        if neto < 0:
            estado_pago = "🔴 Debe al socio"
            a_pagar = 0.0
            deuda = abs(neto)
        else:
            estado_pago = "🟢 A pagar"
            a_pagar = neto
            deuda = 0.0

        data.append({
            "Trabajador": t["nombre_completo"],
            "Días Presentes": t["dias_presente"] or 0,
            "Días Permiso": t["dias_permiso"] or 0,
            "Días Falta": t["dias_falta"] or 0,
            "Días Pagados": dias_pagados,
            "Sueldo/Día (S/)": sueldo_base,
            "Subtotal (S/)": pago_dias,
            "Adelantos (S/)": adelanto,
            "Estado": estado_pago,
            "Neto a Pagar (S/)": round(a_pagar, 2),
            "Deuda del trabajador (S/)": round(deuda, 2),
        })

    if data:
        df = pd.DataFrame(data)
        monto_cols = [
            "Sueldo/Día (S/)",
            "Subtotal (S/)",
            "Adelantos (S/)",
            "Neto a Pagar (S/)",
            "Deuda del trabajador (S/)",
        ]
        for c in monto_cols:
            if c in df.columns:
                df[c] = df[c].map(lambda v: f"{float(v):,.2f}")

        st.dataframe(df, use_container_width=True)
        st.metric("💰 Total Planilla", f"S/ {total_planilla:,.2f}")
    else:
        st.info("No hay datos de planilla para este periodo.")
    return total_planilla

def render_molienda_section(socio_id, periodo_id, periodo_ids, periodo_fi, periodo_ff, readonly):
    st.subheader("4️⃣ Recorrido molienda")
    reg = get_recorrido_molienda(socio_id, periodo_ids, periodo_fi, periodo_ff) or {}

    cargadores_default = float(reg.get("cargadores_monto") or 0)
    bolq_ton_default = float(reg.get("bolquete_toneladas") or 0)
    bolq_precio_default = float(reg.get("bolquete_precio_ton") or 0)
    mol_ton_default = float(reg.get("molienda_toneladas") or 0)
    mol_precio_default = float(reg.get("molienda_precio_ton") or 0)
    fecha_default = reg.get("fecha") or date.today()

    if readonly:
        cargadores = cargadores_default
        bolq_ton = bolq_ton_default
        bolq_precio = bolq_precio_default
        mol_ton = mol_ton_default
        mol_precio = mol_precio_default
        fecha = fecha_default
    else:
        top1, top2 = st.columns([1.2, 1])
        with top1:
            cargadores = st.number_input(
                "Cargadores (monto S/)", min_value=0.0, step=0.01,
                value=cargadores_default, key=f"rm_carg_{socio_id}"
            )
        with top2:
            fecha = st.date_input("Fecha", value=fecha_default, key=f"rm_fecha_{socio_id}")

        st.caption("Volquete y molienda agrupados con sus toneladas")
        grp1, grp2 = st.columns(2)
        with grp1:
            st.markdown("**Volquete**")
            v1, v2 = st.columns(2)
            with v1:
                bolq_ton = st.number_input(
                    "Toneladas", min_value=0.0, step=0.01,
                    value=bolq_ton_default, key=f"rm_bolq_ton_{socio_id}"
                )
            with v2:
                bolq_precio = st.number_input(
                    "Precio x ton (S/)", min_value=0.0, step=0.01,
                    value=bolq_precio_default, key=f"rm_bolq_precio_{socio_id}"
                )
        with grp2:
            st.markdown("**Molienda**")
            m1, m2 = st.columns(2)
            with m1:
                mol_ton = st.number_input(
                    "Toneladas", min_value=0.0, step=0.01,
                    value=mol_ton_default, key=f"rm_mol_ton_{socio_id}"
                )
            with m2:
                mol_precio = st.number_input(
                    "Precio x ton (S/)", min_value=0.0, step=0.01,
                    value=mol_precio_default, key=f"rm_mol_precio_{socio_id}"
                )

    bolq_total = float(bolq_ton) * float(bolq_precio)
    mol_total = float(mol_ton) * float(mol_precio)
    total_recorrido = float(cargadores) + bolq_total + mol_total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cargadores", f"S/ {float(cargadores):,.2f}")
    c2.metric(f"Volquete ({bolq_ton:,.2f} ton)", f"S/ {bolq_total:,.2f}")
    c3.metric(f"Molienda ({mol_ton:,.2f} ton)", f"S/ {mol_total:,.2f}")
    c4.metric("Total recorrido", f"S/ {total_recorrido:,.2f}")

    if not readonly:
        if st.button("💾 Guardar Recorrido molienda", key=f"rm_save_{socio_id}"):
            save_recorrido_molienda(
                socio_id,
                periodo_id,
                fecha,
                cargadores,
                bolq_ton,
                bolq_precio,
                mol_ton,
                mol_precio,
            )
            st.success("Recorrido molienda guardado")
            st.rerun()

    if not reg and readonly:
        st.info("Sin registro de recorrido molienda para este periodo.")

    return total_recorrido

# ─── Render principal ────────────────────────────────────────────────────────

def render(socio: dict, readonly: bool = False):
    nombre = socio["nombre_completo"].split()[0]  # primer nombre
    st.title(f"💼 Sacar Cuentas — {nombre}")

    periodo_activo_id = st.session_state.get("periodo_sistema_id")
    if not periodo_activo_id:
        st.warning("Selecciona un periodo activo en el sidebar para sacar cuentas.")
        return

    periodo_rows = execute_query(
        "SELECT id, fecha_inicio, fecha_fin, observacion FROM cuenta_final_periodos WHERE id = %s LIMIT 1",
        (periodo_activo_id,),
    )
    if not periodo_rows:
        st.warning("El periodo activo no existe.")
        return

    periodo_sel = dict(periodo_rows[0])
    periodo_id = int(periodo_sel["id"])
    periodo_ids = [periodo_id]
    periodo_fi = periodo_sel["fecha_inicio"]
    periodo_ff = periodo_sel["fecha_fin"] or date.today()

    st.info(f"📅 Periodo activo: {periodo_fi} → {periodo_sel['fecha_fin'] or 'Abierto'}")

    st.markdown("---")

    # Secciones de gastos del socio
    total_inv = render_inversion_section(socio["id"], periodo_id, periodo_ids, periodo_fi, periodo_ff, readonly)
    st.markdown("---")
    total_adv = render_adelanto_section(socio["id"], periodo_id, periodo_ids, periodo_fi, periodo_ff, readonly)
    st.markdown("---")
    total_mol = render_molienda_section(socio["id"], periodo_id, periodo_ids, periodo_fi, periodo_ff, readonly)

    # Resumen total
    st.markdown("---")
    total_general = total_inv + total_mol
    st.subheader("📊 Resumen Total (Sacar Cuentas)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Inversiones", f"S/ {total_inv:,.2f}")
    col2.metric("Adelantos (informativo)", f"S/ {total_adv:,.2f}")
    col3.metric("Recorrido molienda", f"S/ {total_mol:,.2f}")
    col4.metric("🔴 TOTAL", f"S/ {total_general:,.2f}")
    st.caption("La planilla (pago a trabajadores) se visualiza y calcula en Cuenta Final.")

    # Exportar
    st.markdown("---")
    if st.button("📥 Preparar exportacion", key=f"export_all_{socio['id']}"):
        inv_items = get_inversiones(socio["id"], periodo_ids, periodo_fi, periodo_ff)
        adv_items = get_adelantos(socio["id"], periodo_ids, periodo_fi, periodo_ff)
        inv_df = pd.DataFrame([dict(i) for i in inv_items]) if inv_items else pd.DataFrame()
        adv_df = pd.DataFrame([dict(a) for a in adv_items]) if adv_items else pd.DataFrame()
        recorrido = get_recorrido_molienda(socio["id"], periodo_ids, periodo_fi, periodo_ff)
        mol_df = pd.DataFrame([recorrido]) if recorrido else pd.DataFrame()

        sheets = {
            "Inversiones": inv_df if not inv_df.empty else pd.DataFrame({"Info": ["Sin datos"]}),
            "Adelantos": adv_df if not adv_df.empty else pd.DataFrame({"Info": ["Sin datos"]}),
            "Recorrido Molienda": mol_df if not mol_df.empty else pd.DataFrame({"Info": ["Sin datos"]}),
        }
        excel_bytes = multiple_sheets_excel(sheets)

        if inv_df.empty:
            inv_pdf_df = pd.DataFrame({"Info": ["Sin datos"]})
        else:
            inv_pdf_df = pd.DataFrame(
                {
                    "Descripcion": inv_df.get("descripcion", pd.Series([], dtype="object")).map(_txt_corto),
                    "Fecha": inv_df.get("fecha", pd.Series([], dtype="object")).map(_fmt_fecha),
                    "Monto (S/)": inv_df.get("monto", pd.Series([], dtype="float")).map(lambda v: f"{float(v or 0):,.2f}"),
                }
            )

        if adv_df.empty:
            adv_pdf_df = pd.DataFrame({"Info": ["Sin datos"]})
        else:
            adv_pdf_df = pd.DataFrame(
                {
                    "Trabajador": adv_df.get("trabajador", pd.Series([], dtype="object")).map(_txt_corto),
                    "Concepto": adv_df.get("descripcion", pd.Series([], dtype="object")).map(_txt_corto),
                    "Fecha": adv_df.get("fecha", pd.Series([], dtype="object")).map(_fmt_fecha),
                    "Monto (S/)": adv_df.get("monto", pd.Series([], dtype="float")).map(lambda v: f"{float(v or 0):,.2f}"),
                }
            )

        if recorrido:
            mol_pdf_df = pd.DataFrame(
                [
                    {
                        "Fecha": _fmt_fecha(recorrido.get("fecha", "")),
                        "Cargadores (S/)": f"{float(recorrido.get('cargadores_monto') or 0):,.2f}",
                        "Volquete (S/)": f"{float(recorrido.get('bolquete_total') or 0):,.2f}",
                        "Molienda (S/)": f"{float(recorrido.get('molienda_total') or 0):,.2f}",
                        "Total (S/)": f"{float(recorrido.get('monto') or 0):,.2f}",
                    }
                ]
            )
        else:
            mol_pdf_df = pd.DataFrame({"Info": ["Sin datos"]})

        resumen_pdf_df = pd.DataFrame(
            [
                {"Concepto": "Inversiones", "Monto (S/)": f"{total_inv:,.2f}"},
                {"Concepto": "Adelantos (informativo, ya descontado en planilla)", "Monto (S/)": f"{total_adv:,.2f}"},
                {"Concepto": "Recorrido molienda", "Monto (S/)": f"{total_mol:,.2f}"},
                {"Concepto": "TOTAL", "Monto (S/)": f"{total_general:,.2f}"},
            ]
        )

        pdf_sections = [
            ("1. Inversiones", inv_pdf_df),
            ("2. Adelantos", adv_pdf_df),
            ("3. Recorrido molienda", mol_pdf_df),
            ("4. Resumen", resumen_pdf_df),
        ]

        pdf_bytes = sections_to_pdf(
            pdf_sections,
            "Sacar Cuentas",
            f"Socio: {socio['nombre_completo']} | Periodo: {_fmt_fecha(periodo_fi)} al {_fmt_fecha(periodo_ff)}",
        )

        col_ex, col_pdf = st.columns(2)
        with col_ex:
            st.download_button(
                "⬇️ Descargar Excel Completo",
                data=excel_bytes,
                file_name=f"sacar_cuentas_{nombre}_{periodo_ff}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_pdf:
            st.download_button(
                "⬇️ Descargar PDF Completo",
                data=pdf_bytes,
                file_name=f"sacar_cuentas_{nombre}_{periodo_ff}.pdf",
                mime="application/pdf"
            )
