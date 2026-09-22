-- ---------------------------------------------------------------------------
-- Dataset e instantánea inicial
--
-- GENERADO por model/tools/generar_semillas.py a partir de api/app/seed/.
-- No editar a mano: regenerar para mantener alineadas las tres capas.
-- ---------------------------------------------------------------------------

-- Las 7 023 imágenes del dataset se generan con generate_series y se
-- reparten con un hash estable del identificador, replicando la política
-- de partición determinista de ml_project/pipelines/dataset.py: una imagen
-- cae siempre del mismo lado aunque el dataset crezca.
INSERT INTO dataset_images (stable_id, class_code, split, file_name, storage_path, source)
SELECT
    c.codigo || '-' || lpad(i::text, 5, '0'),
    c.codigo::tumor_class,
    CASE WHEN ('x' || substr(md5('brainneuroscan-split-v1|' || c.codigo || '|'
                                 || c.codigo || '-' || lpad(i::text, 5, '0')), 1, 8))::bit(32)::bigint
              < 0.81 * 4294967296
         THEN 'train'::dataset_split ELSE 'test'::dataset_split END,
    c.prefijo || '_' || lpad(i::text, 5, '0') || '.jpg',
    '/dataset/' || c.codigo || '/' || c.prefijo || '_' || lpad(i::text, 5, '0') || '.jpg',
    'kaggle'::dataset_image_source
FROM (VALUES
    ('glioma', 'Te-gl', 1621),
    ('meningioma', 'Te-me', 1645),
    ('pituitary', 'Te-pi', 1757),
    ('healthy', 'Te-no', 2000)
) AS c(codigo, prefijo, total)
CROSS JOIN LATERAL generate_series(1, c.total) AS i
ON CONFLICT (stable_id) DO NOTHING;


-- Muestra que el panel enseña para cada clase.
UPDATE dataset_images SET is_showcase = true, file_name = 'Te-gl_0231.jpg'
 WHERE id = (SELECT id FROM dataset_images WHERE class_code = 'glioma'::tumor_class ORDER BY stable_id LIMIT 1);
UPDATE dataset_images SET is_showcase = true, file_name = 'Te-me_0118.jpg'
 WHERE id = (SELECT id FROM dataset_images WHERE class_code = 'meningioma'::tumor_class ORDER BY stable_id LIMIT 1);
UPDATE dataset_images SET is_showcase = true, file_name = 'Te-pi_0204.jpg'
 WHERE id = (SELECT id FROM dataset_images WHERE class_code = 'pituitary'::tumor_class ORDER BY stable_id LIMIT 1);
UPDATE dataset_images SET is_showcase = true, file_name = 'Te-no_0092.jpg'
 WHERE id = (SELECT id FROM dataset_images WHERE class_code = 'healthy'::tumor_class ORDER BY stable_id LIMIT 1);

-- Instantánea inicial, la que sustenta las métricas del modelo en producción.
INSERT INTO dataset_snapshots (snapshot_code, fingerprint, split_salt, train_fraction,
                               total_images, train_images, test_images, reason)
SELECT 'ds-inicial-v1', encode(sha256(string_agg(stable_id, '|' ORDER BY stable_id)::bytea), 'hex'),
       'brainneuroscan-split-v1', 0.810, count(*),
       count(*) FILTER (WHERE split = 'train'), count(*) FILTER (WHERE split = 'test'),
       'Instantánea inicial del dataset de Kaggle.'
FROM dataset_images WHERE deleted_at IS NULL
ON CONFLICT (snapshot_code) DO NOTHING;

INSERT INTO dataset_snapshot_items (snapshot_id, dataset_image_id, split)
SELECT s.id, di.id, di.split
FROM dataset_snapshots s CROSS JOIN dataset_images di
WHERE s.snapshot_code = 'ds-inicial-v1' AND di.deleted_at IS NULL
ON CONFLICT DO NOTHING;


UPDATE models SET dataset_snapshot_id = (SELECT id FROM dataset_snapshots WHERE snapshot_code = 'ds-inicial-v1')
 WHERE slug IN ('effnetb3-bt-v2.4', 'vit-b16-bt-v0.9');
