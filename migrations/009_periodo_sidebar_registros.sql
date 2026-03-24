-- ============================================================
-- MIGRACION 009 - VINCULO DE REGISTROS AL PERIODO DEL SIDEBAR
-- ============================================================

ALTER TABLE planilla ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id);
ALTER TABLE pension ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id);
ALTER TABLE inversiones ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id);
ALTER TABLE adelantos ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id);
ALTER TABLE molienda ADD COLUMN IF NOT EXISTS periodo_sistema_id INTEGER REFERENCES cuenta_final_periodos(id);

ALTER TABLE planilla DROP CONSTRAINT IF EXISTS planilla_trabajador_id_fecha_key;
DROP INDEX IF EXISTS ux_pension_trabajador_fecha;

CREATE UNIQUE INDEX IF NOT EXISTS ux_planilla_trabajador_fecha_periodo
ON planilla(trabajador_id, fecha, periodo_sistema_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pension_trabajador_fecha_periodo
ON pension(trabajador_id, fecha, periodo_sistema_id)
WHERE trabajador_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_planilla_periodo_sistema_id ON planilla(periodo_sistema_id);
CREATE INDEX IF NOT EXISTS idx_pension_periodo_sistema_id ON pension(periodo_sistema_id);
CREATE INDEX IF NOT EXISTS idx_inversiones_periodo_sistema_id ON inversiones(periodo_sistema_id);
CREATE INDEX IF NOT EXISTS idx_adelantos_periodo_sistema_id ON adelantos(periodo_sistema_id);
CREATE INDEX IF NOT EXISTS idx_molienda_periodo_sistema_id ON molienda(periodo_sistema_id);
