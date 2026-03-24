-- ============================================================
-- MIGRACION 008 - PERIODO GLOBAL SIDEBAR Y ASIGNACION DE LUZ
-- ============================================================

ALTER TABLE IF EXISTS cuenta_final_periodos
ALTER COLUMN fecha_fin DROP NOT NULL;

CREATE TABLE IF NOT EXISTS periodo_luz_asignaciones (
    id SERIAL PRIMARY KEY,
    periodo_id INTEGER NOT NULL REFERENCES cuenta_final_periodos(id) ON DELETE CASCADE,
    luz_id INTEGER NOT NULL REFERENCES luz_mensual(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES usuarios(id),
    UNIQUE(luz_id)
);
