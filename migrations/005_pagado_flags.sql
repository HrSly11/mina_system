-- ============================================================
-- MIGRACION 005 - CAMPOS PAGADO
-- ============================================================

ALTER TABLE IF EXISTS luz_mensual
ADD COLUMN IF NOT EXISTS pagado BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE IF EXISTS alquiler_cuarto
ADD COLUMN IF NOT EXISTS pagado BOOLEAN NOT NULL DEFAULT FALSE;
