-- ============================================================
-- MIGRACION 006 - PERIODOS DE CUENTA FINAL Y ASIGNACION DE LUZ
-- ============================================================

CREATE TABLE IF NOT EXISTS cuenta_final_periodos (
    id SERIAL PRIMARY KEY,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    observacion TEXT,
    registrado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE cuenta_final
ADD COLUMN IF NOT EXISTS periodo_cuenta_id INTEGER REFERENCES cuenta_final_periodos(id);

CREATE INDEX IF NOT EXISTS idx_cuenta_final_periodo_cuenta_id
ON cuenta_final(periodo_cuenta_id);

CREATE TABLE IF NOT EXISTS cuenta_final_luz_asignaciones (
    id SERIAL PRIMARY KEY,
    cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
    luz_id INTEGER NOT NULL REFERENCES luz_mensual(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES usuarios(id),
    UNIQUE(luz_id)
);
