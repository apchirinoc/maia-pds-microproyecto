-- ---------------------------------------------------------------------------
-- Auditoría de acciones sensibles
--
-- El nivel de riesgo ALTO asignado al sistema exige poder responder «quién
-- promovió qué modelo y cuándo» sin depender de los registros de la aplicación.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_events (
    id            uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id uuid         REFERENCES users(id) ON DELETE SET NULL,
    actor_label   varchar(120) NOT NULL,
    action        varchar(80)  NOT NULL,
    entity_type   varchar(60)  NOT NULL,
    entity_id     varchar(80),
    payload       jsonb        NOT NULL DEFAULT '{}'::jsonb,
    request_id    varchar(64),
    occurred_at   timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_events_entidad
    ON audit_events (entity_type, entity_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_events_fecha
    ON audit_events (occurred_at DESC);
