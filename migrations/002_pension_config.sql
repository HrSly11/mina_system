-- ============================================================
-- MIGRACION 002 - CONFIGURACION DE PENSION
-- ============================================================

CREATE TABLE IF NOT EXISTS pension_config (
    id INTEGER PRIMARY KEY,
    monto_dia NUMERIC(10,2) NOT NULL DEFAULT 28.00,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES usuarios(id)
);

INSERT INTO pension_config (id, monto_dia)
VALUES (1, 28.00)
ON CONFLICT (id) DO NOTHING;
