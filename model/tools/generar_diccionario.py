"""Genera el diccionario de datos leyendo el catálogo de PostgreSQL.

Se extrae de la base ya creada y no de los ficheros DDL: así el documento
describe el esquema que realmente existe y no puede desviarse de él.

    docker compose up -d
    python tools/generar_diccionario.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

CONTENEDOR = "brainneuroscan-db"
USUARIO = "brainneuroscan"
BASE = "brainneuroscan"
SEPARADOR = "\x1f"

CONSULTA_COLUMNAS = """
SELECT c.relname, a.attnum, a.attname,
       format_type(a.atttypid, a.atttypmod),
       CASE WHEN a.attnotnull THEN 'No' ELSE 'Sí' END,
       coalesce(pg_get_expr(d.adbin, d.adrelid), ''),
       coalesce(col_description(c.oid, a.attnum), '')
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname, a.attnum;
"""

CONSULTA_RESTRICCIONES = """
SELECT c.relname, a.attname, con.contype, pg_get_constraintdef(con.oid)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN unnest(con.conkey) AS k(attnum) ON true
LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
WHERE n.nspname = 'public'
ORDER BY c.relname, a.attname;
"""

CONSULTA_TABLAS = """
SELECT c.relname, coalesce(obj_description(c.oid), '')
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY c.relname;
"""

CONSULTA_ENUMS = """
SELECT t.typname, string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder)
FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public' GROUP BY t.typname ORDER BY t.typname;
"""


def consultar(sql: str) -> list[list[str]]:
    salida = subprocess.run(
        # Sin `-i`: la consulta va en `-c`, así que psql no debe leer stdin. Con
        # la entrada estándar conectada, la segunda invocación consumía restos de
        # la primera y devolvía filas truncadas.
        ["docker", "exec", CONTENEDOR, "psql", "-U", USUARIO, "-d", BASE,
         "-tAF", SEPARADOR, "-c", sql],
        capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL,
    ).stdout
    # Se recortan sólo saltos de línea: `strip()` sin argumentos también
    # elimina 0x1f, que es justo el separador de campos, y dejaba la última
    # fila con una columna de menos.
    return [linea.split(SEPARADOR) for linea in salida.strip("\n").splitlines() if linea]


def main() -> None:
    try:
        columnas = consultar(CONSULTA_COLUMNAS)
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"No se pudo consultar la base: {error}", file=sys.stderr)
        print("Levanta el contenedor con «docker compose up -d».", file=sys.stderr)
        raise SystemExit(1) from error

    comentarios = {fila[0]: fila[1] for fila in consultar(CONSULTA_TABLAS)}
    enums = consultar(CONSULTA_ENUMS)

    restricciones: dict[tuple[str, str], list[str]] = {}
    for tabla, columna, tipo, definicion in consultar(CONSULTA_RESTRICCIONES):
        if not columna:
            continue
        etiqueta = {"p": "PK", "u": "UNIQUE", "f": "FK", "c": "CHECK"}.get(tipo, tipo)
        texto = "PK" if etiqueta == "PK" else (
            definicion.replace("FOREIGN KEY ", "").replace("REFERENCES ", "→ ")
            if etiqueta == "FK" else etiqueta
        )
        restricciones.setdefault((tabla, columna), []).append(texto)

    partes = [
        "# Diccionario de datos — BrainNeuroScan\n",
        "> **GENERADO** por `model/tools/generar_diccionario.py` leyendo el catálogo\n"
        "> de PostgreSQL. Describe el esquema que existe realmente, no el que\n"
        "> describen los ficheros DDL. Para regenerarlo: `docker compose up -d` y\n"
        "> `python tools/generar_diccionario.py`.\n",
        "## Tipos enumerados\n",
        "| Tipo | Valores admitidos |",
        "|---|---|",
    ]
    for nombre, valores in enums:
        partes.append(f"| `{nombre}` | {', '.join(f'`{v}`' for v in valores.split(', '))} |")

    tabla_actual = None
    for tabla, _, columna, tipo, nulo, defecto, comentario in columnas:
        if tabla != tabla_actual:
            tabla_actual = tabla
            partes.append(f"\n## `{tabla}`\n")
            if comentarios.get(tabla):
                partes.append(f"{comentarios[tabla]}\n")
            partes.append("| Columna | Tipo | Nulo | Defecto | Descripción | Restricciones |")
            partes.append("|---|---|---|---|---|---|")

        marcas = restricciones.get((tabla, columna), [])
        # Se ordenan para que la salida sea estable entre ejecuciones.
        marcas_texto = " · ".join(sorted(set(marcas))) if marcas else "—"
        partes.append(
            f"| `{columna}` | `{tipo}` | {nulo} | "
            f"{f'`{defecto}`' if defecto else '—'} | "
            f"{comentario or '—'} | {marcas_texto} |"
        )

    destino = pathlib.Path(__file__).resolve().parents[1] / "docs" / "diccionario-datos.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Escrito {destino.relative_to(destino.parents[2])}: "
          f"{len({c[0] for c in columnas})} tablas, {len(columnas)} columnas")


if __name__ == "__main__":
    main()
