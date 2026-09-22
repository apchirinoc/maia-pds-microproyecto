-- ---------------------------------------------------------------------------
-- Cargas de usuarios, predicciones y verdad de campo
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS uploads (
    id               uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Identificador visible en la interfaz (upl_9f31c4). Se separa del uuid
    -- para no exponer la clave interna.
    public_id        varchar(24)   NOT NULL UNIQUE,
    file_name        varchar(255)  NOT NULL,
    storage_path     text          NOT NULL,
    -- El binario NO vive en la base de datos: sólo su ruta y su hash.
    checksum_sha256  char(64)      NOT NULL UNIQUE,
    country_code     char(2)       NOT NULL REFERENCES countries(code) ON DELETE RESTRICT,
    status           upload_status NOT NULL DEFAULT 'pending',
    reviewed_by      uuid          REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at      timestamptz,
    added_to_dataset boolean       NOT NULL DEFAULT false,
    created_at       timestamptz   NOT NULL DEFAULT now(),
    updated_at       timestamptz   NOT NULL DEFAULT now(),
    deleted_at       timestamptz,
    CONSTRAINT ck_uploads_revision_completa
        CHECK ((reviewed_by IS NULL) = (reviewed_at IS NULL))
);

DROP TRIGGER IF EXISTS trg_uploads_updated_at ON uploads;
CREATE TRIGGER trg_uploads_updated_at
    BEFORE UPDATE ON uploads
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS ix_uploads_fecha
    ON uploads (created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_uploads_pais
    ON uploads (country_code) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_uploads_estado
    ON uploads (status) WHERE deleted_at IS NULL;

-- Cierra el ciclo: una carga promovida al dataset queda enlazada con su imagen.
ALTER TABLE dataset_images
    DROP CONSTRAINT IF EXISTS fk_dataset_images_origen;
ALTER TABLE dataset_images
    ADD CONSTRAINT fk_dataset_images_origen
    FOREIGN KEY (origin_upload_id) REFERENCES uploads(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS predictions (
    id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id       uuid         NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    model_id        uuid         NOT NULL REFERENCES models(id) ON DELETE RESTRICT,
    predicted_class tumor_class  NOT NULL REFERENCES tumor_classes(code) ON DELETE RESTRICT,
    confidence      numeric(5,2) NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    latency_ms      integer      CHECK (latency_ms >= 0),
    preprocess_label varchar(80) NOT NULL,
    -- Huella del preprocesamiento realmente aplicado. Permite descartar
    -- métricas producidas con un preproceso distinto del actual.
    preprocess_fingerprint varchar(32),
    is_simulated    boolean      NOT NULL DEFAULT true,
    created_at      timestamptz  NOT NULL DEFAULT now()
);

-- Una predicción vigente por carga: es la que muestra el histórico.
CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_una_por_carga
    ON predictions (upload_id);

CREATE TABLE IF NOT EXISTS prediction_scores (
    prediction_id uuid         NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    class_code    tumor_class  NOT NULL REFERENCES tumor_classes(code) ON DELETE RESTRICT,
    confidence    numeric(5,2) NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    PRIMARY KEY (prediction_id, class_code)
);

COMMENT ON TABLE prediction_scores IS
    'Probabilidad por clase de cada predicción: lo que pinta la barra de '
    'confianza de la interfaz.';

CREATE TABLE IF NOT EXISTS ground_truth_diagnoses (
    id            uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id     uuid                NOT NULL REFERENCES uploads(id) ON DELETE RESTRICT,
    diagnosis     tumor_class         NOT NULL REFERENCES tumor_classes(code) ON DELETE RESTRICT,
    source        ground_truth_source NOT NULL,
    confirmed_by  varchar(160)        NOT NULL,
    confirmed_at  timestamptz         NOT NULL DEFAULT now(),
    notes         text,
    created_at    timestamptz         NOT NULL DEFAULT now(),
    updated_at    timestamptz         NOT NULL DEFAULT now(),
    -- Una confirmación corregida no se pisa: se marca y queda como historial.
    deleted_at    timestamptz
);

DROP TRIGGER IF EXISTS trg_ground_truth_updated_at ON ground_truth_diagnoses;
CREATE TRIGGER trg_ground_truth_updated_at
    BEFORE UPDATE ON ground_truth_diagnoses
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Exactamente una confirmación vigente por carga. Es lo que permite que el
-- frontend vea un único `groundTruth | null` sin ambigüedad.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ground_truth_vigente_por_carga
    ON ground_truth_diagnoses (upload_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_ground_truth_diagnostico_vigente
    ON ground_truth_diagnoses (diagnosis) WHERE deleted_at IS NULL;
