-- Compatible con instalaciones existentes. Aplicar con psql ON_ERROR_STOP=1.
BEGIN;
-- Los paquetes pueden identificarse por el ID completo de un logged model de MLflow.
-- La vista depende del tipo de version y se recrea en la misma transacción.
DROP VIEW IF EXISTS vw_model_registry_summary;
ALTER TABLE models ALTER COLUMN version TYPE text;
ALTER TABLE models ALTER COLUMN target_draft_version TYPE text;
CREATE VIEW vw_model_registry_summary AS
SELECT
    m.name AS production_model_name,
    m.version AS production_model_version,
    m.active_since,
    m.accuracy AS accuracy_test,
    (SELECT count(*) FROM models WHERE status = 'archived' AND deleted_at IS NULL) AS archived_versions,
    round((SELECT sum(size_mb) FROM models WHERE deleted_at IS NULL) / 1024.0, 2) AS storage_gb
FROM models m
WHERE m.status = 'production' AND m.deleted_at IS NULL;
-- La ausencia de una métrica no equivale a una medición de cero.
ALTER TABLE models ALTER COLUMN accuracy DROP NOT NULL;
ALTER TABLE models ALTER COLUMN f1_macro DROP NOT NULL;
ALTER TABLE models ALTER COLUMN size_mb DROP NOT NULL;
ALTER TABLE uploads ALTER COLUMN storage_path DROP NOT NULL;
-- Se permiten análisis repetidos del mismo archivo y con versiones diferentes.
ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_checksum_sha256_key;
CREATE INDEX IF NOT EXISTS ix_uploads_checksum ON uploads(checksum_sha256);
COMMIT;
