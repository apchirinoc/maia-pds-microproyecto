# Diccionario de datos — BrainNeuroScan

> **GENERADO** por `model/tools/generar_diccionario.py` leyendo el catálogo
> de PostgreSQL. Describe el esquema que existe realmente, no el que
> describen los ficheros DDL. Para regenerarlo: `docker compose up -d` y
> `python tools/generar_diccionario.py`.

## Tipos enumerados

| Tipo | Valores admitidos |
|---|---|
| `dataset_image_source` | `kaggle`, `user_upload` |
| `dataset_split` | `train`, `test` |
| `deployment_event` | `trainingCompleted`, `validated`, `deployedToProduction`, `reverted`, `archived` |
| `ground_truth_source` | `specialist_review`, `radiology_report`, `follow_up_imaging`, `histopathology` |
| `model_status` | `production`, `archived`, `validation`, `baseline` |
| `tumor_class` | `glioma`, `meningioma`, `pituitary`, `healthy` |
| `upload_status` | `validated`, `pending`, `discarded` |

## `audit_events`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `actor_user_id` | `uuid` | Sí | — | — | (actor_user_id) → users(id) ON DELETE SET NULL |
| `actor_label` | `character varying(120)` | No | — | — | — |
| `action` | `character varying(80)` | No | — | — | — |
| `entity_type` | `character varying(60)` | No | — | — | — |
| `entity_id` | `character varying(80)` | Sí | — | — | — |
| `payload` | `jsonb` | No | `'{}'::jsonb` | — | — |
| `request_id` | `character varying(64)` | Sí | — | — | — |
| `occurred_at` | `timestamp with time zone` | No | `now()` | — | — |

## `countries`

Países de origen declarados en las cargas. Las coordenadas alimentan el mapa del panel.

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `code` | `character(2)` | No | — | — | PK |
| `name` | `character varying(120)` | No | — | — | — |
| `name_es` | `character varying(120)` | No | — | — | — |
| `latitude` | `numeric(8,5)` | No | — | — | CHECK |
| `longitude` | `numeric(8,5)` | No | — | — | CHECK |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |

## `dataset_images`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `stable_id` | `character varying(80)` | No | — | — | UNIQUE |
| `class_code` | `tumor_class` | No | — | — | (class_code) → tumor_classes(code) ON DELETE RESTRICT |
| `split` | `dataset_split` | No | — | — | — |
| `file_name` | `character varying(160)` | No | — | — | — |
| `storage_path` | `text` | No | — | — | — |
| `checksum_sha256` | `character(64)` | Sí | — | — | — |
| `source` | `dataset_image_source` | No | `'kaggle'::dataset_image_source` | — | — |
| `origin_upload_id` | `uuid` | Sí | — | — | (origin_upload_id) → uploads(id) ON DELETE SET NULL |
| `is_showcase` | `boolean` | No | `false` | Marca la muestra que el panel enseña para esa clase (una por clase). | — |
| `added_at` | `timestamp with time zone` | No | `now()` | — | — |
| `deleted_at` | `timestamp with time zone` | Sí | — | — | — |

## `dataset_snapshot_items`

Composición exacta de cada instantánea. El guard anti-fuga necesita los identificadores imagen a imagen, no sólo los conteos.

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `snapshot_id` | `uuid` | No | — | — | (snapshot_id) → dataset_snapshots(id) ON DELETE CASCADE · PK |
| `dataset_image_id` | `uuid` | No | — | — | (dataset_image_id) → dataset_images(id) ON DELETE RESTRICT · PK |
| `split` | `dataset_split` | No | — | — | — |

## `dataset_snapshots`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `snapshot_code` | `character varying(40)` | No | — | — | UNIQUE |
| `fingerprint` | `character(64)` | No | — | — | — |
| `split_salt` | `character varying(80)` | No | — | — | — |
| `train_fraction` | `numeric(4,3)` | No | — | — | CHECK |
| `total_images` | `integer` | No | — | — | CHECK |
| `train_images` | `integer` | No | — | — | CHECK |
| `test_images` | `integer` | No | — | — | CHECK |
| `reason` | `text` | Sí | — | — | — |
| `created_by` | `uuid` | Sí | — | — | (created_by) → users(id) ON DELETE SET NULL |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |

## `ground_truth_diagnoses`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `upload_id` | `uuid` | No | — | — | (upload_id) → uploads(id) ON DELETE RESTRICT |
| `diagnosis` | `tumor_class` | No | — | — | (diagnosis) → tumor_classes(code) ON DELETE RESTRICT |
| `source` | `ground_truth_source` | No | — | — | — |
| `confirmed_by` | `character varying(160)` | No | — | — | — |
| `confirmed_at` | `timestamp with time zone` | No | `now()` | — | — |
| `notes` | `text` | Sí | — | — | — |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |
| `updated_at` | `timestamp with time zone` | No | `now()` | — | — |
| `deleted_at` | `timestamp with time zone` | Sí | — | — | — |

## `model_class_metrics`

Métricas por clase. Un F1 macro alto puede esconder una clase hundida; por eso el criterio de promoción exige F1 por clase, no sólo el macro.

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `model_id` | `uuid` | No | — | — | (model_id) → models(id) ON DELETE CASCADE · PK |
| `class_code` | `tumor_class` | No | — | — | (class_code) → tumor_classes(code) ON DELETE RESTRICT · PK |
| `f1` | `numeric(6,4)` | No | — | — | CHECK |
| `precision` | `numeric(6,4)` | Sí | — | — | CHECK |
| `recall` | `numeric(6,4)` | Sí | — | — | CHECK |
| `support` | `integer` | Sí | — | — | CHECK |

## `model_confusion_cells`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `model_id` | `uuid` | No | — | — | (model_id) → models(id) ON DELETE CASCADE · PK |
| `actual_class` | `tumor_class` | No | — | — | (actual_class) → tumor_classes(code) ON DELETE RESTRICT · PK |
| `predicted_class` | `tumor_class` | No | — | — | (predicted_class) → tumor_classes(code) ON DELETE RESTRICT · PK |
| `cell_count` | `integer` | No | — | — | CHECK |

## `model_deployments`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `model_id` | `uuid` | No | — | — | (model_id) → models(id) ON DELETE CASCADE |
| `event_type` | `deployment_event` | No | — | — | — |
| `event_at` | `timestamp with time zone` | No | `now()` | — | — |
| `actor_user_id` | `uuid` | Sí | — | — | (actor_user_id) → users(id) ON DELETE SET NULL |
| `actor_label` | `character varying(120)` | No | — | — | — |
| `notes` | `text` | Sí | — | — | — |

## `models`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `slug` | `character varying(80)` | No | — | — | UNIQUE |
| `name` | `character varying(80)` | No | — | — | UNIQUE |
| `version` | `character varying(20)` | No | — | — | UNIQUE |
| `architecture` | `character varying(80)` | No | — | — | — |
| `accuracy` | `numeric(5,2)` | No | — | — | CHECK |
| `f1_macro` | `numeric(6,4)` | No | — | — | CHECK |
| `precision_macro` | `numeric(6,4)` | Sí | — | — | CHECK |
| `recall_macro` | `numeric(6,4)` | Sí | — | — | CHECK |
| `auc` | `numeric(6,4)` | Sí | — | — | CHECK |
| `size_mb` | `numeric(9,2)` | No | — | — | CHECK |
| `status` | `model_status` | No | `'validation'::model_status` | — | — |
| `weights_file_name` | `character varying(160)` | No | — | — | — |
| `weights_sha256` | `character(64)` | Sí | — | — | — |
| `training_images` | `integer` | Sí | — | — | CHECK |
| `test_images` | `integer` | Sí | — | — | CHECK |
| `active_since` | `date` | Sí | — | — | — |
| `target_draft_version` | `character varying(20)` | Sí | — | — | — |
| `previous_model_id` | `uuid` | Sí | — | — | (previous_model_id) → models(id) ON DELETE SET NULL |
| `mlflow_model_name` | `character varying(120)` | Sí | — | — | — |
| `mlflow_model_version` | `integer` | Sí | — | — | — |
| `mlflow_run_id` | `character(32)` | Sí | — | — | — |
| `mlflow_artifact_uri` | `text` | Sí | — | — | — |
| `dataset_snapshot_id` | `uuid` | Sí | — | — | (dataset_snapshot_id) → dataset_snapshots(id) ON DELETE SET NULL |
| `created_by` | `uuid` | Sí | — | — | (created_by) → users(id) ON DELETE SET NULL |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |
| `updated_at` | `timestamp with time zone` | No | `now()` | — | — |
| `deleted_at` | `timestamp with time zone` | Sí | — | — | — |

## `prediction_scores`

Probabilidad por clase de cada predicción: lo que pinta la barra de confianza de la interfaz.

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `prediction_id` | `uuid` | No | — | — | (prediction_id) → predictions(id) ON DELETE CASCADE · PK |
| `class_code` | `tumor_class` | No | — | — | (class_code) → tumor_classes(code) ON DELETE RESTRICT · PK |
| `confidence` | `numeric(5,2)` | No | — | — | CHECK |

## `predictions`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `upload_id` | `uuid` | No | — | — | (upload_id) → uploads(id) ON DELETE CASCADE |
| `model_id` | `uuid` | No | — | — | (model_id) → models(id) ON DELETE RESTRICT |
| `predicted_class` | `tumor_class` | No | — | — | (predicted_class) → tumor_classes(code) ON DELETE RESTRICT |
| `confidence` | `numeric(5,2)` | No | — | — | CHECK |
| `latency_ms` | `integer` | Sí | — | — | CHECK |
| `preprocess_label` | `character varying(80)` | No | — | — | — |
| `preprocess_fingerprint` | `character varying(32)` | Sí | — | — | — |
| `is_simulated` | `boolean` | No | `true` | — | — |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |

## `refresh_tokens`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `user_id` | `uuid` | No | — | — | (user_id) → users(id) ON DELETE CASCADE |
| `token_hash` | `character(64)` | No | — | — | UNIQUE |
| `issued_at` | `timestamp with time zone` | No | `now()` | — | CHECK |
| `expires_at` | `timestamp with time zone` | No | — | — | CHECK |
| `revoked_at` | `timestamp with time zone` | Sí | — | — | — |
| `user_agent` | `character varying(255)` | Sí | — | — | — |

## `roles`

Roles asignables a los usuarios de la plataforma.

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `code` | `character varying(32)` | No | — | — | UNIQUE |
| `name` | `character varying(80)` | No | — | — | — |
| `description` | `text` | Sí | — | — | — |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |

## `tumor_classes`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `code` | `tumor_class` | No | — | — | PK |
| `label_es` | `character varying(60)` | No | — | — | — |
| `label_en` | `character varying(60)` | No | — | — | — |
| `color_hex` | `character(7)` | No | — | — | CHECK |
| `display_order` | `smallint` | No | — | — | UNIQUE |
| `is_tumor` | `boolean` | No | — | Distingue las tres clases tumorales de healthy. Sostiene el criterio de promoción «recall tumor vs healthy», que es el dominante en un dominio clínico. | — |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |

## `uploads`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `public_id` | `character varying(24)` | No | — | — | UNIQUE |
| `file_name` | `character varying(255)` | No | — | — | — |
| `storage_path` | `text` | No | — | — | — |
| `checksum_sha256` | `character(64)` | No | — | — | UNIQUE |
| `country_code` | `character(2)` | No | — | — | (country_code) → countries(code) ON DELETE RESTRICT |
| `status` | `upload_status` | No | `'pending'::upload_status` | — | — |
| `reviewed_by` | `uuid` | Sí | — | — | (reviewed_by) → users(id) ON DELETE SET NULL · CHECK |
| `reviewed_at` | `timestamp with time zone` | Sí | — | — | CHECK |
| `added_to_dataset` | `boolean` | No | `false` | — | — |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |
| `updated_at` | `timestamp with time zone` | No | `now()` | — | — |
| `deleted_at` | `timestamp with time zone` | Sí | — | — | — |

## `users`

| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |
|---|---|---|---|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | — | PK |
| `username` | `citext` | No | — | — | UNIQUE |
| `email` | `citext` | No | — | — | UNIQUE |
| `display_name` | `character varying(120)` | No | — | — | — |
| `hashed_password` | `text` | No | — | — | — |
| `role_id` | `uuid` | No | — | — | (role_id) → roles(id) ON DELETE RESTRICT |
| `is_active` | `boolean` | No | `true` | — | — |
| `last_login_at` | `timestamp with time zone` | Sí | — | — | — |
| `created_at` | `timestamp with time zone` | No | `now()` | — | — |
| `updated_at` | `timestamp with time zone` | No | `now()` | — | — |
| `deleted_at` | `timestamp with time zone` | Sí | — | — | — |
