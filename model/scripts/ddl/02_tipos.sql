-- ---------------------------------------------------------------------------
-- Tipos enumerados del dominio
--
-- Cada literal coincide exactamente con su equivalente en TypeScript
-- (web/src/types/) y en Python (api/app/schemas/, ml_project/pipelines/config.py).
-- ---------------------------------------------------------------------------

DO $$ BEGIN
    CREATE TYPE tumor_class AS ENUM ('glioma', 'meningioma', 'pituitary', 'healthy');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE upload_status AS ENUM ('validated', 'pending', 'discarded');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- De menor a mayor nivel de evidencia. La anatomía patológica es el patrón oro;
-- una lectura de especialista, la evidencia más débil que se acepta.
DO $$ BEGIN
    CREATE TYPE ground_truth_source AS ENUM (
        'specialist_review', 'radiology_report', 'follow_up_imaging', 'histopathology'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE model_status AS ENUM ('production', 'archived', 'validation', 'baseline');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE deployment_event AS ENUM (
        'trainingCompleted', 'validated', 'deployedToProduction', 'reverted', 'archived'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE dataset_split AS ENUM ('train', 'test');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE dataset_image_source AS ENUM ('kaggle', 'user_upload');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
