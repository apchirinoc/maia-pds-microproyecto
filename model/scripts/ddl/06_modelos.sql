-- ---------------------------------------------------------------------------
-- Registro de modelos
--
-- Con MLflow activo (sección 12 del plan) esta tabla es una PROYECCIÓN DE
-- LECTURA: la fuente de verdad del ciclo de vida es el Model Registry, y aquí
-- se guardan punteros más las métricas desnormalizadas que el panel necesita
-- leer en milisegundos.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS models (
    id                   uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                 varchar(80)   NOT NULL UNIQUE,
    name                 varchar(80)   NOT NULL,
    version              varchar(20)   NOT NULL,
    architecture         varchar(80)   NOT NULL,
    accuracy             numeric(5,2)  NOT NULL CHECK (accuracy BETWEEN 0 AND 100),
    f1_macro             numeric(6,4)  NOT NULL CHECK (f1_macro BETWEEN 0 AND 1),
    precision_macro      numeric(6,4)  CHECK (precision_macro BETWEEN 0 AND 1),
    recall_macro         numeric(6,4)  CHECK (recall_macro BETWEEN 0 AND 1),
    auc                  numeric(6,4)  CHECK (auc BETWEEN 0 AND 1),
    size_mb              numeric(9,2)  NOT NULL CHECK (size_mb > 0),
    status               model_status   NOT NULL DEFAULT 'validation',
    weights_file_name    varchar(160)  NOT NULL,
    weights_sha256       char(64),
    training_images      integer       CHECK (training_images >= 0),
    test_images          integer       CHECK (test_images >= 0),
    active_since         date,
    target_draft_version varchar(20),
    previous_model_id    uuid          REFERENCES models(id) ON DELETE SET NULL,
    -- Punteros a MLflow. Vacíos mientras no exista un run registrado.
    mlflow_model_name    varchar(120),
    mlflow_model_version integer,
    mlflow_run_id        char(32),
    mlflow_artifact_uri  text,
    dataset_snapshot_id  uuid,
    created_by           uuid          REFERENCES users(id) ON DELETE SET NULL,
    created_at           timestamptz   NOT NULL DEFAULT now(),
    updated_at           timestamptz   NOT NULL DEFAULT now(),
    deleted_at           timestamptz,
    CONSTRAINT uq_models_nombre_version UNIQUE (name, version)
);

DROP TRIGGER IF EXISTS trg_models_updated_at ON models;
CREATE TRIGGER trg_models_updated_at
    BEFORE UPDATE ON models
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Como máximo un modelo en producción. Lo impone la base de datos y no la
-- aplicación: si dos despliegues concurrentes intentan promover a la vez, uno
-- falla en vez de dejar el sistema con dos campeones.
CREATE UNIQUE INDEX IF NOT EXISTS uq_models_un_solo_produccion
    ON models ((status))
    WHERE status = 'production' AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS model_class_metrics (
    model_id   uuid         NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    class_code tumor_class  NOT NULL REFERENCES tumor_classes(code) ON DELETE RESTRICT,
    f1         numeric(6,4) NOT NULL CHECK (f1 BETWEEN 0 AND 1),
    precision  numeric(6,4) CHECK (precision BETWEEN 0 AND 1),
    recall     numeric(6,4) CHECK (recall BETWEEN 0 AND 1),
    support    integer      CHECK (support >= 0),
    PRIMARY KEY (model_id, class_code)
);

COMMENT ON TABLE model_class_metrics IS
    'Métricas por clase. Un F1 macro alto puede esconder una clase hundida; '
    'por eso el criterio de promoción exige F1 por clase, no sólo el macro.';

CREATE TABLE IF NOT EXISTS model_confusion_cells (
    model_id        uuid        NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    actual_class    tumor_class NOT NULL REFERENCES tumor_classes(code) ON DELETE RESTRICT,
    predicted_class tumor_class NOT NULL REFERENCES tumor_classes(code) ON DELETE RESTRICT,
    cell_count      integer     NOT NULL CHECK (cell_count >= 0),
    PRIMARY KEY (model_id, actual_class, predicted_class)
);

CREATE TABLE IF NOT EXISTS model_deployments (
    id            uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id      uuid             NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    event_type    deployment_event NOT NULL,
    event_at      timestamptz      NOT NULL DEFAULT now(),
    actor_user_id uuid             REFERENCES users(id) ON DELETE SET NULL,
    -- Se conserva el nombre en texto: si el usuario se da de baja, la bitácora
    -- debe seguir diciendo quién desplegó.
    actor_label   varchar(120)     NOT NULL,
    notes         text
);

CREATE INDEX IF NOT EXISTS ix_model_deployments_modelo_fecha
    ON model_deployments (model_id, event_at DESC);
