-- ---------------------------------------------------------------------------
-- Catálogos: roles, países y clases de tumor
--
-- GENERADO por model/tools/generar_semillas.py a partir de api/app/seed/.
-- No editar a mano: regenerar para mantener alineadas las tres capas.
-- ---------------------------------------------------------------------------

INSERT INTO roles (code, name, description) VALUES
    ('admin', 'Administrador', 'Gestiona modelos, despliegues y curaduría del dataset.'),
    ('researcher', 'Investigador', 'Consulta métricas y propone reentrenamientos.'),
    ('viewer', 'Observador', 'Sólo lectura del panel analítico.')
ON CONFLICT (code) DO NOTHING;


INSERT INTO countries (code, name, name_es, latitude, longitude) VALUES
    ('AR', 'Argentina', 'Argentina', -34.6, -58.4),
    ('AU', 'Australia', 'Australia', -25.3, 133.8),
    ('BR', 'Brazil', 'Brasil', -15.8, -47.9),
    ('CA', 'Canada', 'Canadá', 56.1, -106.3),
    ('CL', 'Chile', 'Chile', -35.7, -71.5),
    ('CN', 'China', 'China', 35.9, 104.2),
    ('CO', 'Colombia', 'Colombia', 4.6, -74.1),
    ('EC', 'Ecuador', 'Ecuador', -1.8, -78.2),
    ('EG', 'Egypt', 'Egipto', 26.8, 30.8),
    ('FR', 'France', 'Francia', 46.2, 2.2),
    ('DE', 'Germany', 'Alemania', 51.2, 10.5),
    ('IN', 'India', 'India', 20.6, 79.0),
    ('ID', 'Indonesia', 'Indonesia', -0.8, 113.9),
    ('IT', 'Italy', 'Italia', 41.9, 12.6),
    ('JP', 'Japan', 'Japón', 36.2, 138.3),
    ('MX', 'Mexico', 'México', 23.6, -102.6),
    ('NL', 'Netherlands', 'Países Bajos', 52.1, 5.3),
    ('NG', 'Nigeria', 'Nigeria', 9.1, 8.7),
    ('PE', 'Peru', 'Perú', -9.2, -75.0),
    ('PL', 'Poland', 'Polonia', 51.9, 19.1),
    ('PT', 'Portugal', 'Portugal', 39.4, -8.2),
    ('SA', 'Saudi Arabia', 'Arabia Saudí', 23.9, 45.1),
    ('ZA', 'South Africa', 'Sudáfrica', -30.6, 22.9),
    ('ES', 'Spain', 'España', 40.5, -3.7),
    ('SE', 'Sweden', 'Suecia', 60.1, 18.6),
    ('TR', 'Turkey', 'Turquía', 38.9, 35.2),
    ('GB', 'United Kingdom', 'Reino Unido', 55.4, -3.4),
    ('US', 'United States of America', 'Estados Unidos', 39.8, -98.6)
ON CONFLICT (code) DO NOTHING;


INSERT INTO tumor_classes (code, label_es, label_en, color_hex, display_order, is_tumor) VALUES
    ('glioma'::tumor_class, 'Glioma', 'Glioma', '#4f46e5', 1, true),
    ('meningioma'::tumor_class, 'Meningioma', 'Meningioma', '#059669', 2, true),
    ('pituitary'::tumor_class, 'Pituitary', 'Pituitary', '#d97706', 3, true),
    ('healthy'::tumor_class, 'Healthy', 'Healthy', '#0891b2', 4, false)
ON CONFLICT (code) DO NOTHING;
