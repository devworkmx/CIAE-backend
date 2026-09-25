-- Migración manual para el panel de superadministrador.
-- El proyecto usa Base.metadata.create_all() (sin Alembic), que SOLO crea
-- tablas nuevas y NUNCA modifica columnas de tablas ya existentes.
-- Corre este script UNA VEZ contra tu base de datos actual antes de
-- desplegar el backend actualizado.
--
-- Uso:
--   psql "TU_DATABASE_URL" -f migracion_superadmin.sql

BEGIN;

-- 1. Nuevas columnas de suscripción en tenants
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS estatus_suscripcion VARCHAR(20) NOT NULL DEFAULT 'activo',
    ADD COLUMN IF NOT EXISTS plan VARCHAR(50),
    ADD COLUMN IF NOT EXISTS fecha_vencimiento DATE,
    ADD COLUMN IF NOT EXISTS notas_pago TEXT,
    ADD COLUMN IF NOT EXISTS puede_emitir_certificados BOOLEAN NOT NULL DEFAULT TRUE;

-- 2. usuarios.tenant_id ahora es opcional (el superadmin no pertenece a un tenant)
ALTER TABLE usuarios
    ALTER COLUMN tenant_id DROP NOT NULL;

COMMIT;

-- Después de correr esto, crea tu primer superadmin con:
--   python create_superadmin.py
