# Migraciones del esquema

## La regla

El DDL de `model/scripts/ddl/` es la **línea base v1** del esquema. Alembic no
la recrea: la revisión `0001_linea_base` está deliberadamente vacía y sólo
representa ese estado. A partir de ahí, **toda evolución del esquema entra por
una revisión de Alembic escrita a mano**.

Sin esta separación habría dos definiciones del mismo esquema —el DDL y las
migraciones— que se desincronizarían a la primera divergencia.

## Por qué no se usa `--autogenerate`

`env.py` fija `target_metadata = None` a propósito. Generar migraciones desde
los modelos ORM sería incorrecto aquí por dos motivos:

1. `app/models/entidades.py` cubre **15 de las 17 tablas**: no mapea
   `refresh_tokens` ni `dataset_snapshot_items`. Una migración autogenerada
   propondría **borrarlas**.
2. El DDL declara triggers, vistas, índices únicos parciales y comentarios de
   columna que el autogenerado no reproduce.

## Base nueva

```bash
cd model && docker compose up -d      # aplica el DDL y las semillas
cd ../api && .venv/bin/alembic stamp head
```

El `stamp` marca la base como si ya tuviera aplicada la línea base, sin
ejecutar nada.

## Cambio de esquema

1. Escribe el cambio en el DDL de `model/scripts/ddl/`, que sigue siendo la
   referencia para levantar una base desde cero.
2. Crea la revisión equivalente:
   `.venv/bin/alembic revision -m "descripción del cambio"`
3. Escribe `upgrade()` y `downgrade()` a mano.
4. Aplícala: `.venv/bin/alembic upgrade head`

## Conexión

La aplicación habla con Postgres por `asyncpg`; Alembic ejecuta de forma
síncrona, así que `env.py` traduce la URL a `psycopg`. Para apuntar a otra base
sin tocar `.env`, exporta `ALEMBIC_DATABASE_URL`.

## Comandos útiles

```bash
.venv/bin/alembic current    # revisión aplicada
.venv/bin/alembic history    # historial
.venv/bin/alembic upgrade head
```
