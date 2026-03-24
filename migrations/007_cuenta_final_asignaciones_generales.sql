-- ============================================================
-- MIGRACION 007 - ASIGNACIONES EXPLICITAS CUENTA FINAL
-- ============================================================

CREATE TABLE IF NOT EXISTS cuenta_final_planilla_asignaciones (
    id SERIAL PRIMARY KEY,
    cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
    planilla_id INTEGER NOT NULL REFERENCES planilla(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES usuarios(id),
    UNIQUE(planilla_id)
);

CREATE TABLE IF NOT EXISTS cuenta_final_adelanto_asignaciones (
    id SERIAL PRIMARY KEY,
    cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
    adelanto_id INTEGER NOT NULL REFERENCES adelantos(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES usuarios(id),
    UNIQUE(adelanto_id)
);

CREATE TABLE IF NOT EXISTS cuenta_final_pension_asignaciones (
    id SERIAL PRIMARY KEY,
    cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
    pension_id INTEGER NOT NULL REFERENCES pension(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES usuarios(id),
    UNIQUE(pension_id)
);

CREATE TABLE IF NOT EXISTS cuenta_final_inversion_asignaciones (
    id SERIAL PRIMARY KEY,
    cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
    inversion_id INTEGER NOT NULL REFERENCES inversiones(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES usuarios(id),
    UNIQUE(inversion_id)
);

CREATE TABLE IF NOT EXISTS cuenta_final_molienda_asignaciones (
    id SERIAL PRIMARY KEY,
    cuenta_final_id INTEGER NOT NULL REFERENCES cuenta_final(id) ON DELETE CASCADE,
    molienda_id INTEGER NOT NULL REFERENCES molienda(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES usuarios(id),
    UNIQUE(molienda_id)
);
