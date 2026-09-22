-- ---------------------------------------------------------------------------
-- Usuarios y sesiones
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    username        citext       NOT NULL UNIQUE,
    email           citext       NOT NULL UNIQUE,
    display_name    varchar(120) NOT NULL,
    -- Sólo el hash. Argon2id, nunca la contraseña ni un digest reversible.
    hashed_password text         NOT NULL,
    role_id         uuid         NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_active       boolean      NOT NULL DEFAULT true,
    last_login_at   timestamptz,
    created_at      timestamptz  NOT NULL DEFAULT now(),
    updated_at      timestamptz  NOT NULL DEFAULT now(),
    -- Baja lógica: un usuario retirado debe seguir siendo citable desde la
    -- auditoría y desde las confirmaciones de diagnóstico que firmó.
    deleted_at      timestamptz
);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Se guarda el hash del token, no el token: si se filtra la tabla, los
    -- tokens siguen sin poder usarse.
    token_hash char(64)    NOT NULL UNIQUE,
    issued_at  timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    user_agent varchar(255),
    CONSTRAINT ck_refresh_tokens_vigencia CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_vigentes
    ON refresh_tokens (user_id, expires_at)
    WHERE revoked_at IS NULL;
