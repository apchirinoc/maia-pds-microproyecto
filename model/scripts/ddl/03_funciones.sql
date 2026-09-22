-- ---------------------------------------------------------------------------
-- Funciones y disparadores compartidos
-- ---------------------------------------------------------------------------

-- Mantiene updated_at sin que la aplicación tenga que acordarse de hacerlo.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;
