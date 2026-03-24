-- ============================================================
-- MIGRACION 004 - ALQUILER DE CUARTO
-- ============================================================

CREATE TABLE IF NOT EXISTS alquiler_cuarto (
    id SERIAL PRIMARY KEY,
    periodo_carga_id INTEGER REFERENCES cargas(id),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('individual', 'compartido', 'sin_pago')),
    referencia VARCHAR(120),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    monto_total NUMERIC(10,2) NOT NULL DEFAULT 0,
    sin_pago BOOLEAN NOT NULL DEFAULT FALSE,
    observacion TEXT,
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alquiler_cuarto_trabajadores (
    id SERIAL PRIMARY KEY,
    alquiler_id INTEGER NOT NULL REFERENCES alquiler_cuarto(id) ON DELETE CASCADE,
    trabajador_id INTEGER NOT NULL REFERENCES trabajadores(id) ON DELETE CASCADE,
    UNIQUE(alquiler_id, trabajador_id)
);
