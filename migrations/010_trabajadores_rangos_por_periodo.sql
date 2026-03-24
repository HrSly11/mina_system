-- ============================================================
-- MIGRACION 010 - RANGOS DE TRABAJADORES POR PERIODO SIDEBAR
-- ============================================================

CREATE TABLE IF NOT EXISTS trabajador_planilla_periodo_config (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER NOT NULL REFERENCES trabajadores(id) ON DELETE CASCADE,
    periodo_id INTEGER NOT NULL REFERENCES cuenta_final_periodos(id) ON DELETE CASCADE,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(trabajador_id, periodo_id)
);

CREATE TABLE IF NOT EXISTS trabajador_pension_periodo_config (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER NOT NULL REFERENCES trabajadores(id) ON DELETE CASCADE,
    periodo_id INTEGER NOT NULL REFERENCES cuenta_final_periodos(id) ON DELETE CASCADE,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(trabajador_id, periodo_id)
);

CREATE INDEX IF NOT EXISTS idx_tp_config_periodo ON trabajador_planilla_periodo_config(periodo_id);
CREATE INDEX IF NOT EXISTS idx_tpen_config_periodo ON trabajador_pension_periodo_config(periodo_id);
