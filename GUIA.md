# ============================================================
# GUÍA COMPLETA - SISTEMA MINERO
# ============================================================

## ÍNDICE
1. Requisitos previos
2. Instalación local (Windows)
3. Configuración de Supabase
4. Migraciones en Supabase
5. Despliegue en GitHub + Streamlit Cloud
6. Estructura del proyecto
7. Usuarios y roles
8. Solución de problemas

---

## 1. REQUISITOS PREVIOS

### En tu computadora local:
- Python 3.10 o superior → https://python.org/downloads
- PostgreSQL 14+ → https://www.postgresql.org/download/windows/
  - Durante la instalación pon contraseña: **12345**
  - Puerto por defecto: 5432
- Git → https://git-scm.com/downloads
- Cuenta en GitHub → https://github.com
- Cuenta en Supabase → https://supabase.com (gratis)
- Cuenta en Streamlit Cloud → https://share.streamlit.io (gratis)

---

## 2. INSTALACIÓN LOCAL (WINDOWS)

### Paso 1 – Descomprimir el proyecto
Extrae el .rar en una carpeta, por ejemplo:
```
C:\proyectos\mina_system\
```

### Paso 2 – Abrir terminal en la carpeta del proyecto
```powershell
cd C:\proyectos\mina_system
```

### Paso 3 – Crear entorno virtual (recomendado)
```powershell
python -m venv venv
venv\Scripts\activate
```
En Mac/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Paso 4 – Ejecutar el setup automático
Este script instala dependencias, crea la BD y corre las migraciones:
```powershell
python setup_local.py
```

Si hay algún error con la BD, puedes hacerlo manualmente (Paso 5).

### Paso 5 – Setup manual de la BD (si el automático falla)
Abre pgAdmin o psql y ejecuta:
```sql
CREATE DATABASE mina_db;
```
Luego ejecuta el archivo de migraciones:
```powershell
psql -U postgres -d mina_db -f migrations/001_initial.sql
```
(Te pedirá la contraseña: **12345**)

### Paso 6 – Iniciar la aplicación
```powershell
streamlit run app.py
```
Abre tu navegador en: **http://localhost:8501**

### Credenciales iniciales:
| Campo    | Valor  |
|----------|--------|
| Usuario  | admin  |
| Password | 12345  |

---

## 3. CONFIGURACIÓN DE SUPABASE

### Paso 1 – Crear proyecto en Supabase
1. Ve a https://supabase.com y haz login
2. Clic en "New Project"
3. Nombre: `mina-system` (o el que prefieras)
4. Contraseña de la BD: pon una segura (guárdala bien)
5. Región: South America (São Paulo) – la más cercana a Perú
6. Clic en "Create new project" y espera ~2 minutos

### Paso 2 – Obtener la cadena de conexión
1. En tu proyecto Supabase, ve a **Settings → Database**
2. Busca la sección **"Connection string"**
3. Selecciona el tipo **URI**
4. Copia la cadena, se verá así:
   ```
   postgresql://postgres:[TU-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
5. Reemplaza `[TU-PASSWORD]` con la contraseña que pusiste al crear el proyecto

### Paso 3 – Ejecutar migraciones en Supabase
1. En tu proyecto Supabase, ve a **SQL Editor**
2. Clic en "New query"
3. Copia y pega todo el contenido de `migrations/001_initial.sql`
4. Clic en **"Run"** (o Ctrl+Enter)
5. Verás los mensajes de éxito en el panel inferior

### Paso 4 – Verificar las tablas
Ve a **Table Editor** y deberías ver:
- usuarios
- trabajadores
- planilla
- pension
- cobros_pension
- cargas
- inversiones
- adelantos
- molienda
- cuenta_final
- historial

---

## 4. CONFIGURAR VARIABLES PARA SUPABASE EN LOCAL (PRUEBA)

Para probar con Supabase desde tu PC local:

1. Edita el archivo `.env`:
```
DATABASE_URL=postgresql://postgres:[TU-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
```

2. Reinicia streamlit:
```powershell
streamlit run app.py
```

---

## 5. DESPLIEGUE EN GITHUB + STREAMLIT CLOUD

### Paso 1 – Crear repositorio en GitHub
1. Ve a https://github.com/new
2. Nombre: `mina-system` (o el que prefieras)
3. Privado (recomendado para datos del negocio)
4. NO marques "Add a README" (ya tienes uno)
5. Clic en "Create repository"

### Paso 2 – Subir código a GitHub
En la terminal dentro de la carpeta del proyecto:
```powershell
git init
git add .
git commit -m "Initial commit - Sistema Minero"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/mina-system.git
git push -u origin main
```
(Reemplaza `TU-USUARIO` con tu usuario de GitHub)

### Paso 3 – Desplegar en Streamlit Cloud
1. Ve a https://share.streamlit.io
2. Haz login con tu cuenta de GitHub
3. Clic en **"New app"**
4. Selecciona tu repositorio `mina-system`
5. Branch: `main`
6. Main file path: `app.py`
7. Clic en **"Advanced settings"**

### Paso 4 – Configurar Secrets en Streamlit Cloud
En "Advanced settings" → "Secrets", pega esto:
```toml
[database]
url = "postgresql://postgres:[TU-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres"

[app]
secret_key = "mina_secret_2024_pon_algo_unico_aqui"
```
(Reemplaza con tu cadena de conexión real de Supabase)

8. Clic en **"Deploy!"**
9. Espera 2-3 minutos a que despliegue

Tu app estará en: `https://TU-USUARIO-mina-system.streamlit.app`

---

## 6. ESTRUCTURA DEL PROYECTO

```
mina_system/
│
├── app.py                    # Punto de entrada, login y router
│
├── modules/                  # Módulos por funcionalidad
│   ├── planilla.py           # Asistencia diaria de trabajadores
│   ├── pension.py            # Registro diario de pensión + cobros
│   ├── cargas.py             # Registro de toneladas (periodos)
│   ├── sacar_cuentas.py      # Las 4 partes: inversión, adelanto, planilla, molienda
│   ├── cuenta_final.py       # Cuenta final + ganancia neta
│   ├── historial_ui.py       # Historial de acciones
│   └── permisos.py           # Admin: usuarios, trabajadores, borrar datos
│
├── utils/                    # Utilidades compartidas
│   ├── db.py                 # Conexión y queries a PostgreSQL
│   ├── auth.py               # Login, roles, contraseñas
│   ├── historial.py          # Registro de acciones
│   └── exports.py            # Exportar a PDF y Excel
│
├── migrations/
│   └── 001_initial.sql       # Creación de todas las tablas + usuario admin
│
├── .streamlit/
│   ├── config.toml           # Tema visual dorado/oscuro
│   └── secrets.toml.example  # Ejemplo de secrets para Streamlit Cloud
│
├── requirements.txt          # Dependencias Python
├── .env.example              # Ejemplo de variables de entorno
├── .gitignore                # Archivos a ignorar en git
├── setup_local.py            # Script de setup automático local
└── GUIA.md                   # Este archivo
```

---

## 7. USUARIOS Y ROLES

| Rol         | Acceso                                                                 |
|-------------|------------------------------------------------------------------------|
| admin       | Todo: usuarios, trabajadores, borrar datos, ver todo                   |
| socio       | Planilla (ver), pensión (ver), su propio Sacar Cuentas (editar), ver cuentas del otro socio (solo lectura), Cuenta Final |
| pensionista | Planilla (editar), Pensión (editar), Cuentas-Pensión (ver)             |

### Crear usuarios de socios (desde el admin):
1. Login como admin / 12345
2. Ve a ⚙️ Permisos / Admin
3. Tab "Usuarios" → "Crear Nuevo Usuario"
4. Nombre: `Máximo Muñoz`, Username: `maximo`, Rol: `socio`
5. Repetir para `Luis Polo`, username: `luis`, rol: `socio`
6. Crear pensionista con rol: `pensionista`

### Crear trabajadores:
1. Ve a ⚙️ Permisos / Admin → Tab "Trabajadores"
2. Agregar cada trabajador con su nombre, DNI, cargo y sueldo por día

---

## 8. FLUJO DE USO RECOMENDADO

### Al inicio de cada periodo:
1. Registrar la carga anterior en **⛏️ Cargas** (esto crea el periodo)
2. El sistema automáticamente usará ese periodo para calcular planilla y cuentas

### Día a día:
1. **Pensionista** registra la planilla diaria (presente/falta/permiso)
2. **Pensionista** registra si hubo pensión ese día (sí/no)
3. Los socios registran sus **inversiones**, **adelantos** y **molienda** según corresponda

### Al hacer la descarga (≈50 ton):
1. Registrar en **Cargas** la fecha y toneladas
2. Ir a **Sacar Cuentas** de cada socio y revisar los totales
3. Ir a **Cuenta Final**, ingresar el ingreso obtenido
4. El sistema calcula automáticamente la ganancia neta
5. Exportar en PDF o Excel para entregar a los trabajadores

---

## 9. SOLUCIÓN DE PROBLEMAS

### Error: "No module named psycopg2"
```powershell
pip install psycopg2-binary
```

### Error de conexión a PostgreSQL local
- Verifica que PostgreSQL esté corriendo
- Abre "Servicios" en Windows y busca "postgresql"
- Verifica que la contraseña sea `12345`
- Verifica que el puerto sea `5432`

### Error en Streamlit Cloud: "cannot connect to database"
- Verifica que los Secrets estén bien escritos en Streamlit Cloud
- Verifica que la cadena de conexión de Supabase sea correcta
- En Supabase → Settings → Database → Connection string

### El hash de la contraseña admin no funciona
Ejecuta este script para regenerar el hash:
```python
import bcrypt
password = b"12345"
hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
print(hashed)
```
Luego actualiza en la tabla usuarios:
```sql
UPDATE usuarios SET password_hash = 'NUEVO_HASH' WHERE username = 'admin';
```

### Supabase gratis se llena
Usa la función **Borrar Datos** en ⚙️ Permisos → "Borrar Datos":
- Selecciona el rango de fechas de periodos ya cerrados
- Escribe CONFIRMAR y borra

El plan gratuito de Supabase tiene 500MB de almacenamiento, suficiente para meses de operación normal.

---

## 10. ACTUALIZAR LA APP DESPUÉS DE CAMBIOS

Cuando hagas cambios al código:
```powershell
git add .
git commit -m "descripción del cambio"
git push origin main
```
Streamlit Cloud detecta el push y redespliega automáticamente en ~1 minuto.

---

*Sistema Minero v1.0 — Desarrollado con Python + Streamlit + PostgreSQL*
