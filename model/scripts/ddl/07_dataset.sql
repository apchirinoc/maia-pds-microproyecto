-- ---------------------------------------------------------------------------
-- Dataset e instantáneas reproducibles
--
-- Sin congelar la composición del dataset, cualquier reentrenamiento posterior
-- sería irreproducible: el conjunto sería un blanco móvil en cuanto se
-- promueve una carga de usuario. Ver patrón «Repeatable Splitting».
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dataset_images (
    id            uuid                 PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Identificador estable: es lo que se hashea para decidir la partición, de
    -- modo que una imagen cae siempre del mismo lado aunque crezca el dataset.
    stable_id     varchar(80)          NOT NULL UNIQUE,
    class_code    tumor_class          NOT NULL REFERENCES tumor_classes(code) ON DELETE RESTRICT,
    split         dataset_split        NOT NULL,
    file_name     varchar(160)         NOT NULL,
    storage_path  text                 NOT NULL,
    checksum_sha256 char(64),
    source        dataset_image_source NOT NULL DEFAULT 'kaggle',
    origin_upload_id uuid,
    is_showcase   boolean              NOT NULL DEFAULT false,
    added_at      timestamptz          NOT NULL DEFAULT now(),
    deleted_at    timestamptz
);

COMMENT ON COLUMN dataset_images.is_showcase IS
    'Marca la muestra que el panel enseña para esa clase (una por clase).';

CREATE INDEX IF NOT EXISTS ix_dataset_images_clase_split
    ON dataset_images (class_code, split) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_dataset_images_showcase_por_clase
    ON dataset_images (class_code)
    WHERE is_showcase AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS dataset_snapshots (
    id            uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_code varchar(40)  NOT NULL UNIQUE,
    -- Huella SHA-256 del contenido: dos instantáneas con los mismos
    -- identificadores y la misma configuración comparten huella.
    fingerprint   char(64)     NOT NULL,
    split_salt    varchar(80)  NOT NULL,
    train_fraction numeric(4,3) NOT NULL CHECK (train_fraction > 0 AND train_fraction < 1),
    total_images  integer      NOT NULL CHECK (total_images >= 0),
    train_images  integer      NOT NULL CHECK (train_images >= 0),
    test_images   integer      NOT NULL CHECK (test_images >= 0),
    reason        text,
    created_by    uuid         REFERENCES users(id) ON DELETE SET NULL,
    created_at    timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_dataset_snapshots_totales CHECK (train_images + test_images = total_images)
);

CREATE TABLE IF NOT EXISTS dataset_snapshot_items (
    snapshot_id      uuid          NOT NULL REFERENCES dataset_snapshots(id) ON DELETE CASCADE,
    dataset_image_id uuid          NOT NULL REFERENCES dataset_images(id) ON DELETE RESTRICT,
    split            dataset_split NOT NULL,
    PRIMARY KEY (snapshot_id, dataset_image_id)
);

COMMENT ON TABLE dataset_snapshot_items IS
    'Composición exacta de cada instantánea. El guard anti-fuga necesita los '
    'identificadores imagen a imagen, no sólo los conteos.';

-- Se declara aquí porque models se crea antes que dataset_snapshots.
ALTER TABLE models
    DROP CONSTRAINT IF EXISTS fk_models_dataset_snapshot;
ALTER TABLE models
    ADD CONSTRAINT fk_models_dataset_snapshot
    FOREIGN KEY (dataset_snapshot_id) REFERENCES dataset_snapshots(id) ON DELETE SET NULL;
