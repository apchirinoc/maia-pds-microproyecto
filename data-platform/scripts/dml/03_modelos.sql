-- ---------------------------------------------------------------------------
-- Registro de modelos, métricas y despliegues
--
-- GENERADO por model/tools/generar_semillas.py a partir de api/app/seed/.
-- No editar a mano: regenerar para mantener alineadas las tres capas.
-- ---------------------------------------------------------------------------

INSERT INTO models (slug, name, version, architecture, accuracy, f1_macro,
                    precision_macro, recall_macro, auc, size_mb, status,
                    weights_file_name, training_images, test_images,
                    active_since, target_draft_version) VALUES
    ('effnetb3-bt-v2.4', 'EffNetB3-BT', 'v2.4', 'EfficientNet-B3', 98.4, 0.981, 0.983, 0.979, 0.997, 47, 'production'::model_status, 'effnetb3_bt_v2.4.onnx', 5712, 1311, '2026-08-12', 'v2.5'),
    ('effnetb3-bt-v2.3', 'EffNetB3-BT', 'v2.3', 'EfficientNet-B3', 97.2, 0.968, 0.969, 0.966, 0.992, 47.3, 'archived'::model_status, 'effnetb3_bt_v2.3.onnx', 5400, 1280, '2026-02-02', 'v2.4'),
    ('resnet50-bt-v1.8', 'ResNet50-BT', 'v1.8', 'ResNet-50', 95.6, 0.951, 0.949, 0.944, 0.981, 98.4, 'archived'::model_status, 'resnet50_bt_v1.8.h5', 5100, 1200, '2025-10-18', 'v1.9'),
    ('vit-b16-bt-v0.9', 'ViT-B16-BT', 'v0.9', 'ViT-B/16', 96.9, 0.964, 0.962, 0.958, 0.989, 331, 'validation'::model_status, 'vit_b16_v0.9.pt', 5712, 1311, NULL, 'v0.9'),
    ('cnn-base-v1.0', 'CNN-Base', 'v1.0', 'CNN · 6 capas', 91.3, 0.902, 0.905, 0.898, 0.951, 12.8, 'baseline'::model_status, 'cnn_base_v1.0.h5', 4800, 1100, '2025-01-05', 'v1.1')
ON CONFLICT (slug) DO NOTHING;


-- Enlace con la versión anterior de cada modelo.
UPDATE models SET previous_model_id = (SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3')
 WHERE slug = 'effnetb3-bt-v2.4';


INSERT INTO model_class_metrics (model_id, class_code, f1) VALUES
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'glioma'::tumor_class, 0.983),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'meningioma'::tumor_class, 0.97),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'pituitary'::tumor_class, 0.99),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'healthy'::tumor_class, 0.997),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'glioma'::tumor_class, 0.965),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'meningioma'::tumor_class, 0.958),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'pituitary'::tumor_class, 0.972),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'healthy'::tumor_class, 0.988),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'glioma'::tumor_class, 0.941),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'meningioma'::tumor_class, 0.932),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'pituitary'::tumor_class, 0.951),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'healthy'::tumor_class, 0.97),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'glioma'::tumor_class, 0.955),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'meningioma'::tumor_class, 0.948),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'pituitary'::tumor_class, 0.964),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'healthy'::tumor_class, 0.981),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'glioma'::tumor_class, 0.891),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'meningioma'::tumor_class, 0.879),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'pituitary'::tumor_class, 0.902),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'healthy'::tumor_class, 0.94)
ON CONFLICT DO NOTHING;


INSERT INTO model_confusion_cells (model_id, actual_class, predicted_class, cell_count) VALUES
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'glioma'::tumor_class, 'glioma'::tumor_class, 295),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'glioma'::tumor_class, 'meningioma'::tumor_class, 4),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'glioma'::tumor_class, 'pituitary'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'glioma'::tumor_class, 'healthy'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'meningioma'::tumor_class, 'glioma'::tumor_class, 6),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'meningioma'::tumor_class, 'meningioma'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'meningioma'::tumor_class, 'pituitary'::tumor_class, 3),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'meningioma'::tumor_class, 'healthy'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'pituitary'::tumor_class, 'glioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'pituitary'::tumor_class, 'meningioma'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'pituitary'::tumor_class, 'pituitary'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'pituitary'::tumor_class, 'healthy'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'healthy'::tumor_class, 'glioma'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'healthy'::tumor_class, 'meningioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'healthy'::tumor_class, 'pituitary'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'healthy'::tumor_class, 'healthy'::tumor_class, 404),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'glioma'::tumor_class, 'glioma'::tumor_class, 295),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'glioma'::tumor_class, 'meningioma'::tumor_class, 4),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'glioma'::tumor_class, 'pituitary'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'glioma'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'meningioma'::tumor_class, 'glioma'::tumor_class, 6),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'meningioma'::tumor_class, 'meningioma'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'meningioma'::tumor_class, 'pituitary'::tumor_class, 3),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'meningioma'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'pituitary'::tumor_class, 'glioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'pituitary'::tumor_class, 'meningioma'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'pituitary'::tumor_class, 'pituitary'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'pituitary'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'healthy'::tumor_class, 'glioma'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'healthy'::tumor_class, 'meningioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'healthy'::tumor_class, 'pituitary'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'healthy'::tumor_class, 'healthy'::tumor_class, 404),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'glioma'::tumor_class, 'glioma'::tumor_class, 295),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'glioma'::tumor_class, 'meningioma'::tumor_class, 4),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'glioma'::tumor_class, 'pituitary'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'glioma'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'meningioma'::tumor_class, 'glioma'::tumor_class, 6),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'meningioma'::tumor_class, 'meningioma'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'meningioma'::tumor_class, 'pituitary'::tumor_class, 3),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'meningioma'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'pituitary'::tumor_class, 'glioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'pituitary'::tumor_class, 'meningioma'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'pituitary'::tumor_class, 'pituitary'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'pituitary'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'healthy'::tumor_class, 'glioma'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'healthy'::tumor_class, 'meningioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'healthy'::tumor_class, 'pituitary'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'healthy'::tumor_class, 'healthy'::tumor_class, 404),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'glioma'::tumor_class, 'glioma'::tumor_class, 295),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'glioma'::tumor_class, 'meningioma'::tumor_class, 4),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'glioma'::tumor_class, 'pituitary'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'glioma'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'meningioma'::tumor_class, 'glioma'::tumor_class, 6),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'meningioma'::tumor_class, 'meningioma'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'meningioma'::tumor_class, 'pituitary'::tumor_class, 3),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'meningioma'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'pituitary'::tumor_class, 'glioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'pituitary'::tumor_class, 'meningioma'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'pituitary'::tumor_class, 'pituitary'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'pituitary'::tumor_class, 'healthy'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'healthy'::tumor_class, 'glioma'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'healthy'::tumor_class, 'meningioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'healthy'::tumor_class, 'pituitary'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'healthy'::tumor_class, 'healthy'::tumor_class, 404),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'glioma'::tumor_class, 'glioma'::tumor_class, 295),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'glioma'::tumor_class, 'meningioma'::tumor_class, 4),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'glioma'::tumor_class, 'pituitary'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'glioma'::tumor_class, 'healthy'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'meningioma'::tumor_class, 'glioma'::tumor_class, 6),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'meningioma'::tumor_class, 'meningioma'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'meningioma'::tumor_class, 'pituitary'::tumor_class, 3),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'meningioma'::tumor_class, 'healthy'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'pituitary'::tumor_class, 'glioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'pituitary'::tumor_class, 'meningioma'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'pituitary'::tumor_class, 'pituitary'::tumor_class, 297),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'pituitary'::tumor_class, 'healthy'::tumor_class, 2),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'healthy'::tumor_class, 'glioma'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'healthy'::tumor_class, 'meningioma'::tumor_class, 1),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'healthy'::tumor_class, 'pituitary'::tumor_class, 0),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'healthy'::tumor_class, 'healthy'::tumor_class, 404)
ON CONFLICT DO NOTHING;


INSERT INTO model_deployments (model_id, event_type, event_at, actor_label, actor_user_id) VALUES
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'deployedToProduction'::deployment_event, '2026-04-12'::timestamptz, 'm.rivera', (SELECT id FROM users WHERE username = 'm.rivera')),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'validated'::deployment_event, '2026-04-10'::timestamptz, 'a.suarez', (SELECT id FROM users WHERE username = 'a.suarez')),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), 'trainingCompleted'::deployment_event, '2026-04-06'::timestamptz, 'pipeline-ci', (SELECT id FROM users WHERE username = 'pipeline-ci')),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'archived'::deployment_event, '2026-08-12'::timestamptz, 'm.rivera', (SELECT id FROM users WHERE username = 'm.rivera')),
    ((SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3'), 'deployedToProduction'::deployment_event, '2026-02-02'::timestamptz, 'm.rivera', (SELECT id FROM users WHERE username = 'm.rivera')),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'archived'::deployment_event, '2026-02-02'::timestamptz, 'a.suarez', (SELECT id FROM users WHERE username = 'a.suarez')),
    ((SELECT id FROM models WHERE slug = 'resnet50-bt-v1.8'), 'deployedToProduction'::deployment_event, '2025-10-18'::timestamptz, 'a.suarez', (SELECT id FROM users WHERE username = 'a.suarez')),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'validated'::deployment_event, '2026-08-28'::timestamptz, 'a.suarez', (SELECT id FROM users WHERE username = 'a.suarez')),
    ((SELECT id FROM models WHERE slug = 'vit-b16-bt-v0.9'), 'trainingCompleted'::deployment_event, '2026-08-20'::timestamptz, 'pipeline-ci', (SELECT id FROM users WHERE username = 'pipeline-ci')),
    ((SELECT id FROM models WHERE slug = 'cnn-base-v1.0'), 'trainingCompleted'::deployment_event, '2025-01-05'::timestamptz, 'pipeline-ci', (SELECT id FROM users WHERE username = 'pipeline-ci'));
