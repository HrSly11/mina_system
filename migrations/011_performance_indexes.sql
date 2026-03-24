-- ============================================================
-- 011_performance_indexes.sql
-- Indices para mejorar rendimiento global en consultas por periodo/fecha
-- NOTA: se crea cada indice solo si existen la tabla y columnas esperadas.
-- ============================================================

DO $$
BEGIN
    -- PLANILLA
    IF to_regclass('public.planilla') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'planilla' AND column_name = 'periodo_sistema_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'planilla' AND column_name = 'fecha') THEN
        CREATE INDEX IF NOT EXISTS idx_planilla_periodo_fecha
            ON planilla (periodo_sistema_id, fecha);
    END IF;

    IF to_regclass('public.planilla') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'planilla' AND column_name = 'trabajador_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'planilla' AND column_name = 'periodo_sistema_id') THEN
        CREATE INDEX IF NOT EXISTS idx_planilla_trabajador_periodo
            ON planilla (trabajador_id, periodo_sistema_id);
    END IF;

    -- PENSION
    IF to_regclass('public.pension') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pension' AND column_name = 'periodo_sistema_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pension' AND column_name = 'fecha') THEN
        CREATE INDEX IF NOT EXISTS idx_pension_periodo_fecha
            ON pension (periodo_sistema_id, fecha);
    END IF;

    IF to_regclass('public.pension') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pension' AND column_name = 'trabajador_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pension' AND column_name = 'periodo_sistema_id') THEN
        CREATE INDEX IF NOT EXISTS idx_pension_trabajador_periodo
            ON pension (trabajador_id, periodo_sistema_id);
    END IF;

    -- CARGAS
    IF to_regclass('public.cargas') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cargas' AND column_name = 'periodo_sistema_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cargas' AND column_name = 'fecha') THEN
        CREATE INDEX IF NOT EXISTS idx_cargas_periodo_fecha
            ON cargas (periodo_sistema_id, fecha);
    END IF;

    -- INVERSIONES / ADELANTOS / MOLIENDA
    IF to_regclass('public.inversiones') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'inversiones' AND column_name = 'periodo_sistema_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'inversiones' AND column_name = 'fecha') THEN
        CREATE INDEX IF NOT EXISTS idx_inversiones_periodo_fecha
            ON inversiones (periodo_sistema_id, fecha);
    END IF;

    IF to_regclass('public.adelantos') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'adelantos' AND column_name = 'periodo_sistema_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'adelantos' AND column_name = 'fecha') THEN
        CREATE INDEX IF NOT EXISTS idx_adelantos_periodo_fecha
            ON adelantos (periodo_sistema_id, fecha);
    END IF;

    IF to_regclass('public.molienda') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'molienda' AND column_name = 'periodo_sistema_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'molienda' AND column_name = 'fecha') THEN
        CREATE INDEX IF NOT EXISTS idx_molienda_periodo_fecha
            ON molienda (periodo_sistema_id, fecha);
    END IF;

    -- CUENTA FINAL TABLAS
    IF to_regclass('public.cuenta_final') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final' AND column_name = 'periodo_cuenta_id') THEN
        CREATE INDEX IF NOT EXISTS idx_cuenta_final_periodo
            ON cuenta_final (periodo_cuenta_id);
    END IF;

    IF to_regclass('public.cuenta_final_inversion_asignaciones') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_inversion_asignaciones' AND column_name = 'periodo_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_inversion_asignaciones' AND column_name = 'socio_id') THEN
        CREATE INDEX IF NOT EXISTS idx_cuenta_final_inversion_asig_periodo
            ON cuenta_final_inversion_asignaciones (periodo_id, socio_id);
    END IF;

    IF to_regclass('public.cuenta_final_adelanto_asignaciones') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_adelanto_asignaciones' AND column_name = 'periodo_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_adelanto_asignaciones' AND column_name = 'socio_id') THEN
        CREATE INDEX IF NOT EXISTS idx_cuenta_final_adelanto_asig_periodo
            ON cuenta_final_adelanto_asignaciones (periodo_id, socio_id);
    END IF;

    IF to_regclass('public.cuenta_final_planilla_asignaciones') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_planilla_asignaciones' AND column_name = 'periodo_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_planilla_asignaciones' AND column_name = 'trabajador_id') THEN
        CREATE INDEX IF NOT EXISTS idx_cuenta_final_planilla_asig_periodo
            ON cuenta_final_planilla_asignaciones (periodo_id, trabajador_id);
    END IF;

    IF to_regclass('public.cuenta_final_pension_asignaciones') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_pension_asignaciones' AND column_name = 'periodo_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_pension_asignaciones' AND column_name = 'trabajador_id') THEN
        CREATE INDEX IF NOT EXISTS idx_cuenta_final_pension_asig_periodo
            ON cuenta_final_pension_asignaciones (periodo_id, trabajador_id);
    END IF;

    IF to_regclass('public.cuenta_final_molienda_asignaciones') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_molienda_asignaciones' AND column_name = 'periodo_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cuenta_final_molienda_asignaciones' AND column_name = 'socio_id') THEN
        CREATE INDEX IF NOT EXISTS idx_cuenta_final_molienda_asig_periodo
            ON cuenta_final_molienda_asignaciones (periodo_id, socio_id);
    END IF;

    -- HISTORIAL
    IF to_regclass('public.historial') IS NOT NULL
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'historial' AND column_name = 'modulo')
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'historial' AND column_name = 'fecha_hora') THEN
        CREATE INDEX IF NOT EXISTS idx_historial_modulo_fecha
            ON historial (modulo, fecha_hora);
    END IF;
END
$$;
