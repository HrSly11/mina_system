# ⛏️ Sistema Minero

Sistema de gestión para empresa minera. Administra planilla, pensión, cargas, cuentas por socio y cuenta final.

## Tecnologías
- **Frontend**: Streamlit
- **Backend**: Python 3.10+
- **Base de datos**: PostgreSQL (local) / Supabase (producción)

## Configuración rápida

```bash
python setup_local.py
streamlit run app.py
```

Ver `GUIA.md` para instrucciones completas de instalación local, Supabase y Streamlit Cloud.

## Roles
- **admin** — acceso total
- **socio** — planilla (ver), sus cuentas (editar), cuentas del otro socio (ver)
- **pensionista** — planilla + pensión (editar)

## Credenciales iniciales
- Usuario: `admin`
- Contraseña: `12345`
