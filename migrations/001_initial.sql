-- ============================================================
-- MIGRACIÓN COMPLETA - SISTEMA MINERO
-- Ejecutar en orden en PostgreSQL local y en Supabase
-- ============================================================

-- 1. USUARIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'socio', 'pensionista')),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. TRABAJADORES
CREATE TABLE IF NOT EXISTS trabajadores (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(100) NOT NULL,
    dni VARCHAR(20),
    cargo VARCHAR(50) DEFAULT 'Operario',
    sueldo_base NUMERIC(10,2) DEFAULT 0,
    fecha_inicio_planilla DATE DEFAULT CURRENT_DATE,
    fecha_fin_planilla DATE,
    fecha_inicio_pension DATE DEFAULT CURRENT_DATE,
    fecha_fin_pension DATE,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. PLANILLA (asistencia diaria por trabajador)
CREATE TABLE IF NOT EXISTS planilla (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER REFERENCES trabajadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente' CHECK (estado IN ('presente', 'falta', 'permiso', 'pendiente')),
    motivo TEXT,
    detalle TEXT,
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(trabajador_id, fecha)
);

-- 4. PENSIÓN (registro diario general)
CREATE TABLE IF NOT EXISTS pension (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER REFERENCES trabajadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL UNIQUE,
    estado VARCHAR(10) DEFAULT 'pendiente' CHECK (estado IN ('si', 'no', 'pendiente')),
    detalle TEXT,
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. COBROS DE PENSIÓN (registro mensual de cobro)
CREATE TABLE IF NOT EXISTS cobros_pension (
    id SERIAL PRIMARY KEY,
    mes INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    monto_por_dia NUMERIC(10,2) DEFAULT 28.00,
    total_cobrado NUMERIC(10,2),
    fecha_cobro DATE,
    observacion TEXT,
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(mes, anio)
);

-- 6. CARGAS (toneladas - disparador de planilla de pago)
CREATE TABLE IF NOT EXISTS cargas (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    toneladas NUMERIC(10,2) NOT NULL,
    bajada BOOLEAN DEFAULT FALSE,
    fecha_bajada DATE,
    observacion TEXT,
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_inicio_planilla DATE DEFAULT CURRENT_DATE;
ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_fin_planilla DATE;
ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_inicio_pension DATE DEFAULT CURRENT_DATE;
ALTER TABLE trabajadores ADD COLUMN IF NOT EXISTS fecha_fin_pension DATE;
ALTER TABLE cargas ADD COLUMN IF NOT EXISTS bajada BOOLEAN DEFAULT FALSE;
ALTER TABLE cargas ADD COLUMN IF NOT EXISTS fecha_bajada DATE;

ALTER TABLE pension ADD COLUMN IF NOT EXISTS trabajador_id INTEGER REFERENCES trabajadores(id) ON DELETE CASCADE;
ALTER TABLE pension DROP CONSTRAINT IF EXISTS pension_fecha_key;
CREATE UNIQUE INDEX IF NOT EXISTS ux_pension_trabajador_fecha ON pension(trabajador_id, fecha) WHERE trabajador_id IS NOT NULL;

-- 7. INVERSIONES (por socio)
CREATE TABLE IF NOT EXISTS inversiones (
    id SERIAL PRIMARY KEY,
    socio_id INTEGER REFERENCES usuarios(id),
    descripcion VARCHAR(255) NOT NULL,
    monto NUMERIC(10,2) NOT NULL,
    fecha DATE DEFAULT CURRENT_DATE,
    periodo_carga_id INTEGER REFERENCES cargas(id),
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 8. ADELANTOS (por socio a trabajador)
CREATE TABLE IF NOT EXISTS adelantos (
    id SERIAL PRIMARY KEY,
    socio_id INTEGER REFERENCES usuarios(id),
    trabajador_id INTEGER REFERENCES trabajadores(id),
    descripcion VARCHAR(255),
    monto NUMERIC(10,2) NOT NULL,
    fecha DATE DEFAULT CURRENT_DATE,
    periodo_carga_id INTEGER REFERENCES cargas(id),
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 9. MOLIENDA (gastos de transporte al molino, por socio)
CREATE TABLE IF NOT EXISTS molienda (
    id SERIAL PRIMARY KEY,
    socio_id INTEGER REFERENCES usuarios(id),
    descripcion VARCHAR(255) NOT NULL,
    monto NUMERIC(10,2) NOT NULL,
    fecha DATE DEFAULT CURRENT_DATE,
    periodo_carga_id INTEGER REFERENCES cargas(id),
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Extensiones para "Recorrido molienda" (registro único por socio/periodo)
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS cargadores_monto NUMERIC(10,2) DEFAULT 0;
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS bolquete_toneladas NUMERIC(10,2) DEFAULT 0;
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS bolquete_precio_ton NUMERIC(10,2) DEFAULT 0;
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS bolquete_total NUMERIC(10,2) DEFAULT 0;
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS molienda_toneladas NUMERIC(10,2) DEFAULT 0;
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS molienda_precio_ton NUMERIC(10,2) DEFAULT 0;
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS molienda_total NUMERIC(10,2) DEFAULT 0;

-- 10. CUENTA FINAL (ingresos de molienda y ganancia neta)
CREATE TABLE IF NOT EXISTS cuenta_final (
    id SERIAL PRIMARY KEY,
    periodo_carga_id INTEGER REFERENCES cargas(id),
    ingreso_molienda NUMERIC(10,2) DEFAULT 0,
    total_gastos_socio1 NUMERIC(10,2) DEFAULT 0,
    total_gastos_socio2 NUMERIC(10,2) DEFAULT 0,
    ganancia_neta NUMERIC(10,2) DEFAULT 0,
    observacion TEXT,
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 11. HISTORIAL DE ACCIONES
CREATE TABLE IF NOT EXISTS historial (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    nombre_usuario VARCHAR(100),
    accion VARCHAR(255) NOT NULL,
    modulo VARCHAR(50),
    detalle TEXT,
    fecha_hora TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- DATOS INICIALES
-- ============================================================

-- Usuario admin (password: 12345)
INSERT INTO usuarios (username, nombre_completo, password_hash, rol)
VALUES (
    'admin',
    'Administrador',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhcanFp8RRDlaVs7GovnBq',
    'admin'
) ON CONFLICT (username) DO NOTHING;

-- Nota: El hash anterior corresponde a '12345' con bcrypt
-- Si necesitas regenerarlo ejecuta en Python:
-- import bcrypt; print(bcrypt.hashpw(b'12345', bcrypt.gensalt()).decode())
