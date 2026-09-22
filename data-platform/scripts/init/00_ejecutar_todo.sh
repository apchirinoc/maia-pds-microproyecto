#!/bin/bash
# ---------------------------------------------------------------------------
# Punto de entrada de la inicialización.
#
# Postgres ejecuta lo que encuentre en /docker-entrypoint-initdb.d en orden
# alfabético, y sólo en el primer arranque (cuando el volumen está vacío).
# Este script fuerza el orden correcto: primero todo el DDL, después el DML.
#
# `set -e` es deliberado: si un script falla, el contenedor debe morir en vez
# de quedarse en marcha con un esquema a medias.
# ---------------------------------------------------------------------------
set -e

ejecutar() {
    echo "  → $(basename "$1")"
    psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
         --set ON_ERROR_STOP=1 --quiet --file "$1"
}

echo "[model] Aplicando DDL…"
for archivo in /scripts/ddl/*.sql; do ejecutar "$archivo"; done

echo "[model] Cargando datos semilla…"
for archivo in /scripts/dml/*.sql; do ejecutar "$archivo"; done

echo "[model] Esquema listo."
