import pandas as pd
import streamlit as st
from datetime import date

from utils.auth import get_current_user
from utils.db import execute_insert, execute_query
from utils.exports import df_to_excel, df_to_pdf, sections_to_pdf
from utils.historial import registrar_accion

DEFAULT_MONTO_DIA_PENSION = 28.0


def _ensure_cuenta_final_schema():
    if st.session_state.get("_schema_cuenta_final_ready"):
        return

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_periodos (
            id SERIAL PRIMARY KEY,
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE NOT NULL,
            observacion TEXT,
            registrado_por INTEGER REFERENCES usuarios(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        fetch=False,
    )

    execute_insert(
        "ALTER TABLE cuenta_final ADD COLUMN IF NOT EXISTS periodo_cuenta_id INTEGER REFERENCES cuenta_final_periodos(id)",
        fetch=False,
    )
    execute_insert(
        "CREATE INDEX IF NOT EXISTS idx_cuenta_final_periodo_cuenta_id ON cuenta_final(periodo_cuenta_id)",
        fetch=False,
    )

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

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_luz_asignaciones (
            id SERIAL PRIMARY KEY,
            cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
            luz_id INTEGER NOT NULL REFERENCES luz_mensual(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            assigned_by INTEGER REFERENCES usuarios(id),
            UNIQUE(luz_id)
        )
        """,
        fetch=False,
    )
    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS periodo_luz_asignaciones (
            id SERIAL PRIMARY KEY,
            periodo_id INTEGER NOT NULL REFERENCES cuenta_final_periodos(id) ON DELETE CASCADE,
            luz_id INTEGER NOT NULL REFERENCES luz_mensual(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            assigned_by INTEGER REFERENCES usuarios(id),
            UNIQUE(luz_id)
        )
        """,
        fetch=False,
    )

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_planilla_asignaciones (
            id SERIAL PRIMARY KEY,
            cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
            planilla_id INTEGER NOT NULL REFERENCES planilla(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            assigned_by INTEGER REFERENCES usuarios(id),
            UNIQUE(planilla_id)
        )
        """,
        fetch=False,
    )

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_adelanto_asignaciones (
            id SERIAL PRIMARY KEY,
            cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
            adelanto_id INTEGER NOT NULL REFERENCES adelantos(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            assigned_by INTEGER REFERENCES usuarios(id),
            UNIQUE(adelanto_id)
        )
        """,
        fetch=False,
    )

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_pension_asignaciones (
            id SERIAL PRIMARY KEY,
            cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
            pension_id INTEGER NOT NULL REFERENCES pension(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            assigned_by INTEGER REFERENCES usuarios(id),
            UNIQUE(pension_id)
        )
        """,
        fetch=False,
    )

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_inversion_asignaciones (
            id SERIAL PRIMARY KEY,
            cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
            inversion_id INTEGER NOT NULL REFERENCES inversiones(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            assigned_by INTEGER REFERENCES usuarios(id),
            UNIQUE(inversion_id)
        )
        """,
        fetch=False,
    )

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_molienda_asignaciones (
            id SERIAL PRIMARY KEY,
            cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
            molienda_id INTEGER NOT NULL REFERENCES molienda(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            assigned_by INTEGER REFERENCES usuarios(id),
            UNIQUE(molienda_id)
        )
        """,
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE planilla ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id)",
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE pension ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id)",
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE inversiones ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id)",
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE adelantos ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id)",
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE molienda ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id)",
        fetch=False,
    )
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
    st.session_state["_schema_cuenta_final_ready"] = True


def get_default_periodo_trabajadores():
    rows = execute_query(
        """
        SELECT
            MIN(fecha_inicio_planilla) AS fi,
            MAX(COALESCE(fecha_fin_planilla, CURRENT_DATE)) AS ff
        FROM trabajadores
        WHERE activo = TRUE
        """
    )
    if rows:
        rr = dict(rows[0])
        return rr.get("fi") or date.today(), rr.get("ff") or date.today()
    return date.today(), date.today()


def get_periodos_cuenta_final():
    rows = execute_query(
        """
        SELECT id, fecha_inicio, fecha_fin, observacion
        FROM cuenta_final_periodos
        ORDER BY id DESC
        """
    )
    return [dict(r) for r in rows] if rows else []


def get_periodo_by_id(periodo_id):
    rows = execute_query(
        "SELECT id, fecha_inicio, fecha_fin, observacion FROM cuenta_final_periodos WHERE id = %s LIMIT 1",
        (periodo_id,),
    )
    return dict(rows[0]) if rows else None


def create_periodo_cuenta_final(fecha_inicio, fecha_fin, observacion=""):
    user = get_current_user()
    row = execute_insert(
        """
        INSERT INTO cuenta_final_periodos (fecha_inicio, fecha_fin, observacion, registrado_por)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (fecha_inicio, fecha_fin, observacion, user.get("id")),
    )
    periodo_id = int(row["id"]) if row else None
    registrar_accion(user.get("id"), user.get("nombre_completo"), f"Creo periodo cuenta final id={periodo_id}", "cuenta_final")
    return periodo_id


def update_periodo_cuenta_final(periodo_id, fecha_inicio, fecha_fin, observacion=""):
    user = get_current_user()
    execute_insert(
        """
        UPDATE cuenta_final_periodos
        SET fecha_inicio=%s,
            fecha_fin=%s,
            observacion=%s,
            registrado_por=%s,
            updated_at=NOW()
        WHERE id=%s
        """,
        (fecha_inicio, fecha_fin, observacion, user.get("id"), periodo_id),
        fetch=False,
    )


def get_cuenta_final_by_periodo_cuenta(periodo_cuenta_id):
    rows = execute_query(
        "SELECT * FROM cuenta_final WHERE periodo_cuenta_id = %s ORDER BY id DESC LIMIT 1",
        (periodo_cuenta_id,),
    )
    return dict(rows[0]) if rows else None


def ensure_cuenta_final_base(periodo_cuenta_id):
    existente = get_cuenta_final_by_periodo_cuenta(periodo_cuenta_id)
    if existente:
        return int(existente["id"])

    user = get_current_user()
    row = execute_insert(
        """
        INSERT INTO cuenta_final (
            periodo_carga_id,
            periodo_cuenta_id,
            ingreso_molienda,
            total_gastos_socio1,
            total_gastos_socio2,
            ganancia_neta,
            observacion,
            registrado_por
        )
        VALUES (NULL, %s, 0, 0, 0, 0, '', %s)
        RETURNING id
        """,
        (periodo_cuenta_id, user.get("id")),
    )
    return int(row["id"]) if row else None


def save_cuenta_final(periodo_cuenta_id, ingreso, total_s1, total_s2, ganancia, obs=""):
    user = get_current_user()
    existente = get_cuenta_final_by_periodo_cuenta(periodo_cuenta_id)
    if existente:
        execute_insert(
            """
            UPDATE cuenta_final
            SET ingreso_molienda=%s,
                total_gastos_socio1=%s,
                total_gastos_socio2=%s,
                ganancia_neta=%s,
                observacion=%s,
                registrado_por=%s
            WHERE id=%s
            """,
            (ingreso, total_s1, total_s2, ganancia, obs, user.get("id"), existente["id"]),
            fetch=False,
        )
    else:
        execute_insert(
            """
            INSERT INTO cuenta_final (
                periodo_carga_id,
                periodo_cuenta_id,
                ingreso_molienda,
                total_gastos_socio1,
                total_gastos_socio2,
                ganancia_neta,
                observacion,
                registrado_por
            )
            VALUES (NULL, %s, %s, %s, %s, %s, %s, %s)
            """,
            (periodo_cuenta_id, ingreso, total_s1, total_s2, ganancia, obs, user.get("id")),
            fetch=False,
        )
    registrar_accion(user.get("id"), user.get("nombre_completo"), f"Guardo cuenta final periodo={periodo_cuenta_id}", "cuenta_final")


def get_planilla_no_asignada(fi, ff, exigir_rango_trabajador=True):
    if exigir_rango_trabajador:
        rango_sql = """
          AND p.fecha >= COALESCE(t.fecha_inicio_planilla, p.fecha)
          AND (t.fecha_fin_planilla IS NULL OR p.fecha <= t.fecha_fin_planilla)
        """
    else:
        rango_sql = ""

    query = f"""
        SELECT p.id, p.fecha, t.nombre_completo, p.estado, p.motivo
        FROM planilla p
        JOIN trabajadores t ON t.id = p.trabajador_id
        LEFT JOIN cuenta_final_planilla_asignaciones a ON a.planilla_id = p.id
        WHERE p.fecha BETWEEN %s AND %s
          AND a.planilla_id IS NULL
          {rango_sql}
        ORDER BY p.fecha, t.nombre_completo
    """
    rows = execute_query(query, (fi, ff))
    return [dict(r) for r in rows] if rows else []


def assign_planilla_ids(cuenta_final_id, planilla_ids):
    user = get_current_user()
    if not planilla_ids:
        return
    execute_insert(
        """
        INSERT INTO cuenta_final_planilla_asignaciones (cuenta_final_id, planilla_id, assigned_by)
        SELECT %s, p.id, %s
        FROM planilla p
        WHERE p.id = ANY(%s)
        """,
        (cuenta_final_id, user.get("id"), planilla_ids),
        fetch=False,
    )


def assign_adelantos_periodo(cuenta_final_id, fi, ff):
    user = get_current_user()

    execute_insert(
        """
        INSERT INTO cuenta_final_adelanto_asignaciones (cuenta_final_id, adelanto_id, assigned_by)
        SELECT %s, ad.id, %s
        FROM adelantos ad
        LEFT JOIN cuenta_final_adelanto_asignaciones a ON a.adelanto_id = ad.id
        WHERE ad.fecha BETWEEN %s AND %s
          AND a.adelanto_id IS NULL
        """,
        (cuenta_final_id, user.get("id"), fi, ff),
        fetch=False,
    )


def get_pension_no_asignada(fi, ff, exigir_rango_trabajador=True):
    if exigir_rango_trabajador:
        rango_sql = """
          AND p.fecha >= COALESCE(t.fecha_inicio_pension, p.fecha)
          AND (t.fecha_fin_pension IS NULL OR p.fecha <= t.fecha_fin_pension)
        """
    else:
        rango_sql = ""

    query = f"""
        SELECT p.id, p.fecha, t.nombre_completo, p.estado, p.detalle
        FROM pension p
        JOIN trabajadores t ON t.id = p.trabajador_id
        LEFT JOIN cuenta_final_pension_asignaciones a ON a.pension_id = p.id
        WHERE p.fecha BETWEEN %s AND %s
          AND a.pension_id IS NULL
          {rango_sql}
        ORDER BY p.fecha, t.nombre_completo
    """
    rows = execute_query(query, (fi, ff))
    return [dict(r) for r in rows] if rows else []


def assign_pension_ids(cuenta_final_id, pension_ids):
    user = get_current_user()
    if not pension_ids:
        return
    execute_insert(
        """
        INSERT INTO cuenta_final_pension_asignaciones (cuenta_final_id, pension_id, assigned_by)
        SELECT %s, p.id, %s
        FROM pension p
        WHERE p.id = ANY(%s)
        """,
        (cuenta_final_id, user.get("id"), pension_ids),
        fetch=False,
    )


def assign_socios(cuenta_final_id, fi, ff):
    user = get_current_user()
    execute_insert(
        """
        INSERT INTO cuenta_final_inversion_asignaciones (cuenta_final_id, inversion_id, assigned_by)
        SELECT %s, i.id, %s
        FROM inversiones i
        LEFT JOIN cuenta_final_inversion_asignaciones a ON a.inversion_id = i.id
        WHERE i.fecha BETWEEN %s AND %s
          AND a.inversion_id IS NULL
        """,
        (cuenta_final_id, user.get("id"), fi, ff),
        fetch=False,
    )

    execute_insert(
        """
        INSERT INTO cuenta_final_molienda_asignaciones (cuenta_final_id, molienda_id, assigned_by)
        SELECT %s, m.id, %s
        FROM molienda m
        LEFT JOIN cuenta_final_molienda_asignaciones a ON a.molienda_id = m.id
        WHERE m.fecha BETWEEN %s AND %s
          AND a.molienda_id IS NULL
        """,
        (cuenta_final_id, user.get("id"), fi, ff),
        fetch=False,
    )


def get_sueldos_detalle_asignado(cuenta_final_id):
    planilla_rows = execute_query(
        """
        SELECT t.id AS trabajador_id, t.nombre_completo, t.sueldo_base,
               COUNT(CASE WHEN p.estado IN ('presente','permiso') THEN 1 END) AS dias_pagados
        FROM cuenta_final_planilla_asignaciones a
        JOIN planilla p ON p.id = a.planilla_id
        JOIN trabajadores t ON t.id = p.trabajador_id
        WHERE a.cuenta_final_id = %s
        GROUP BY t.id, t.nombre_completo, t.sueldo_base
        """,
        (cuenta_final_id,),
    )
    adel_rows = execute_query(
        """
        SELECT ad.trabajador_id, COALESCE(SUM(ad.monto), 0) AS total_adelantos
        FROM cuenta_final_adelanto_asignaciones a
        JOIN adelantos ad ON ad.id = a.adelanto_id
        WHERE a.cuenta_final_id = %s
        GROUP BY ad.trabajador_id
        """,
        (cuenta_final_id,),
    )

    adel_map = {int(r["trabajador_id"]): float(r["total_adelantos"] or 0) for r in adel_rows}
    detalle = []
    total_neto = 0.0

    for r in planilla_rows:
        rr = dict(r)
        tid = int(rr["trabajador_id"])
        dias = int(rr.get("dias_pagados") or 0)
        sueldo = float(rr.get("sueldo_base") or 0)
        subtotal = dias * sueldo
        adelantos_total = adel_map.get(tid, 0.0)
        neto = subtotal - adelantos_total
        neto_a_pagar = max(neto, 0.0)
        deuda = abs(neto) if neto < 0 else 0.0
        total_neto += neto_a_pagar
        detalle.append(
            {
                "Trabajador": rr.get("nombre_completo"),
                "Dias pagados": dias,
                "Sueldo dia (S/)": round(sueldo, 2),
                "Subtotal (S/)": round(subtotal, 2),
                "Adelantos (S/)": round(adelantos_total, 2),
                "Neto a pagar (S/)": round(neto_a_pagar, 2),
                "Deuda (S/)": round(deuda, 2),
            }
        )

    return detalle, total_neto


def get_monto_dia_pension():
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
        (DEFAULT_MONTO_DIA_PENSION,),
        fetch=False,
    )
    return DEFAULT_MONTO_DIA_PENSION


def get_pension_detalle_asignado(cuenta_final_id):
    monto_dia = get_monto_dia_pension()
    rows = execute_query(
        """
        SELECT t.id, t.nombre_completo,
               COUNT(CASE WHEN p.estado = 'si' THEN 1 END) AS dias_si
        FROM cuenta_final_pension_asignaciones a
        JOIN pension p ON p.id = a.pension_id
        JOIN trabajadores t ON t.id = p.trabajador_id
        WHERE a.cuenta_final_id = %s
        GROUP BY t.id, t.nombre_completo
        ORDER BY t.nombre_completo
        """,
        (cuenta_final_id,),
    )

    detalle = []
    total = 0.0
    for r in rows:
        rr = dict(r)
        dias_si = int(rr.get("dias_si") or 0)
        monto_total = dias_si * float(monto_dia)
        total += monto_total
        detalle.append(
            {
                "Trabajador": rr.get("nombre_completo"),
                "Dias pension (SI)": dias_si,
                "Monto dia (S/)": round(float(monto_dia), 2),
                "Total pension (S/)": round(monto_total, 2),
            }
        )

    return detalle, total


def get_totales_socios_asignado(cuenta_final_id, socios):
    inv_rows = execute_query(
        """
        SELECT i.socio_id, COALESCE(SUM(i.monto),0) AS total
        FROM cuenta_final_inversion_asignaciones a
        JOIN inversiones i ON i.id = a.inversion_id
        WHERE a.cuenta_final_id = %s
        GROUP BY i.socio_id
        """,
        (cuenta_final_id,),
    )
    mol_rows = execute_query(
        """
        SELECT m.socio_id, COALESCE(SUM(m.monto),0) AS total
        FROM cuenta_final_molienda_asignaciones a
        JOIN molienda m ON m.id = a.molienda_id
        WHERE a.cuenta_final_id = %s
        GROUP BY m.socio_id
        """,
        (cuenta_final_id,),
    )

    inv_map = {int(r["socio_id"]): float(r["total"] or 0) for r in inv_rows}
    mol_map = {int(r["socio_id"]): float(r["total"] or 0) for r in mol_rows}

    totales = []
    total_socios = 0.0
    for s in socios:
        ss = dict(s)
        sid = int(ss["id"])
        t_inv = inv_map.get(sid, 0.0)
        t_mol = mol_map.get(sid, 0.0)
        t = t_inv + t_mol
        total_socios += t
        totales.append((sid, t_inv, t_mol, t))

    return totales, total_socios


def get_luz_no_asignados():
    rows = execute_query(
        """
        SELECT l.id, l.fecha_inicio, l.fecha_fin, l.monto, l.pagado, l.observacion
        FROM luz_mensual l
        LEFT JOIN periodo_luz_asignaciones a ON a.luz_id = l.id
        WHERE a.luz_id IS NULL
          AND l.pagado = TRUE
        ORDER BY l.id DESC
        """
    )
    return [dict(r) for r in rows] if rows else []


def get_luz_asignados_periodo(periodo_id):
    rows = execute_query(
        """
        SELECT l.id, l.fecha_inicio, l.fecha_fin, l.monto, l.pagado, l.observacion
        FROM periodo_luz_asignaciones a
        JOIN luz_mensual l ON l.id = a.luz_id
        WHERE a.periodo_id = %s
        ORDER BY l.id DESC
        """,
        (periodo_id,),
    )
    return [dict(r) for r in rows] if rows else []


def assign_luz(periodo_id, luz_ids):
    if not luz_ids:
        return
    user = get_current_user()
    for luz_id in luz_ids:
        execute_insert(
            """
            INSERT INTO periodo_luz_asignaciones (periodo_id, luz_id, assigned_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (luz_id) DO NOTHING
            """,
            (periodo_id, luz_id, user.get("id")),
            fetch=False,
        )
    execute_insert(
        """
        UPDATE luz_mensual
        SET pagado = TRUE,
            registrado_por = %s,
            updated_at = NOW()
        WHERE id = ANY(%s)
        """,
        (user.get("id"), luz_ids),
        fetch=False,
    )


def unassign_luz(periodo_id, luz_ids):
        if not luz_ids:
                return
        execute_insert(
                "DELETE FROM periodo_luz_asignaciones WHERE periodo_id = %s AND luz_id = ANY(%s)",
                (periodo_id, luz_ids),
                fetch=False,
        )


def auto_assign_default_records(cuenta_final_id, fi, ff, user_id):
        periodo_id = st.session_state.get("periodo_sistema_id")

        execute_insert(
                """
                DELETE FROM cuenta_final_planilla_asignaciones a
                USING planilla p
                JOIN trabajadores t ON t.id = p.trabajador_id
                LEFT JOIN cuenta_final_periodos cp ON cp.id = %s
                LEFT JOIN trabajador_planilla_periodo_config cfg ON cfg.trabajador_id = t.id AND cfg.periodo_id = %s
                WHERE a.cuenta_final_id = %s
                    AND a.planilla_id = p.id
                    AND (
                                p.periodo_sistema_id = %s
                        AND p.fecha >= COALESCE(cfg.fecha_inicio, cp.fecha_inicio, t.fecha_inicio_planilla, p.fecha)
                        AND (
                                COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_planilla) IS NULL
                                OR p.fecha <= COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_planilla)
                        )
                    ) IS NOT TRUE
                """,
                (periodo_id, periodo_id, cuenta_final_id, periodo_id),
                fetch=False,
        )

        execute_insert(
                """
                INSERT INTO cuenta_final_planilla_asignaciones (cuenta_final_id, planilla_id, assigned_by)
                SELECT %s, p.id, %s
                FROM planilla p
                JOIN trabajadores t ON t.id = p.trabajador_id
                LEFT JOIN cuenta_final_periodos cp ON cp.id = %s
                LEFT JOIN trabajador_planilla_periodo_config cfg ON cfg.trabajador_id = t.id AND cfg.periodo_id = %s
                LEFT JOIN cuenta_final_planilla_asignaciones a ON a.planilla_id = p.id
                WHERE p.periodo_sistema_id = %s
                    AND p.fecha >= COALESCE(cfg.fecha_inicio, cp.fecha_inicio, t.fecha_inicio_planilla, p.fecha)
                    AND (
                                COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_planilla) IS NULL
                                OR p.fecha <= COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_planilla)
                    )
                    AND a.planilla_id IS NULL
                """,
                (cuenta_final_id, user_id, periodo_id, periodo_id, periodo_id),
                fetch=False,
        )

        execute_insert(
                """
                DELETE FROM cuenta_final_adelanto_asignaciones a
                USING adelantos ad
                WHERE a.cuenta_final_id = %s
                    AND a.adelanto_id = ad.id
                    AND (
                                ad.periodo_sistema_id = %s
                                OR (ad.periodo_sistema_id IS NULL AND ad.fecha BETWEEN %s AND %s)
                    ) IS NOT TRUE
                """,
                (cuenta_final_id, periodo_id, fi, ff),
                fetch=False,
        )

        execute_insert(
                """
                INSERT INTO cuenta_final_adelanto_asignaciones (cuenta_final_id, adelanto_id, assigned_by)
                SELECT %s, ad.id, %s
                FROM adelantos ad
                LEFT JOIN cuenta_final_adelanto_asignaciones a ON a.adelanto_id = ad.id
                WHERE (
                                ad.periodo_sistema_id = %s
                                OR (ad.periodo_sistema_id IS NULL AND ad.fecha BETWEEN %s AND %s)
                            )
                    AND a.adelanto_id IS NULL
                """,
                (cuenta_final_id, user_id, periodo_id, fi, ff),
                fetch=False,
        )

        execute_insert(
                """
                DELETE FROM cuenta_final_pension_asignaciones a
                USING pension p
                JOIN trabajadores t ON t.id = p.trabajador_id
                LEFT JOIN cuenta_final_periodos cp ON cp.id = %s
                LEFT JOIN trabajador_pension_periodo_config cfg ON cfg.trabajador_id = t.id AND cfg.periodo_id = %s
                WHERE a.cuenta_final_id = %s
                    AND a.pension_id = p.id
                    AND (
                                p.periodo_sistema_id = %s
                        AND p.fecha >= COALESCE(cfg.fecha_inicio, cp.fecha_inicio, t.fecha_inicio_pension, p.fecha)
                        AND (
                                COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_pension) IS NULL
                                OR p.fecha <= COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_pension)
                        )
                    ) IS NOT TRUE
                """,
                (periodo_id, periodo_id, cuenta_final_id, periodo_id),
                fetch=False,
        )

        execute_insert(
                """
                INSERT INTO cuenta_final_pension_asignaciones (cuenta_final_id, pension_id, assigned_by)
                SELECT %s, p.id, %s
                FROM pension p
                JOIN trabajadores t ON t.id = p.trabajador_id
                LEFT JOIN cuenta_final_periodos cp ON cp.id = %s
                LEFT JOIN trabajador_pension_periodo_config cfg ON cfg.trabajador_id = t.id AND cfg.periodo_id = %s
                LEFT JOIN cuenta_final_pension_asignaciones a ON a.pension_id = p.id
                WHERE p.periodo_sistema_id = %s
                    AND p.fecha >= COALESCE(cfg.fecha_inicio, cp.fecha_inicio, t.fecha_inicio_pension, p.fecha)
                    AND (
                                COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_pension) IS NULL
                                OR p.fecha <= COALESCE(cfg.fecha_fin, cp.fecha_fin, t.fecha_fin_pension)
                    )
                    AND a.pension_id IS NULL
                """,
                (cuenta_final_id, user_id, periodo_id, periodo_id, periodo_id),
                fetch=False,
        )

        execute_insert(
                """
                DELETE FROM cuenta_final_inversion_asignaciones a
                USING inversiones i
                WHERE a.cuenta_final_id = %s
                    AND a.inversion_id = i.id
                    AND (
                                i.periodo_sistema_id = %s
                                OR (i.periodo_sistema_id IS NULL AND i.fecha BETWEEN %s AND %s)
                    ) IS NOT TRUE
                """,
                (cuenta_final_id, periodo_id, fi, ff),
                fetch=False,
        )

        execute_insert(
                """
                INSERT INTO cuenta_final_inversion_asignaciones (cuenta_final_id, inversion_id, assigned_by)
                SELECT %s, i.id, %s
                FROM inversiones i
                LEFT JOIN cuenta_final_inversion_asignaciones a ON a.inversion_id = i.id
                WHERE (
                                i.periodo_sistema_id = %s
                                OR (i.periodo_sistema_id IS NULL AND i.fecha BETWEEN %s AND %s)
                            )
                    AND a.inversion_id IS NULL
                """,
                (cuenta_final_id, user_id, periodo_id, fi, ff),
                fetch=False,
        )

        execute_insert(
                """
                DELETE FROM cuenta_final_molienda_asignaciones a
                USING molienda m
                WHERE a.cuenta_final_id = %s
                    AND a.molienda_id = m.id
                    AND (
                        m.periodo_sistema_id = %s
                        OR (m.periodo_sistema_id IS NULL AND m.fecha BETWEEN %s AND %s)
                    ) IS NOT TRUE
                """,
                (cuenta_final_id, periodo_id, fi, ff),
                fetch=False,
        )

        # Para molienda se usa el mismo criterio que Sacar Cuentas:
        # solo el recorrido mas reciente por socio dentro del periodo activo.
        execute_insert(
                "DELETE FROM cuenta_final_molienda_asignaciones WHERE cuenta_final_id = %s",
                (cuenta_final_id,),
                fetch=False,
        )

        execute_insert(
                """
                INSERT INTO cuenta_final_molienda_asignaciones (cuenta_final_id, molienda_id, assigned_by)
                SELECT %s, mm.id, %s
                FROM (
                    SELECT DISTINCT ON (m.socio_id)
                        m.id,
                        m.socio_id,
                        m.fecha
                    FROM molienda m
                    WHERE (
                        m.periodo_sistema_id = %s
                        OR (m.periodo_sistema_id IS NULL AND m.fecha BETWEEN %s AND %s)
                    )
                    ORDER BY m.socio_id, m.fecha DESC, m.id DESC
                ) mm
                """,
                (cuenta_final_id, user_id, periodo_id, fi, ff),
                fetch=False,
        )


def render():
    st.title("📊 Cuenta Final")
    user = get_current_user()
    can_edit = user.get("rol") in ("admin", "socio")

    _ensure_cuenta_final_schema()

    socios = execute_query("SELECT * FROM usuarios WHERE rol = 'socio' AND activo = TRUE ORDER BY id")
    if not socios:
        st.warning("No hay socios registrados.")
        return

    periodo_cuenta_id = st.session_state.get("periodo_sistema_id")
    if not periodo_cuenta_id:
        st.warning("No hay periodo del sistema seleccionado en el sidebar.")
        return

    periodo_sel = get_periodo_by_id(periodo_cuenta_id)
    if not periodo_sel:
        st.warning("El periodo seleccionado no existe. Selecciona otro en el sidebar.")
        return

    periodo_fi = periodo_sel["fecha_inicio"]
    periodo_ff = periodo_sel["fecha_fin"] or date.today()

    st.info(f"📅 Periodo del sidebar: {periodo_fi} -> {periodo_sel['fecha_fin'] or 'Abierto'}")
    st.caption("Este periodo controla asignaciones por ID: Planilla, Adelantos, Pension, Inversiones, Molienda y Luz.")

    cuenta_final_id = ensure_cuenta_final_base(periodo_cuenta_id) if can_edit else (get_cuenta_final_by_periodo_cuenta(periodo_cuenta_id) or {}).get("id")
    if not cuenta_final_id:
        st.warning("No se pudo preparar la cuenta final de este periodo.")
        return

    if can_edit:
        auto_assign_default_records(cuenta_final_id, periodo_fi, periodo_ff, user.get("id"))

    st.markdown("---")
    st.subheader("🔗 Asignaciones del periodo")
    st.caption("Planilla, Pension y Gastos de Socios se autoasignan por periodo_sistema_id del sidebar.")
    if can_edit and st.button("🔄 Recalcular autoasignaciones", key="cf_recalc_auto"):
        auto_assign_default_records(cuenta_final_id, periodo_fi, periodo_ff, user.get("id"))
        st.success("Autoasignaciones actualizadas.")
        st.rerun()

    st.markdown("---")
    st.subheader("⚡ Luz del periodo (asignar / desasignar)")
    luz_no_asig = get_luz_no_asignados()
    luz_sel_ids = []
    if luz_no_asig:
        df_luz_no = pd.DataFrame(
            [
                {
                    "Seleccionar": False,
                    "ID": r.get("id"),
                    "Fecha inicio": r.get("fecha_inicio"),
                    "Fecha fin": r.get("fecha_fin"),
                    "Monto (S/)": float(r.get("monto") or 0),
                    "Estado pago": "Pagado" if r.get("pagado") else "Pendiente",
                    "Observacion": r.get("observacion") or "",
                }
                for r in luz_no_asig
            ]
        )
        df_luz_edit = st.data_editor(
            df_luz_no,
            use_container_width=True,
            hide_index=True,
            key="cf_luz_no_asig_tbl",
            column_config={"Seleccionar": st.column_config.CheckboxColumn("Asignar")},
            disabled=[c for c in df_luz_no.columns if c != "Seleccionar"],
        )
        sel_rows = df_luz_edit[df_luz_edit["Seleccionar"] == True]
        luz_sel_ids = [int(v) for v in sel_rows["ID"].tolist()]
        if can_edit and st.button("✅ Asignar pagos de luz a este periodo", key="cf_assign_luz"):
            if not luz_sel_ids:
                st.error("Selecciona al menos una fila de luz.")
            else:
                assign_luz(periodo_cuenta_id, luz_sel_ids)
                st.success("Pagos de luz asignados al periodo.")
                st.rerun()
    else:
        st.info("No hay pagos de luz pagados no asignados.")

    luz_asig = get_luz_asignados_periodo(periodo_cuenta_id)
    if luz_asig:
        st.markdown("#### Luz asignada a este periodo")
        df_luz_asig = pd.DataFrame(
            [
                {
                    "Seleccionar": False,
                    "ID": r.get("id"),
                    "Inicio": r.get("fecha_inicio"),
                    "Fin": r.get("fecha_fin"),
                    "Monto (S/)": float(r.get("monto") or 0),
                    "Pagado": "Si" if r.get("pagado") else "No",
                    "Observacion": r.get("observacion") or "",
                }
                for r in luz_asig
            ]
        )
        df_luz_asig_edit = st.data_editor(
            df_luz_asig,
            use_container_width=True,
            hide_index=True,
            key="cf_luz_asig_tbl",
            column_config={"Seleccionar": st.column_config.CheckboxColumn("Desasignar")},
            disabled=[c for c in df_luz_asig.columns if c != "Seleccionar"],
        )
        sel_rows_un = df_luz_asig_edit[df_luz_asig_edit["Seleccionar"] == True]
        luz_un_ids = [int(v) for v in sel_rows_un["ID"].tolist()]
        if can_edit and st.button("↩️ Dejar de asignar pagos de luz", key="cf_unassign_luz"):
            if not luz_un_ids:
                st.error("Selecciona al menos una fila asignada.")
            else:
                unassign_luz(periodo_cuenta_id, luz_un_ids)
                st.success("Pagos de luz desasignados del periodo.")
                st.rerun()
    else:
        st.info("No hay luz asignada a este periodo.")

    luz_total = sum(float(x.get("monto") or 0) for x in luz_asig)
    st.markdown(f"**Total luz asignada: S/ {luz_total:,.2f}**")

    sueldos_det, sueldos_total = get_sueldos_detalle_asignado(cuenta_final_id)
    pension_det, pension_total = get_pension_detalle_asignado(cuenta_final_id)
    socio_totales, total_socios = get_totales_socios_asignado(cuenta_final_id, socios)

    st.markdown("---")
    st.subheader("📋 Planilla asignada")
    if sueldos_det:
        st.dataframe(pd.DataFrame(sueldos_det), use_container_width=True)
    else:
        st.info("No hay planilla asignada a esta cuenta final.")
    st.markdown(f"**Total planilla (neto): S/ {sueldos_total:,.2f}**")

    st.markdown("---")
    st.subheader("🍽️ Pension asignada")
    if pension_det:
        st.dataframe(pd.DataFrame(pension_det), use_container_width=True)
    else:
        st.info("No hay pension asignada a esta cuenta final.")
    st.markdown(f"**Total pension: S/ {pension_total:,.2f}**")

    st.markdown("---")
    cols = st.columns(len(socios))
    socio_totales_map = {sid: (t_inv, t_mol, t) for sid, t_inv, t_mol, t in socio_totales}
    for col, s in zip(cols, socios):
        ss = dict(s)
        sid = int(ss["id"])
        t_inv, t_mol, t_tot = socio_totales_map.get(sid, (0.0, 0.0, 0.0))
        with col:
            st.subheader(f"👤 {ss['nombre_completo'].split()[0]}")
            st.metric("Inversiones", f"S/ {t_inv:,.2f}")
            st.metric("Recorrido molienda", f"S/ {t_mol:,.2f}")
            st.metric("Total socio", f"S/ {t_tot:,.2f}")
    st.markdown(f"**Total socios: S/ {total_socios:,.2f}**")

    gastos_globales = sueldos_total + pension_total + luz_total
    grand_total = total_socios + gastos_globales

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total socios", f"S/ {total_socios:,.2f}")
    c2.metric("Total sueldos", f"S/ {sueldos_total:,.2f}")
    c3.metric("Total pension", f"S/ {pension_total:,.2f}")
    st.metric("Total luz", f"S/ {luz_total:,.2f}")
    st.metric("🔴 TOTAL GASTOS COMBINADOS", f"S/ {grand_total:,.2f}")

    st.markdown("---")
    st.subheader("💵 Ingreso por Molienda")
    cf_existente = get_cuenta_final_by_periodo_cuenta(periodo_cuenta_id)
    ingreso_actual = float(cf_existente.get("ingreso_molienda") or 0) if cf_existente else 0.0

    if can_edit:
        ingreso = st.number_input("Ingreso obtenido de la molienda (S/)", min_value=0.0, step=0.01, value=ingreso_actual, key="cf_ingreso")
        obs = st.text_area("Observacion", value=cf_existente.get("observacion", "") if cf_existente else "", key="cf_obs")
        ganancia_neta = ingreso - grand_total
        st.metric("Ganancia neta", f"S/ {ganancia_neta:,.2f}")

        socios_vals = [v[3] for v in socio_totales]
        t1 = socios_vals[0] if len(socios_vals) > 0 else 0.0
        t2 = socios_vals[1] if len(socios_vals) > 1 else 0.0

        if st.button("💾 Guardar Cuenta Final", key="cf_save"):
            save_cuenta_final(periodo_cuenta_id, ingreso, t1, t2, ganancia_neta, obs)
            st.success("Cuenta Final guardada correctamente.")
            st.rerun()

    st.markdown("---")
    export_data = []
    for s in socios:
        ss = dict(s)
        sid = int(ss["id"])
        t_inv, t_mol, t_tot = socio_totales_map.get(sid, (0.0, 0.0, 0.0))
        export_data.append(
            {
                "Socio": ss["nombre_completo"],
                "Inversiones (S/)": t_inv,
                "Recorrido molienda (S/)": t_mol,
                "Total socio (S/)": t_tot,
            }
        )

    df_exp = pd.DataFrame(export_data)

    luz_pdf_df = (
        pd.DataFrame(
            [
                {
                    "Inicio": x.get("fecha_inicio"),
                    "Fin": x.get("fecha_fin"),
                    "Monto (S/)": f"{float(x.get('monto') or 0):,.2f}",
                    "Estado": "Pagado" if x.get("pagado") else "Pendiente",
                    "Observacion": x.get("observacion") or "",
                }
                for x in luz_asig
            ]
        )
        if luz_asig
        else pd.DataFrame({"Info": ["Sin pagos de luz asignados"]})
    )

    planilla_pdf_df = (
        pd.DataFrame(sueldos_det)
        if sueldos_det
        else pd.DataFrame({"Info": ["Sin planilla asignada"]})
    )

    pension_pdf_df = (
        pd.DataFrame(pension_det)
        if pension_det
        else pd.DataFrame({"Info": ["Sin pension asignada"]})
    )

    socios_pdf_df = (
        df_exp.copy()
        if not df_exp.empty
        else pd.DataFrame({"Info": ["Sin gastos de socios asignados"]})
    )

    resumen_pdf_df = pd.DataFrame(
        [
            {"Concepto": "Total socios", "Monto (S/)": f"{total_socios:,.2f}"},
            {"Concepto": "Total sueldos", "Monto (S/)": f"{sueldos_total:,.2f}"},
            {"Concepto": "Total pension", "Monto (S/)": f"{pension_total:,.2f}"},
            {"Concepto": "Total luz", "Monto (S/)": f"{luz_total:,.2f}"},
            {"Concepto": "Total gastos combinados", "Monto (S/)": f"{grand_total:,.2f}"},
            {"Concepto": "Ingreso por molienda", "Monto (S/)": f"{ingreso_actual:,.2f}"},
            {
                "Concepto": "Ganancia neta estimada",
                "Monto (S/)": f"{(ingreso_actual - grand_total):,.2f}",
            },
        ]
    )

    pdf_sections = [
        ("Luz asignada", luz_pdf_df),
        ("Planilla asignada", planilla_pdf_df),
        ("Pension asignada", pension_pdf_df),
        ("Gastos por socio", socios_pdf_df),
        ("Resumen general", resumen_pdf_df),
    ]

    pdf_bytes = sections_to_pdf(
        pdf_sections,
        "Cuenta Final",
        f"Periodo: {periodo_fi} al {periodo_sel['fecha_fin'] or 'Abierto'}",
    )

    ex1, ex2 = st.columns(2)
    with ex1:
        st.download_button(
            "📥 Excel",
            df_to_excel(df_exp, "Cuenta Final"),
            file_name=f"cuenta_final_{periodo_ff}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with ex2:
        st.download_button(
            "📥 PDF",
            pdf_bytes,
            file_name=f"cuenta_final_{periodo_ff}.pdf",
            mime="application/pdf",
        )
