import streamlit as st
import pandas as pd
from datetime import date
from utils.db import execute_query, execute_insert
from utils.auth import (create_user, get_all_users, toggle_user_active,
                         update_user_password, get_current_user, update_user_basic)
from utils.historial import registrar_accion

# ─── Trabajadores ────────────────────────────────────────────────────────────

def get_trabajadores():
    return execute_query("SELECT * FROM trabajadores ORDER BY nombre_completo")

def create_trabajador(nombre, dni, cargo, sueldo, fecha_inicio_planilla, fecha_fin_planilla, fecha_inicio_pension, fecha_fin_pension):
    user = get_current_user()
    execute_insert(
        """INSERT INTO trabajadores
                            (nombre_completo, dni, cargo, sueldo_base, fecha_inicio_planilla, fecha_fin_planilla, fecha_inicio_pension, fecha_fin_pension)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (nombre, dni, cargo, sueldo, fecha_inicio_planilla, fecha_fin_planilla, fecha_inicio_pension, fecha_fin_pension)
    )
    registrar_accion(user.get("id"), user.get("nombre_completo"),
                     f"Creó trabajador '{nombre}'", "permisos")

def toggle_trabajador(trab_id, activo):
    execute_insert("UPDATE trabajadores SET activo = %s WHERE id = %s", (activo, trab_id))

def update_trabajador(trab_id, nombre, dni, cargo, sueldo, fecha_inicio_planilla, fecha_fin_planilla, fecha_inicio_pension, fecha_fin_pension):
    user = get_current_user()
    execute_insert(
        """UPDATE trabajadores
           SET nombre_completo=%s, dni=%s, cargo=%s, sueldo_base=%s,
               fecha_inicio_planilla=%s, fecha_fin_planilla=%s,
               fecha_inicio_pension=%s, fecha_fin_pension=%s
           WHERE id=%s""",
        (nombre, dni, cargo, sueldo, fecha_inicio_planilla, fecha_fin_planilla, fecha_inicio_pension, fecha_fin_pension, trab_id)
    )
    registrar_accion(user.get("id"), user.get("nombre_completo"),
                     f"Actualizó trabajador id={trab_id}", "permisos")

# ─── Borrar datos ────────────────────────────────────────────────────────────

def borrar_datos_periodo(fecha_inicio, fecha_fin):
    user = get_current_user()
    tablas = [
        ("planilla", "fecha"),
        ("pension", "fecha"),
        ("inversiones", "fecha"),
        ("adelantos", "fecha"),
        ("molienda", "fecha"),
    ]
    for tabla, col_fecha in tablas:
        execute_insert(
            f"DELETE FROM {tabla} WHERE {col_fecha} BETWEEN %s AND %s",
            (fecha_inicio, fecha_fin)
        )
    execute_insert(
        "DELETE FROM cargas WHERE fecha BETWEEN %s AND %s",
        (fecha_inicio, fecha_fin)
    )
    registrar_accion(
        user.get("id"), user.get("nombre_completo"),
        f"Borró datos del periodo {fecha_inicio} al {fecha_fin}", "admin"
    )

# ─── UI ─────────────────────────────────────────────────────────────────────

def render():
    st.title("⚙️ Permisos y Administración")
    user = get_current_user()

    if user.get("rol") != "admin":
        st.error("Acceso restringido solo para el administrador.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["👤 Usuarios", "👷 Trabajadores", "🗑️ Borrar Datos"])

    # ── Tab Usuarios ──────────────────────────────────────────────────────
    with tab1:
        st.subheader("Gestión de Usuarios")

        with st.expander("➕ Crear Nuevo Usuario"):
            with st.form("usr_create_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input("Username", key="usr_username")
                    nombre = st.text_input("Nombre Completo", key="usr_nombre")
                with col2:
                    rol = st.selectbox("Rol", ["socio", "pensionista", "admin"], key="usr_rol")
                    password = st.text_input("Contraseña", type="password", key="usr_pass")
                    password2 = st.text_input("Confirmar contraseña", type="password", key="usr_pass2")

                submit_usr = st.form_submit_button("💾 Crear Usuario")

            if submit_usr:
                if not username or not nombre or not password:
                    st.error("Completa todos los campos")
                elif password != password2:
                    st.error("Las contraseñas no coinciden")
                else:
                    result = create_user(username, nombre, password, rol)
                    if result:
                        st.success(f"Usuario '{username}' creado con rol '{rol}'")
                        st.rerun()
                    else:
                        st.error("Error al crear usuario. ¿El username ya existe?")

        st.markdown("---")
        usuarios = get_all_users()
        if usuarios:
            for u in usuarios:
                u = dict(u)
                col1, col2, col3, col4 = st.columns([2, 1.5, 1, 1.5])
                col1.write(f"**{u['nombre_completo']}** (@{u['username']})")
                col2.write(u["rol"].upper())
                estado = "✅ Activo" if u["activo"] else "❌ Inactivo"
                col3.write(estado)
                with col4:
                    if u["username"] != "admin":
                        btn_label = "Desactivar" if u["activo"] else "Activar"
                        if st.button(btn_label, key=f"tog_usr_{u['id']}"):
                            toggle_user_active(u["id"], not u["activo"])
                            st.rerun()

            st.markdown("### ✏️ Editar Usuarios y Contraseñas")
            for u in usuarios:
                u = dict(u)

                titulo = f"Editar: {u['nombre_completo']} (@{u['username']})"
                with st.expander(titulo):
                    with st.form(f"usr_edit_form_{u['id']}"):
                        puede_editar_basico = u.get("rol") in ("socio", "pensionista") and u.get("username") != "admin"

                        if puede_editar_basico:
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                usr_edit_username = st.text_input(
                                    "Username",
                                    value=u["username"],
                                    key=f"usr_edit_username_{u['id']}",
                                )
                                usr_edit_nombre = st.text_input(
                                    "Nombre completo",
                                    value=u["nombre_completo"],
                                    key=f"usr_edit_nombre_{u['id']}",
                                )
                            with col_e2:
                                rol_default = "socio" if u["rol"] == "socio" else "pensionista"
                                usr_edit_rol = st.selectbox(
                                    "Rol",
                                    ["socio", "pensionista"],
                                    index=0 if rol_default == "socio" else 1,
                                    key=f"usr_edit_rol_{u['id']}",
                                )
                        else:
                            st.info("Para este usuario solo se permite cambiar contraseña.")

                        st.caption("Cambio de contraseña (opcional)")
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            usr_edit_pass = st.text_input(
                                "Nueva contraseña",
                                type="password",
                                key=f"usr_edit_pass_{u['id']}",
                            )
                        with col_p2:
                            usr_edit_pass2 = st.text_input(
                                "Confirmar nueva contraseña",
                                type="password",
                                key=f"usr_edit_pass2_{u['id']}",
                            )

                        submit_edit_usr = st.form_submit_button("💾 Guardar cambios")

                    if submit_edit_usr:
                        if (usr_edit_pass or usr_edit_pass2) and usr_edit_pass != usr_edit_pass2:
                            st.error("Las contraseñas no coinciden")
                        else:
                            ok = True
                            if puede_editar_basico:
                                if not usr_edit_username.strip() or not usr_edit_nombre.strip():
                                    st.warning("Username y nombre son obligatorios")
                                    ok = False
                                else:
                                    ok = update_user_basic(
                                        u["id"],
                                        usr_edit_username.strip(),
                                        usr_edit_nombre.strip(),
                                        usr_edit_rol,
                                    )

                            if ok:
                                if usr_edit_pass:
                                    update_user_password(u["id"], usr_edit_pass)
                                    st.success("Contraseña actualizada")
                                elif puede_editar_basico:
                                    st.success("Usuario actualizado")
                                else:
                                    st.info("No hubo cambios para guardar")
                                st.rerun()
                            else:
                                st.error("No se pudo actualizar. Verifica si el username ya existe.")

    # ── Tab Trabajadores ──────────────────────────────────────────────────
    with tab2:
        st.subheader("Gestión de Trabajadores")

        with st.expander("➕ Agregar Trabajador"):
            with st.form("trab_create_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    t_nombre = st.text_input("Nombre Completo", key="trab_nombre")
                    t_dni = st.text_input("DNI", key="trab_dni")
                with col2:
                    t_cargo = st.text_input("Cargo", value="Operario", key="trab_cargo")
                    t_sueldo = st.number_input("Sueldo por día (S/)", min_value=0.0, step=0.01, key="trab_sueldo")
                col3, col4 = st.columns(2)
                with col3:
                    t_fi_plan = st.date_input("Inicio planilla", value=date.today(), key="trab_fi_plan")
                with col4:
                    t_ff_plan_enabled = st.checkbox("Tiene fecha fin de planilla", key="trab_ff_plan_enabled")
                    t_ff_plan = st.date_input("Fin planilla", value=date.today(), key="trab_ff_plan") if t_ff_plan_enabled else None
                col5, col6 = st.columns(2)
                with col5:
                    t_fi_pen = st.date_input("Inicio pensión", value=date.today(), key="trab_fi_pen")
                with col6:
                    t_ff_pen_enabled = st.checkbox("Tiene fecha fin de pensión", key="trab_ff_pen_enabled")
                    t_ff_pen = st.date_input("Fin pensión", value=date.today(), key="trab_ff_pen") if t_ff_pen_enabled else None

                submit_trab = st.form_submit_button("💾 Agregar")

            if submit_trab:
                if t_nombre:
                    create_trabajador(t_nombre, t_dni, t_cargo, t_sueldo, t_fi_plan, t_ff_plan, t_fi_pen, t_ff_pen)
                    st.success(f"Trabajador '{t_nombre}' agregado")
                    st.rerun()
                else:
                    st.warning("El nombre es requerido")

        st.markdown("---")
        trabajadores = get_trabajadores()
        if trabajadores:
            for t in trabajadores:
                t = dict(t)
                with st.expander(f"{'✅' if t['activo'] else '❌'} {t['nombre_completo']} — {t['cargo']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        t_nom_edit = st.text_input("Nombre", value=t["nombre_completo"], key=f"te_nom_{t['id']}")
                        t_dni_edit = st.text_input("DNI", value=t["dni"] or "", key=f"te_dni_{t['id']}")
                    with col2:
                        t_car_edit = st.text_input("Cargo", value=t["cargo"] or "", key=f"te_car_{t['id']}")
                        t_sue_edit = st.number_input("Sueldo/día (S/)", value=float(t["sueldo_base"] or 0),
                                                      key=f"te_sue_{t['id']}")
                    col3, col4 = st.columns(2)
                    with col3:
                        t_fi_plan_edit = st.date_input(
                            "Inicio planilla",
                            value=t.get("fecha_inicio_planilla") or date.today(),
                            key=f"te_fiplan_{t['id']}"
                        )
                    with col4:
                        t_ff_plan_enabled_edit = st.checkbox(
                            "Tiene fin de planilla",
                            value=bool(t.get("fecha_fin_planilla")),
                            key=f"te_ffplan_enabled_{t['id']}"
                        )
                        t_ff_plan_edit = st.date_input(
                            "Fin planilla",
                            value=t.get("fecha_fin_planilla") or date.today(),
                            key=f"te_ffplan_{t['id']}"
                        ) if t_ff_plan_enabled_edit else None
                    col5, col6 = st.columns(2)
                    with col5:
                        t_fi_pen_edit = st.date_input(
                            "Inicio pensión",
                            value=t.get("fecha_inicio_pension") or date.today(),
                            key=f"te_fipen_{t['id']}"
                        )
                    with col6:
                        t_ff_enabled_edit = st.checkbox(
                            "Tiene fin de pensión",
                            value=bool(t.get("fecha_fin_pension")),
                            key=f"te_ffpen_enabled_{t['id']}"
                        )
                        t_ff_pen_edit = st.date_input(
                            "Fin pensión",
                            value=t.get("fecha_fin_pension") or date.today(),
                            key=f"te_ffpen_{t['id']}"
                        ) if t_ff_enabled_edit else None
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("💾 Actualizar", key=f"te_upd_{t['id']}"):
                            update_trabajador(
                                t["id"], t_nom_edit, t_dni_edit, t_car_edit, t_sue_edit,
                                t_fi_plan_edit, t_ff_plan_edit, t_fi_pen_edit, t_ff_pen_edit
                            )
                            st.success("Actualizado")
                            st.rerun()
                    with col_b:
                        btn_label = "Desactivar" if t["activo"] else "Activar"
                        if st.button(btn_label, key=f"te_tog_{t['id']}"):
                            toggle_trabajador(t["id"], not t["activo"])
                            st.rerun()
        else:
            st.info("No hay trabajadores registrados.")

    # ── Tab Borrar Datos ──────────────────────────────────────────────────
    with tab3:
        st.subheader("🗑️ Borrar Datos de Periodo")
        st.warning("⚠️ Esta acción eliminará permanentemente los datos del periodo seleccionado. Úsala para liberar espacio en la base de datos gratuita de Supabase.")

        col1, col2 = st.columns(2)
        with col1:
            bd_fi = st.date_input("Desde", key="bd_fi")
        with col2:
            bd_ff = st.date_input("Hasta", key="bd_ff")

        confirmar = st.text_input("Escribe **CONFIRMAR** para continuar", key="bd_confirm")
        if st.button("🗑️ Borrar Datos", type="primary", key="bd_btn"):
            if confirmar == "CONFIRMAR":
                borrar_datos_periodo(bd_fi, bd_ff)
                st.success(f"Datos del periodo {bd_fi} al {bd_ff} eliminados correctamente.")
            else:
                st.error("Debes escribir CONFIRMAR para proceder.")
