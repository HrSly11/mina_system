-- ============================================================
-- MIGRACION 003 - LUZ MENSUAL
-- ============================================================

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
);
