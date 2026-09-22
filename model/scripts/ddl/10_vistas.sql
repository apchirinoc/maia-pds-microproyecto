-- ---------------------------------------------------------------------------
-- Vistas de agregación
--
-- Los KPI se calculan aquí y no en la API, para que exista una sola definición
-- de cada métrica. El frontend replica estas fórmulas únicamente en su modo de
-- datos simulados.
-- ---------------------------------------------------------------------------

-- Distribución del dataset por clase (donut del panel).
CREATE OR REPLACE VIEW vw_dataset_distribution AS
SELECT
    di.class_code,
    count(*)                                          AS total_images,
    count(*) FILTER (WHERE di.split = 'train')        AS train_images,
    count(*) FILTER (WHERE di.split = 'test')         AS test_images
FROM dataset_images di
WHERE di.deleted_at IS NULL
GROUP BY di.class_code;

-- Volumen de cargas por país (mapa del panel).
CREATE OR REPLACE VIEW vw_uploads_by_country AS
SELECT
    c.code AS country_code,
    c.name AS country_name,
    count(u.id) AS uploads
FROM countries c
LEFT JOIN uploads u ON u.country_code = c.code AND u.deleted_at IS NULL
GROUP BY c.code, c.name
HAVING count(u.id) > 0
ORDER BY uploads DESC;

-- Cargas por mes de los últimos doce meses.
CREATE OR REPLACE VIEW vw_uploads_by_month AS
SELECT
    date_trunc('month', u.created_at) AS month_start,
    count(*)                          AS uploads
FROM uploads u
WHERE u.deleted_at IS NULL
GROUP BY 1
ORDER BY 1;

-- Detalle de cada carga con su predicción y su verdad de campo.
-- `is_correct` es NULL cuando no hay diagnóstico confirmado: «desconocido» no
-- es «error», y confundirlos haría inservible la métrica de rendimiento real.
CREATE OR REPLACE VIEW vw_upload_ground_truth AS
SELECT
    u.id                       AS upload_id,
    u.public_id,
    u.file_name,
    u.created_at               AS captured_at,
    u.country_code,
    c.name                     AS country_name,
    u.status,
    p.predicted_class,
    p.confidence,
    g.diagnosis                AS ground_truth_diagnosis,
    g.source                   AS ground_truth_source,
    g.confirmed_by,
    g.confirmed_at,
    (g.id IS NOT NULL)         AS has_ground_truth,
    CASE WHEN g.id IS NULL THEN NULL
         ELSE g.diagnosis = p.predicted_class
    END                        AS is_correct
FROM uploads u
JOIN countries c ON c.code = u.country_code
LEFT JOIN predictions p ON p.upload_id = u.id
LEFT JOIN ground_truth_diagnoses g ON g.upload_id = u.id AND g.deleted_at IS NULL
WHERE u.deleted_at IS NULL;

-- Los dos KPI del circuito de verdad de campo.
CREATE OR REPLACE VIEW vw_ground_truth_performance AS
SELECT
    count(*)                                             AS total_uploads,
    count(*) FILTER (WHERE has_ground_truth)             AS confirmed_uploads,
    count(*) FILTER (WHERE is_correct)                   AS correct_predictions,
    count(*) FILTER (WHERE is_correct IS FALSE)          AS mismatched_predictions,
    round(100.0 * count(*) FILTER (WHERE has_ground_truth)
          / nullif(count(*), 0), 2)                      AS coverage,
    round(100.0 * count(*) FILTER (WHERE is_correct)
          / nullif(count(*) FILTER (WHERE has_ground_truth), 0), 2) AS measured_accuracy
FROM vw_upload_ground_truth;

-- Rendimiento real por clase: sostiene el análisis por subgrupos que exige
-- el patrón «Fairness Lens» y que hoy es una brecha abierta del proyecto.
CREATE OR REPLACE VIEW vw_ground_truth_performance_by_class AS
SELECT
    predicted_class,
    count(*)                                    AS total_uploads,
    count(*) FILTER (WHERE has_ground_truth)    AS confirmed_uploads,
    count(*) FILTER (WHERE is_correct)          AS correct_predictions,
    round(100.0 * count(*) FILTER (WHERE is_correct)
          / nullif(count(*) FILTER (WHERE has_ground_truth), 0), 2) AS measured_accuracy
FROM vw_upload_ground_truth
WHERE predicted_class IS NOT NULL
GROUP BY predicted_class
ORDER BY predicted_class;

-- Rendimiento por país: el dato de partición ya se captura en cada carga.
CREATE OR REPLACE VIEW vw_ground_truth_performance_by_country AS
SELECT
    country_code,
    country_name,
    count(*)                                    AS total_uploads,
    count(*) FILTER (WHERE has_ground_truth)    AS confirmed_uploads,
    round(100.0 * count(*) FILTER (WHERE is_correct)
          / nullif(count(*) FILTER (WHERE has_ground_truth), 0), 2) AS measured_accuracy
FROM vw_upload_ground_truth
GROUP BY country_code, country_name
ORDER BY total_uploads DESC;

-- Resumen del histórico: los cuatro indicadores de la cabecera de la vista.
CREATE OR REPLACE VIEW vw_upload_history_summary AS
SELECT
    (SELECT count(*) FROM uploads WHERE deleted_at IS NULL)                       AS total_uploads,
    (SELECT count(*) FROM uploads WHERE deleted_at IS NULL AND status = 'pending')  AS pending_review,
    (SELECT round(avg(confidence), 2) FROM predictions)                            AS average_confidence,
    (SELECT count(*) FROM uploads WHERE deleted_at IS NULL AND status = 'discarded') AS discarded;

-- Resumen del registro de modelos.
CREATE OR REPLACE VIEW vw_model_registry_summary AS
SELECT
    m.name                     AS production_model_name,
    m.version                  AS production_model_version,
    m.active_since,
    m.accuracy                 AS accuracy_test,
    (SELECT count(*) FROM models WHERE status = 'archived' AND deleted_at IS NULL) AS archived_versions,
    round((SELECT sum(size_mb) FROM models WHERE deleted_at IS NULL) / 1024.0, 2)  AS storage_gb
FROM models m
WHERE m.status = 'production' AND m.deleted_at IS NULL;
