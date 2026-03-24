import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from utils.db import run_migrations
from utils.auth import login, logout, get_current_user, get_all_socios
from utils.db import execute_query, execute_insert

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sistema Minero",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

# --- Theming styles ---
if st.session_state.theme == 'dark':
    # Dark Gold Mining Theme
    bg_sidebar = "linear-gradient(180deg, #1C1E26 0%, #0D0F14 100%)"
    btn_color = "#E5E7EB"
    btn_hover_bg = "rgba(234, 179, 8, 0.15)"
    btn_hover_color = "#EAB308"
    h1_color = "#EAB308"  # Gold
    h2_color = "#FDE047"
    card_bg = "#1F232B"
    text_color = "#E5E7EB"
    main_bg = "#0F1219"
    accent_color = "#EAB308"
else:
    # Light Gold Mining Theme
    bg_sidebar = "linear-gradient(180deg, #F8FAFC 0%, #E2E8F0 100%)"
    btn_color = "#1E293B"
    btn_hover_bg = "rgba(202, 138, 4, 0.15)"
    btn_hover_color = "#CA8A04"
    h1_color = "#CA8A04"  # Darker Gold
    h2_color = "#A16207"
    card_bg = "#FFFFFF"
    text_color = "#1E293B"
    main_bg = "#F1F5F9"
    accent_color = "#CA8A04"

# ─── CSS personalizado ────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    /* Global */
    .stApp {{
        background-color: {main_bg};
        color: {text_color};
    }}
    /* Main container fix for Streamlit paddings */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {bg_sidebar} !important;
        border-right: 1px solid {accent_color}33;
    }}
    /* Sidebar Buttons (Menu items) */
    [data-testid="stSidebar"] .stButton button {{
        width: 100%;
        text-align: left;
        background: transparent;
        border: 1px solid transparent;
        color: {btn_color};
        padding: 10px 16px;
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
        font-weight: 500;
        margin-bottom: 4px;
        box-shadow: none;
    }}
    [data-testid="stSidebar"] .stButton button:hover,
    [data-testid="stSidebar"] .stButton button:active {{
        background: {btn_hover_bg};
        color: {btn_hover_color};
        border-left: 4px solid {accent_color};
        transform: translateX(2px);
    }}
    /* Main Buttons */
    .stButton > button {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {accent_color}55 !important;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        background-color: {btn_hover_bg} !important;
        border-color: {accent_color} !important;
        color: {accent_color} !important;
    }}
    /* Primary buttons */
    .stButton > button[data-baseweb="button"]:not(:hover) {{
        background-color: {accent_color} !important;
        color: #111827 !important;
        border: none;
    }}
    .stButton > button[data-baseweb="button"]:hover {{
        background-color: #FACC15 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px {accent_color}40;
    }}
    /* Headings */
    h1 {{ color: {h1_color} !important; font-weight: 800 !important; letter-spacing: -0.5px; }}
    h2 {{ color: {h2_color} !important; font-weight: 700 !important; }}
    h3, p, span, div, label {{ color: {text_color} !important; }}
    /* Metric components */
    [data-testid="stMetricValue"] {{ 
        font-size: 1.8rem !important; 
        color: {accent_color} !important; 
        font-weight: 800 !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.9rem !important;
        color: {text_color} !important;
        opacity: 0.8;
    }}
    /* Cards */
    div[data-testid="stMetric"] {{
        background: {card_bg};
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid {accent_color}22;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    .css-1r6slb0 {{ background: {card_bg}; border-radius: 12px; }}
    
    /* Tables and DataFrames container level fixes */
    [data-testid="stDataFrame"], [data-testid="stTable"] {{ 
        background-color: {card_bg} !important; 
        border-radius: 12px; 
    }}
    /* Important for inner Dataframe iframes when light mode Streamlit is dark but forced light */
    {"[data-testid='stDataFrame'] iframe { filter: invert(1) hue-rotate(180deg) brightness(0.95); }" if st.session_state.theme == 'light' else ""}
    
    thead tr th {{
        background-color: {bg_sidebar} !important;
        color: {accent_color} !important;
        font-weight: 700 !important;
        border-bottom: 2px solid {accent_color}44 !important;
    }}
    tbody tr td {{
        color: {text_color} !important;
        border-bottom: 1px solid {accent_color}11 !important;
    }}
    
    /* Inputs Fix: Specific baseweb classes Streamlit uses */
    input, textarea, div[data-baseweb="select"] > div {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {accent_color}44 !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="select"] span, div[data-baseweb="select"] svg {{
        color: {text_color} !important;
        fill: {text_color} !important;
    }}
    ul[data-baseweb="menu"] {{
        background-color: {card_bg} !important;
        border: 1px solid {accent_color}44 !important;
    }}
    ul[data-baseweb="menu"] li {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}
    ul[data-baseweb="menu"] li:hover {{
        background-color: {btn_hover_bg} !important;
        color: {accent_color} !important;
    }}
    
    input:focus, textarea:focus, div[data-baseweb="select"] > div:focus-within {{
        border-color: {accent_color} !important;
        box-shadow: 0 0 0 1px {accent_color} !important;
    }}
    /* Expander */
    .streamlit-expanderHeader {{
        background-color: {card_bg};
        border-radius: 8px;
        border: 1px solid {accent_color}33;
    }}
    /* Charts Native Canvas Inversion for Light Mode (If needed) */
    {"[data-testid='stVegaLiteChart'] canvas, [data-testid='stVegaLiteChart'] svg { filter: invert(1) hue-rotate(180deg) brightness(0.9); }" if st.session_state.theme == 'light' else ""}
    [data-testid="stVegaLiteChart"] {{
        background-color: {card_bg} !important;
        border-radius: 12px;
        padding: 5px;
    }}
</style>
""", unsafe_allow_html=True)

# ─── Inicializar BD ───────────────────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    run_migrations()
    st.session_state["db_initialized"] = True

# ─── Login ────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("## ⛏️ Sistema Minero")
        st.markdown("### Iniciar Sesión")
        username = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", type="primary", use_container_width=True):
            user = login(username, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop()

# ─── Usuario autenticado ──────────────────────────────────────────────────────
user = get_current_user()
rol = user.get("rol")
nombre = user.get("nombre_completo", "")


def _ensure_periodo_sidebar_schema():
    if st.session_state.get("_schema_periodo_sidebar_ready"):
        return

    execute_insert(
        """
        CREATE TABLE IF NOT EXISTS cuenta_final_periodos (
            id SERIAL PRIMARY KEY,
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE,
            observacion TEXT,
            registrado_por INTEGER REFERENCES usuarios(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        fetch=False,
    )
    execute_insert(
        "ALTER TABLE cuenta_final_periodos ALTER COLUMN fecha_fin DROP NOT NULL",
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
        "ALTER TABLE planilla DROP CONSTRAINT IF EXISTS planilla_trabajador_id_fecha_key",
        fetch=False,
    )
    execute_insert(
        "DROP INDEX IF EXISTS ux_pension_trabajador_fecha",
        fetch=False,
    )
    execute_insert(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_planilla_trabajador_fecha_periodo ON planilla(trabajador_id, fecha, periodo_sistema_id)",
        fetch=False,
    )
    execute_insert(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_pension_trabajador_fecha_periodo ON pension(trabajador_id, fecha, periodo_sistema_id) WHERE trabajador_id IS NOT NULL",
        fetch=False,
    )
    st.session_state["_schema_periodo_sidebar_ready"] = True


def _get_periodos_sidebar():
    rows = execute_query(
        """
        SELECT id, fecha_inicio, fecha_fin, observacion
        FROM cuenta_final_periodos
        ORDER BY id DESC
        """
    )
    return [dict(r) for r in rows] if rows else []

if rol in ("admin", "socio"):
    estado_cargas = execute_query(
        """
        SELECT
            EXISTS(SELECT 1 FROM cargas WHERE bajada = FALSE) AS hay_abierta,
            (SELECT bajada FROM cargas ORDER BY id DESC LIMIT 1) AS ultima_bajada
        """
    )
    if estado_cargas:
        estado = dict(estado_cargas[0])
        hay_abierta = bool(estado.get("hay_abierta"))
        ultima_bajada = bool(estado.get("ultima_bajada"))

        if (not hay_abierta) and ultima_bajada:
            st.markdown(
                """
                <div style="
                    background: #fff4ce;
                    border: 1px solid #e0b100;
                    color: #5c4400;
                    padding: 10px 14px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                    font-weight: 600;
                ">
                    Carga bajada
                </div>
                """,
                unsafe_allow_html=True,
            )

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### ⛏️ Sistema Minero")
    
    # Theme toggle
    theme_state = st.toggle("Modo Claro", value=(st.session_state.theme == 'light'))
    new_theme = 'light' if theme_state else 'dark'
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown(f"**{nombre}**  \n`{rol.upper()}`")
    st.markdown("---")

    if rol in ("admin", "socio", "pensionista"):
        _ensure_periodo_sidebar_schema()
        st.markdown("**Periodo del sistema**")
        periodos_sidebar = _get_periodos_sidebar()

        if periodos_sidebar:
            if not st.session_state.get("periodo_sistema_id"):
                st.session_state["periodo_sistema_id"] = int(periodos_sidebar[0]["id"])
            else:
                ids_validos = {int(p["id"]) for p in periodos_sidebar}
                if int(st.session_state.get("periodo_sistema_id")) not in ids_validos:
                    st.session_state["periodo_sistema_id"] = int(periodos_sidebar[0]["id"])

        if rol in ("admin", "socio"):
            with st.expander("➕ Crear nuevo periodo", expanded=(len(periodos_sidebar) == 0)):
                ps_fi = st.date_input("Inicio del nuevo periodo", key="sb_periodo_fi")
                ps_obs = st.text_input("Observacion", value="", key="sb_periodo_obs")
                if st.button("Crear periodo", key="sb_periodo_create"):
                    execute_insert(
                        """
                        INSERT INTO cuenta_final_periodos (fecha_inicio, fecha_fin, observacion, registrado_por)
                        VALUES (%s, NULL, %s, %s)
                        """,
                        (ps_fi, ps_obs, user.get("id")),
                        fetch=False,
                    )
                    st.success("Periodo creado (abierto).")
                    st.rerun()

        if periodos_sidebar:
            labels = [
                f"{p['id']} | {p['fecha_inicio']} -> {p['fecha_fin'] or 'Abierto'}"
                for p in periodos_sidebar
            ]
            default_idx = 0
            saved_pid = st.session_state.get("periodo_sistema_id")
            if saved_pid:
                for i, p in enumerate(periodos_sidebar):
                    if int(p["id"]) == int(saved_pid):
                        default_idx = i
                        break

            sel = st.selectbox("Periodo activo", labels, index=default_idx, key="sb_periodo_sel")
            periodo_id_activo = int(sel.split("|")[0].strip())
            st.session_state["periodo_sistema_id"] = periodo_id_activo

            p_act = next((p for p in periodos_sidebar if int(p["id"]) == periodo_id_activo), None)

            if p_act and rol in ("admin", "socio"):
                with st.expander("✏️ Editar periodo activo", expanded=False):
                    edit_fi = st.date_input(
                        "Inicio del periodo activo",
                        value=p_act["fecha_inicio"],
                        key=f"sb_periodo_edit_fi_{periodo_id_activo}",
                    )
                    edit_tiene_fin = st.checkbox(
                        "Este periodo tiene fecha fin",
                        value=bool(p_act.get("fecha_fin")),
                        key=f"sb_periodo_edit_has_ff_{periodo_id_activo}",
                    )
                    edit_ff = None
                    if edit_tiene_fin:
                        edit_ff = st.date_input(
                            "Fecha fin del periodo activo",
                            value=p_act.get("fecha_fin") or p_act["fecha_inicio"],
                            key=f"sb_periodo_edit_ff_{periodo_id_activo}",
                        )
                    edit_obs = st.text_input(
                        "Observacion del periodo activo",
                        value=p_act.get("observacion") or "",
                        key=f"sb_periodo_edit_obs_{periodo_id_activo}",
                    )

                    if st.button("Guardar cambios del periodo", key=f"sb_periodo_edit_save_{periodo_id_activo}"):
                        if edit_tiene_fin and edit_ff and edit_ff < edit_fi:
                            st.error("La fecha fin no puede ser menor a la fecha inicio.")
                        else:
                            execute_insert(
                                """
                                UPDATE cuenta_final_periodos
                                SET fecha_inicio = %s,
                                    fecha_fin = %s,
                                    observacion = %s,
                                    updated_at = NOW(),
                                    registrado_por = %s
                                WHERE id = %s
                                """,
                                (
                                    edit_fi,
                                    edit_ff if edit_tiene_fin else None,
                                    edit_obs,
                                    user.get("id"),
                                    periodo_id_activo,
                                ),
                                fetch=False,
                            )
                            st.success("Periodo actualizado.")
                            st.rerun()

            if p_act and (rol in ("admin", "socio")) and not p_act.get("fecha_fin"):
                cierre = st.date_input("Cerrar periodo en", key="sb_periodo_cierre")
                if st.button("Cerrar periodo", key="sb_periodo_close"):
                    if cierre < p_act["fecha_inicio"]:
                        st.error("La fecha fin no puede ser menor a la fecha inicio.")
                    else:
                        execute_insert(
                            "UPDATE cuenta_final_periodos SET fecha_fin = %s, updated_at = NOW(), registrado_por = %s WHERE id = %s",
                            (cierre, user.get("id"), periodo_id_activo),
                            fetch=False,
                        )
                        st.success("Periodo cerrado.")
                        st.rerun()
        else:
            st.caption("No hay periodos creados aun.")

        st.markdown("---")

    # Menú según rol
    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"

    def nav(label, key):
        if st.button(label, key=f"nav_{key}"):
            st.session_state["page"] = key
            st.rerun()

    nav("🏠 Dashboard", "dashboard")
    nav("🗓️ Asistencia-Planilla", "asistencia_planilla")
    nav("🍽️ Asistencia-Pensión", "asistencia_pension")
    nav("📋 Planilla", "planilla")
    nav("🍽️ Pensión", "pension")
    nav("🍽️ Cuentas - Pensión", "cuentas_pension")
    if rol != "pensionista":
        nav("💵 Sueldo de Trabajadores", "sueldos")

    if rol in ("admin", "socio"):
        nav("⛏️ Cargas", "cargas")
        nav("⚡ Luz", "luz")
        nav("🛏️ Alquiler de Cuarto", "alquiler_cuarto")

        # Sacar cuentas por socio
        socios = get_all_socios()
        if socios:
            st.markdown("**Sacar Cuentas:**")
            for s in socios:
                s = dict(s)
                primer_nombre = s["nombre_completo"].split()[0]
                if rol == "admin" or (rol == "socio" and user["id"] == s["id"]):
                    nav(f"  💼 {primer_nombre}", f"sc_{s['id']}_edit")
                else:
                    nav(f"  👁️ {primer_nombre}", f"sc_{s['id']}_view")

        nav("📊 Cuenta Final", "cuenta_final")

    if rol != "pensionista":
        nav("📜 Historial", "historial")

    if rol == "admin":
        st.markdown("---")
        nav("⚙️ Permisos / Admin", "permisos")

    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", key="nav_logout"):
        logout()

# ─── Router de páginas ────────────────────────────────────────────────────────
page = st.session_state.get("page", "dashboard")

# Dashboard
if page == "dashboard":
    st.title("🏠 Dashboard")
    st.markdown(f"Bienvenido, **{nombre}**")

    from datetime import date

    if rol == "pensionista":
        st.info("Aquí verás únicamente indicadores de pensión de tu periodo activo.")
        periodo_id = st.session_state.get("periodo_sistema_id")
        if not periodo_id:
            st.warning("Selecciona un periodo activo en el sidebar.")
            st.stop()

        hoy = date.today()
        resumen_pension = execute_query(
            """
            SELECT
                COUNT(*) FILTER (WHERE estado = 'si') AS dias_si,
                COUNT(*) FILTER (WHERE estado = 'no') AS dias_no,
                COUNT(*) FILTER (WHERE fecha = %s AND estado = 'si') AS hoy_si,
                COUNT(*) FILTER (WHERE fecha = %s AND estado = 'no') AS hoy_no,
                COUNT(DISTINCT trabajador_id) FILTER (WHERE trabajador_id IS NOT NULL) AS trabajadores_con_registro
            FROM pension
            WHERE periodo_sistema_id = %s
            """,
            (hoy, hoy, periodo_id),
        )
        rp = dict(resumen_pension[0]) if resumen_pension else {}
        c1, c2, c3 = st.columns(3)
        c1.metric("👷 Trabajadores con registro", int(rp.get("trabajadores_con_registro") or 0))
        c2.metric("✅ Días SI (periodo)", int(rp.get("dias_si") or 0))
        c3.metric("❌ Días NO (periodo)", int(rp.get("dias_no") or 0))

        c4, c5 = st.columns(2)
        c4.metric("Hoy SI", int(rp.get("hoy_si") or 0))
        c5.metric("Hoy NO", int(rp.get("hoy_no") or 0))

        st.markdown("---")
        st.subheader("📝 Tareas Rápidas")
        if st.button("Ir a Asistencia-Pensión", key="btn_go_asis_pen"):
            st.session_state["page"] = "asistencia_pension"
            st.rerun()
        if st.button("Ir a Registro de Pensión", key="btn_go_reg_pen"):
            st.session_state["page"] = "pension"
            st.rerun()

    else:
        col1, col2 = st.columns(2)
        header_rows = execute_query(
            """
            SELECT
                (SELECT COUNT(*) FROM trabajadores WHERE activo = TRUE) AS n_trabajadores,
                (SELECT COUNT(*) FROM cargas) AS n_cargas
            """
        )
        header = dict(header_rows[0]) if header_rows else {}
        
        col1.metric("👷 Trabajadores Activos",
                    int(header.get("n_trabajadores") or 0))
        col2.metric("⛏️ Total Cargas Registradas",
                    int(header.get("n_cargas") or 0))

        st.markdown("---")
        st.subheader("📊 Resumen del Periodo Activo (Para Socios)")

        periodo_id = st.session_state.get("periodo_sistema_id")
        if not periodo_id:
            st.info("Selecciona un periodo activo en el sidebar para ver el resumen.")
        else:
            resumen_periodo_rows = execute_query(
                """
                WITH p AS (
                    SELECT
                        id,
                        fecha_inicio,
                        fecha_fin,
                        COALESCE(fecha_fin, CURRENT_DATE) AS fecha_fin_real
                    FROM cuenta_final_periodos
                    WHERE id = %s
                    LIMIT 1
                )
                SELECT
                    p.fecha_inicio,
                    p.fecha_fin,
                    p.fecha_fin_real,

                    COALESCE((
                        SELECT SUM(i.monto)
                        FROM inversiones i
                        WHERE i.periodo_sistema_id = %s
                           OR (i.periodo_sistema_id IS NULL AND i.fecha BETWEEN p.fecha_inicio AND p.fecha_fin_real)
                    ), 0) AS total_inv,

                    COALESCE((
                        SELECT SUM(a.monto)
                        FROM adelantos a
                        WHERE a.periodo_sistema_id = %s
                           OR (a.periodo_sistema_id IS NULL AND a.fecha BETWEEN p.fecha_inicio AND p.fecha_fin_real)
                    ), 0) AS total_ade,

                    COALESCE((
                        SELECT c.toneladas
                        FROM cargas c
                        WHERE c.periodo_sistema_id = %s
                        ORDER BY c.id DESC
                        LIMIT 1
                    ), (
                        SELECT c2.toneladas
                        FROM cargas c2
                        WHERE c2.periodo_sistema_id IS NULL
                          AND c2.fecha BETWEEN p.fecha_inicio AND p.fecha_fin_real
                        ORDER BY c2.id DESC
                        LIMIT 1
                    ), 0) AS ton_cg,

                    CASE
                        WHEN EXISTS(
                            SELECT 1
                            FROM cargas c
                            WHERE c.periodo_sistema_id = %s
                        ) THEN 1
                        WHEN EXISTS(
                            SELECT 1
                            FROM cargas c2
                            WHERE c2.periodo_sistema_id IS NULL
                              AND c2.fecha BETWEEN p.fecha_inicio AND p.fecha_fin_real
                        ) THEN 1
                        ELSE 0
                    END AS cant_cg,

                    COALESCE((
                        SELECT COUNT(*) FILTER (WHERE pl.estado = 'presente')
                        FROM planilla pl
                        WHERE pl.periodo_sistema_id = %s
                    ), 0) AS presentes,

                    COALESCE((
                        SELECT COUNT(*) FILTER (WHERE pl.estado = 'falta')
                        FROM planilla pl
                        WHERE pl.periodo_sistema_id = %s
                    ), 0) AS faltas,

                    COALESCE((
                        SELECT COUNT(*) FILTER (WHERE pl.estado = 'permiso')
                        FROM planilla pl
                        WHERE pl.periodo_sistema_id = %s
                    ), 0) AS permisos
                FROM p
                """,
                (
                    periodo_id,
                    periodo_id,
                    periodo_id,
                    periodo_id,
                    periodo_id,
                    periodo_id,
                    periodo_id,
                    periodo_id,
                ),
            )
            if not resumen_periodo_rows:
                st.warning("El periodo activo seleccionado no existe.")
            else:
                resumen_periodo = dict(resumen_periodo_rows[0])
                f_ini = resumen_periodo['fecha_inicio']
                f_fin = resumen_periodo['fecha_fin']
                
                st.caption(f"Periodo analizado: **{f_ini}** al **{f_fin or 'Actualidad (Abierto)'}**")

                total_inv = float(resumen_periodo.get("total_inv") or 0.0)
                total_ade = float(resumen_periodo.get("total_ade") or 0.0)
                ton_cg = float(resumen_periodo.get("ton_cg") or 0.0)
                cant_cg = int(resumen_periodo.get("cant_cg") or 0)
                presentes = int(resumen_periodo.get("presentes") or 0)
                faltas = int(resumen_periodo.get("faltas") or 0)
                permisos = int(resumen_periodo.get("permisos") or 0)
                total_registros = presentes + faltas + permisos
                tasa_asistencia = (presentes / total_registros * 100.0) if total_registros > 0 else 0.0

                st.markdown("#### 💰 Impacto Económico en Curso")
                c1, c2, c3 = st.columns(3)
                c1.metric("Inversiones (S/)", f"S/ {float(total_inv):,.2f}")
                c2.metric("Adelantos Entregados", f"S/ {float(total_ade):,.2f}")
                c3.metric("Cargas Extraídas", f"{float(ton_cg):,.2f} ton")

                st.markdown("#### 👥 Comportamiento Laboral")
                c4, c5, c6 = st.columns(3)
                c4.metric("Días Operativos (Presencias)", presentes)
                c5.metric("Ausentismos Totales (Faltas)", faltas)
                c6.metric("Tasa de Asistencia", f"{tasa_asistencia:.1f}%")
                
                st.markdown("#### 📝 Notas y Notificaciones")
                if faltas > (presentes * 0.15) and presentes > 0:
                    st.warning(f"⚠️ Hay un índice de faltas elevado en este periodo ({faltas} faltas). Podría haber impacto en la productividad.")
                if float(total_inv) > 0:
                    st.info(f"💡 Se ha inyectado capital de **S/ {float(total_inv):,.2f}** a la operación.")
                if float(ton_cg) > 0:
                    st.success(f"⛏️ La producción en curso suma **{float(ton_cg):,.2f} toneladas** extraídas por la contrata.")
                if cant_cg == 0 and presentes > 10:
                    st.info("ℹ️ Hay presencias operativas del personal pero aún no se han registrado viajes de carga de mineral.")

# Planilla
elif page == "planilla":
    from modules.planilla import render
    render()

# Asistencia-Planilla de hoy
elif page == "asistencia_planilla":
    from modules.planilla import render_asistencia_hoy
    render_asistencia_hoy()

# Asistencia-Pensión de hoy
elif page == "asistencia_pension":
    from modules.pension import render_asistencia_hoy
    render_asistencia_hoy()

# Pensión
elif page == "pension":
    from modules.pension import render
    render()

# Cuentas Pensión (visible para todos)
elif page == "cuentas_pension":
    from modules.cuentas_pension import render
    render()

# Sueldos
elif page == "sueldos":
    if rol == "pensionista":
        st.error("Acceso no autorizado")
    else:
        from modules.sueldos_trabajadores import render
        render()

# Cargas
elif page == "cargas":
    if rol in ("admin", "socio"):
        from modules.cargas import render
        render()
    else:
        st.error("Acceso no autorizado")

# Luz
elif page == "luz":
    if rol in ("admin", "socio"):
        from modules.luz import render
        render()
    else:
        st.error("Acceso no autorizado")

# Alquiler de Cuarto
elif page == "alquiler_cuarto":
    if rol in ("admin", "socio"):
        from modules.alquiler_cuarto import render
        render()
    else:
        st.error("Acceso no autorizado")

# Sacar Cuentas por Socio
elif page.startswith("sc_"):
    if rol not in ("admin", "socio"):
        st.error("Acceso no autorizado")
        st.stop()

    parts = page.split("_")
    socio_id = int(parts[1])
    mode = parts[2]  # edit o view

    from utils.db import execute_query as eq
    socio_rows = eq("SELECT * FROM usuarios WHERE id = %s", (socio_id,))
    if socio_rows:
        socio = dict(socio_rows[0])
        readonly = (mode == "view")

        # Verificar acceso
        if mode == "edit" and rol == "socio" and user["id"] != socio_id:
            st.error("No puedes editar las cuentas de otro socio.")
            st.stop()

        from modules.sacar_cuentas import render
        render(socio=socio, readonly=readonly)
    else:
        st.error("Socio no encontrado")

# Cuenta Final
elif page == "cuenta_final":
    if rol in ("admin", "socio"):
        from modules.cuenta_final import render
        render()
    else:
        st.error("Acceso no autorizado")

# Historial
elif page == "historial":
    if rol == "pensionista":
        st.error("Acceso no autorizado")
    else:
        from modules.historial_ui import render
        render()

# Permisos
elif page == "permisos":
    from modules.permisos import render
    render()

else:
    st.error(f"Página no encontrada: {page}")
