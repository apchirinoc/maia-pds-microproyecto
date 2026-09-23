-- Compatible con instalaciones existentes. Aplicar con psql ON_ERROR_STOP=1.
-- La ausencia de una métrica no equivale a una medición de cero.
ALTER TABLE models ALTER COLUMN accuracy DROP NOT NULL;
ALTER TABLE models ALTER COLUMN f1_macro DROP NOT NULL;
ALTER TABLE models ALTER COLUMN size_mb DROP NOT NULL;
ALTER TABLE uploads ALTER COLUMN storage_path DROP NOT NULL;
-- Se permiten análisis repetidos del mismo archivo y con versiones diferentes.
ALTER TABLE uploads DROP CONSTRAINT IF EXISTS uploads_checksum_sha256_key;
CREATE INDEX IF NOT EXISTS ix_uploads_checksum ON uploads(checksum_sha256);
