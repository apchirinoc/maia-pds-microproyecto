-- ---------------------------------------------------------------------------
-- Extensiones y convenciones del esquema
--
-- Convenciones aplicadas en todo el modelo:
--   · Tablas en snake_case y plural; PK siempre `id`; FK como <tabla_singular>_id.
--   · PK de tipo uuid con gen_random_uuid(): evita que la API exponga
--     identificadores enumerables.
--   · Marcas de tiempo en timestamptz (UTC). El formateo por zona y locale es
--     responsabilidad del frontend (web/src/lib/format.ts).
--   · Borrado lógico (deleted_at / is_active / status), nunca DELETE físico
--     sobre usuarios, modelos ni cargas.
--   · Los literales de los ENUM son idénticos a los tipos de TypeScript y a los
--     de Python, para no traducir datos en ninguna capa.
-- ---------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;    -- correos y logins sin distinguir caja
