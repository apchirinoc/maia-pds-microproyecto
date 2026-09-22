-- ---------------------------------------------------------------------------
-- Catálogos: roles, países y clases de tumor
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS roles (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code        varchar(32)  NOT NULL UNIQUE,
    name        varchar(80)  NOT NULL,
    description text,
    created_at  timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE roles IS 'Roles asignables a los usuarios de la plataforma.';

-- Clave natural: el código ISO-3166-1 alfa-2. No se usa uuid porque el código
-- ya es estable, universal y es lo que viaja en la API y en el mapa.
CREATE TABLE IF NOT EXISTS countries (
    code       char(2)      PRIMARY KEY,
    name       varchar(120) NOT NULL,
    name_es    varchar(120) NOT NULL,
    latitude   numeric(8,5) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude  numeric(8,5) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    created_at timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE countries IS
    'Países de origen declarados en las cargas. Las coordenadas alimentan el mapa del panel.';

-- El código es el mismo literal del ENUM tumor_class y del tipo TumorClass de
-- TypeScript. La tabla añade lo que un ENUM no puede llevar: etiqueta por
-- idioma, color y orden de presentación.
CREATE TABLE IF NOT EXISTS tumor_classes (
    code          tumor_class  PRIMARY KEY,
    label_es      varchar(60)  NOT NULL,
    label_en      varchar(60)  NOT NULL,
    color_hex     char(7)      NOT NULL CHECK (color_hex ~ '^#[0-9a-fA-F]{6}$'),
    display_order smallint     NOT NULL UNIQUE,
    is_tumor      boolean      NOT NULL,
    created_at    timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON COLUMN tumor_classes.is_tumor IS
    'Distingue las tres clases tumorales de healthy. Sostiene el criterio de '
    'promoción «recall tumor vs healthy», que es el dominante en un dominio clínico.';
