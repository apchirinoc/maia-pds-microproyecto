"""Genera los scripts DML a partir de la semilla del API.

El histórico de cargas se define una sola vez, en `api/app/seed/cargas.py`, que
a su vez replica el generador del frontend. Este script deriva de ahí el SQL, de
modo que las tres capas no pueden divergir: si cambia la semilla, se regenera.

    python tools/generar_semillas.py
"""

from __future__ import annotations

import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "api"))

from app.seed.cargas import HISTORICO_CARGAS  # noqa: E402
from app.seed.catalogos import CARGAS_POR_PAIS, PAISES  # noqa: E402
from app.seed.modelos import DETALLES_MODELO, MODELOS  # noqa: E402
from app.seed.panel import DISTRIBUCION_POR_CLASE, MUESTRAS_DATASET  # noqa: E402

DESTINO = RAIZ / "model" / "scripts" / "dml"

ETIQUETAS_CLASE = {
    "glioma": ("Glioma", "Glioma", "#4f46e5", 1, True),
    "meningioma": ("Meningioma", "Meningioma", "#059669", 2, True),
    "pituitary": ("Pituitary", "Pituitary", "#d97706", 3, True),
    "healthy": ("Healthy", "Healthy", "#0891b2", 4, False),
}

NOMBRES_ES = {
    "United States of America": "Estados Unidos",
    "United Kingdom": "Reino Unido",
    "Germany": "Alemania",
    "France": "Francia",
    "Spain": "España",
    "Italy": "Italia",
    "Japan": "Japón",
    "Brazil": "Brasil",
    "Mexico": "México",
    "Turkey": "Turquía",
    "South Africa": "Sudáfrica",
    "Egypt": "Egipto",
    "Sweden": "Suecia",
    "Netherlands": "Países Bajos",
    "Poland": "Polonia",
    "Saudi Arabia": "Arabia Saudí",
    "Peru": "Perú",
    "Canada": "Canadá",
    "India": "India",
    "China": "China",
    "Indonesia": "Indonesia",
    "Nigeria": "Nigeria",
    "Portugal": "Portugal",
    "Argentina": "Argentina",
    "Australia": "Australia",
    "Chile": "Chile",
    "Colombia": "Colombia",
    "Ecuador": "Ecuador",
}

CABECERA = (
    "-- ---------------------------------------------------------------------------\n"
    "-- {titulo}\n"
    "--\n"
    "-- GENERADO por model/tools/generar_semillas.py a partir de api/app/seed/.\n"
    "-- No editar a mano: regenerar para mantener alineadas las tres capas.\n"
    "-- ---------------------------------------------------------------------------\n\n"
)


def cita(valor: object) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def escribir(nombre: str, titulo: str, cuerpo: str) -> None:
    (DESTINO / nombre).write_text(CABECERA.format(titulo=titulo) + cuerpo, encoding="utf-8")
    print(f"  {nombre}")


def semilla_catalogos() -> None:
    lineas = ["INSERT INTO roles (code, name, description) VALUES"]
    roles = [
        ("admin", "Administrador", "Gestiona modelos, despliegues y curaduría del dataset."),
        ("researcher", "Investigador", "Consulta métricas y propone reentrenamientos."),
        ("viewer", "Observador", "Sólo lectura del panel analítico."),
    ]
    lineas.append(
        ",\n".join(f"    ({cita(c)}, {cita(n)}, {cita(d)})" for c, n, d in roles)
        + "\nON CONFLICT (code) DO NOTHING;\n"
    )

    lineas.append("\nINSERT INTO countries (code, name, name_es, latitude, longitude) VALUES")
    lineas.append(
        ",\n".join(
            f"    ({cita(p['code'])}, {cita(p['name'])}, "
            f"{cita(NOMBRES_ES.get(str(p['name']), p['name']))}, {p['latitude']}, {p['longitude']})"
            for p in PAISES
        )
        + "\nON CONFLICT (code) DO NOTHING;\n"
    )

    lineas.append(
        "\nINSERT INTO tumor_classes (code, label_es, label_en, color_hex, display_order, is_tumor) VALUES"
    )
    lineas.append(
        ",\n".join(
            f"    ({cita(codigo)}::tumor_class, {cita(es)}, {cita(en)}, {cita(color)}, {orden}, {cita(tumor)})"
            for codigo, (es, en, color, orden, tumor) in ETIQUETAS_CLASE.items()
        )
        + "\nON CONFLICT (code) DO NOTHING;\n"
    )
    escribir("01_catalogos.sql", "Catálogos: roles, países y clases de tumor", "\n".join(lineas))


def semilla_usuarios() -> None:
    # Hashes Argon2id reales, generados con la misma librería que usa el API.
    from app.core.security import hash_password

    cuentas = [
        # `demo` es la cuenta que documentan el API (DEMO_USERNAME) y el
        # frontend. Debe existir también en la base: sin ella, activar
        # DATA_SOURCE=postgres rompía el acceso de demostración en silencio.
        ("demo", "demo@brainneuroscan.example", "M. Rivera", "admin", "demo"),
        ("m.rivera", "m.rivera@brainneuroscan.example", "M. Rivera", "admin", "demo"),
        ("a.suarez", "a.suarez@brainneuroscan.example", "A. Suárez", "researcher", "demo"),
        ("pipeline-ci", "ci@brainneuroscan.example", "Pipeline CI", "researcher", "demo"),
    ]
    filas = ",\n".join(
        f"    ({cita(u)}, {cita(correo)}, {cita(nombre)}, {cita(hash_password(clave))}, "
        f"(SELECT id FROM roles WHERE code = {cita(rol)}))"
        for u, correo, nombre, rol, clave in cuentas
    )
    cuerpo = (
        "-- Contraseña de todas las cuentas de demostración: «demo».\n"
        "-- Se almacena el hash Argon2id, nunca la contraseña.\n"
        "INSERT INTO users (username, email, display_name, hashed_password, role_id) VALUES\n"
        f"{filas}\nON CONFLICT (username) DO NOTHING;\n"
    )
    escribir("02_usuarios.sql", "Usuarios de demostración", cuerpo)


def semilla_modelos() -> None:
    lineas = [
        "INSERT INTO models (slug, name, version, architecture, accuracy, f1_macro,",
        "                    precision_macro, recall_macro, auc, size_mb, status,",
        "                    weights_file_name, training_images, test_images,",
        "                    active_since, target_draft_version) VALUES",
    ]
    filas = []
    for modelo in MODELOS:
        detalle = DETALLES_MODELO[modelo["id"]]
        metricas = detalle["metrics"]
        filas.append(
            f"    ({cita(modelo['id'])}, {cita(modelo['name'])}, {cita(modelo['version'])}, "
            f"{cita(modelo['architecture'])}, {modelo['accuracy']}, {modelo['f1']}, "
            f"{metricas['precision_macro']}, {metricas['recall_macro']}, {metricas['auc']}, "
            f"{modelo['size_mb']}, {cita(modelo['status'])}::model_status, "
            f"{cita(modelo['weights_file_name'])}, {detalle['training_images']}, "
            f"{detalle['test_images']}, "
            f"{cita(detalle['active_since']) if detalle['active_since'] else 'NULL'}, "
            f"{cita(detalle['target_draft_version'])})"
        )
    lineas.append(",\n".join(filas) + "\nON CONFLICT (slug) DO NOTHING;\n")

    lineas.append("\n-- Enlace con la versión anterior de cada modelo.")
    lineas.append(
        "UPDATE models SET previous_model_id = (SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.3')\n"
        " WHERE slug = 'effnetb3-bt-v2.4';\n"
    )

    lineas.append("\nINSERT INTO model_class_metrics (model_id, class_code, f1) VALUES")
    filas = []
    for slug, detalle in DETALLES_MODELO.items():
        for clase, valor in detalle["class_performance"].items():
            filas.append(
                f"    ((SELECT id FROM models WHERE slug = {cita(slug)}), "
                f"{cita(clase)}::tumor_class, {valor})"
            )
    lineas.append(",\n".join(filas) + "\nON CONFLICT DO NOTHING;\n")

    lineas.append(
        "\nINSERT INTO model_confusion_cells (model_id, actual_class, predicted_class, cell_count) VALUES"
    )
    filas = []
    for slug, detalle in DETALLES_MODELO.items():
        for real, fila in detalle["confusion_matrix"].items():
            for predicha, conteo in fila.items():
                filas.append(
                    f"    ((SELECT id FROM models WHERE slug = {cita(slug)}), "
                    f"{cita(real)}::tumor_class, {cita(predicha)}::tumor_class, {conteo})"
                )
    lineas.append(",\n".join(filas) + "\nON CONFLICT DO NOTHING;\n")

    lineas.append(
        "\nINSERT INTO model_deployments (model_id, event_type, event_at, actor_label,"
        " actor_user_id) VALUES"
    )
    filas = []
    for slug, detalle in DETALLES_MODELO.items():
        for evento in detalle["deployment_history"]:
            filas.append(
                f"    ((SELECT id FROM models WHERE slug = {cita(slug)}), "
                f"{cita(evento['label'])}::deployment_event, "
                f"{cita(evento['date'])}::timestamptz, {cita(evento['author'])}, "
                f"(SELECT id FROM users WHERE username = {cita(evento['author'])}))"
            )
    lineas.append(",\n".join(filas) + ";\n")
    escribir("03_modelos.sql", "Registro de modelos, métricas y despliegues", "\n".join(lineas))


def semilla_dataset() -> None:
    muestras = {m["tumor_class"]: m["file_name"] for m in MUESTRAS_DATASET}
    lineas = [
        "-- Las 7 023 imágenes del dataset se generan con generate_series y se",
        "-- reparten con un hash estable del identificador, replicando la política",
        "-- de partición determinista de ml_project/pipelines/dataset.py: una imagen",
        "-- cae siempre del mismo lado aunque el dataset crezca.",
        "INSERT INTO dataset_images (stable_id, class_code, split, file_name, storage_path, source)",
        "SELECT",
        "    c.codigo || '-' || lpad(i::text, 5, '0'),",
        "    c.codigo::tumor_class,",
        "    CASE WHEN ('x' || substr(md5('brainneuroscan-split-v1|' || c.codigo || '|'",
        "                                 || c.codigo || '-' || lpad(i::text, 5, '0')), 1, 8))::bit(32)::bigint",
        "              < 0.81 * 4294967296",
        "         THEN 'train'::dataset_split ELSE 'test'::dataset_split END,",
        "    c.prefijo || '_' || lpad(i::text, 5, '0') || '.jpg',",
        "    '/dataset/' || c.codigo || '/' || c.prefijo || '_' || lpad(i::text, 5, '0') || '.jpg',",
        "    'kaggle'::dataset_image_source",
        "FROM (VALUES",
    ]
    prefijos = {"glioma": "Te-gl", "meningioma": "Te-me", "pituitary": "Te-pi", "healthy": "Te-no"}
    lineas.append(
        ",\n".join(
            f"    ({cita(clase)}, {cita(prefijos[clase])}, {total})"
            for clase, total in DISTRIBUCION_POR_CLASE.items()
        )
    )
    lineas.append(") AS c(codigo, prefijo, total)")
    lineas.append("CROSS JOIN LATERAL generate_series(1, c.total) AS i")
    lineas.append("ON CONFLICT (stable_id) DO NOTHING;\n")

    lineas.append("\n-- Muestra que el panel enseña para cada clase.")
    for clase, archivo in muestras.items():
        lineas.append(
            "UPDATE dataset_images SET is_showcase = true, file_name = "
            f"{cita(archivo)}\n WHERE id = (SELECT id FROM dataset_images "
            f"WHERE class_code = {cita(clase)}::tumor_class ORDER BY stable_id LIMIT 1);"
        )

    lineas.append("\n-- Instantánea inicial, la que sustenta las métricas del modelo en producción.")
    lineas.append(
        "INSERT INTO dataset_snapshots (snapshot_code, fingerprint, split_salt, train_fraction,\n"
        "                               total_images, train_images, test_images, reason)\n"
        "SELECT 'ds-inicial-v1', encode(sha256(string_agg(stable_id, '|' ORDER BY stable_id)::bytea), 'hex'),\n"
        "       'brainneuroscan-split-v1', 0.810, count(*),\n"
        "       count(*) FILTER (WHERE split = 'train'), count(*) FILTER (WHERE split = 'test'),\n"
        "       'Instantánea inicial del dataset de Kaggle.'\n"
        "FROM dataset_images WHERE deleted_at IS NULL\n"
        "ON CONFLICT (snapshot_code) DO NOTHING;\n"
    )
    lineas.append(
        "INSERT INTO dataset_snapshot_items (snapshot_id, dataset_image_id, split)\n"
        "SELECT s.id, di.id, di.split\n"
        "FROM dataset_snapshots s CROSS JOIN dataset_images di\n"
        "WHERE s.snapshot_code = 'ds-inicial-v1' AND di.deleted_at IS NULL\n"
        "ON CONFLICT DO NOTHING;\n"
    )
    lineas.append(
        "\nUPDATE models SET dataset_snapshot_id ="
        " (SELECT id FROM dataset_snapshots WHERE snapshot_code = 'ds-inicial-v1')\n"
        " WHERE slug IN ('effnetb3-bt-v2.4', 'vit-b16-bt-v0.9');\n"
    )
    escribir("04_dataset.sql", "Dataset e instantánea inicial", "\n".join(lineas))


def semilla_cargas() -> None:
    por_pais = {p["country_name"]: p["country_code"] for p in CARGAS_POR_PAIS}
    por_nombre = {p["name"]: p["code"] for p in PAISES}

    lineas = [
        "-- Réplica exacta del histórico que sirven el API y el frontend:",
        "-- 120 cargas, 56 con diagnóstico confirmado (46,67 % de cobertura) y",
        "-- 12 discrepancias (78,57 % de precisión real medida).",
        "INSERT INTO uploads (public_id, file_name, storage_path, checksum_sha256,",
        "                     country_code, status, created_at, reviewed_by, reviewed_at) VALUES",
    ]
    filas = []
    for indice, registro in enumerate(HISTORICO_CARGAS):
        codigo = por_nombre.get(registro["country_name"]) or por_pais[registro["country_name"]]
        revisor = (
            "(SELECT id FROM users WHERE username = 'm.rivera')"
            if registro["status"] != "pending"
            else "NULL"
        )
        revisado = cita(registro["captured_at"]) + "::timestamptz" if registro["status"] != "pending" else "NULL"
        # Checksum sintético pero único y estable por carga.
        checksum = f"md5({cita(registro['public_id'] if 'public_id' in registro else registro['id'])})::text || md5({cita(registro['file_name'])})::text"
        filas.append(
            f"    ({cita(registro['id'])}, {cita(registro['file_name'])}, "
            f"{cita('/uploads/' + registro['id'] + '.jpg')}, {checksum}, "
            f"{cita(codigo)}, {cita(registro['status'])}::upload_status, "
            f"{cita(registro['captured_at'])}::timestamptz, {revisor}, {revisado})"
        )
        _ = indice
    lineas.append(",\n".join(filas) + "\nON CONFLICT (public_id) DO NOTHING;\n")

    lineas.append(
        "\nINSERT INTO predictions (upload_id, model_id, predicted_class, confidence,"
        " preprocess_label, is_simulated, created_at) VALUES"
    )
    filas = []
    for registro in HISTORICO_CARGAS:
        filas.append(
            f"    ((SELECT id FROM uploads WHERE public_id = {cita(registro['id'])}), "
            f"(SELECT id FROM models WHERE slug = 'effnetb3-bt-v2.4'), "
            f"{cita(registro['prediction'])}::tumor_class, {registro['confidence']}, "
            f"'224×224 · CLAHE', true, {cita(registro['captured_at'])}::timestamptz)"
        )
    lineas.append(",\n".join(filas) + "\nON CONFLICT DO NOTHING;\n")

    confirmadas = [r for r in HISTORICO_CARGAS if r["ground_truth"]]
    lineas.append(
        "\nINSERT INTO ground_truth_diagnoses (upload_id, diagnosis, source, confirmed_by,"
        " confirmed_at) VALUES"
    )
    filas = []
    for registro in confirmadas:
        verdad = registro["ground_truth"]
        filas.append(
            f"    ((SELECT id FROM uploads WHERE public_id = {cita(registro['id'])}), "
            f"{cita(verdad['diagnosis'])}::tumor_class, {cita(verdad['source'])}::ground_truth_source, "
            f"{cita(verdad['confirmed_by'])}, {cita(verdad['confirmed_at'])}::timestamptz)"
        )
    lineas.append(",\n".join(filas) + ";\n")
    escribir("05_cargas.sql", "Histórico de cargas, predicciones y verdad de campo", "\n".join(lineas))


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Generando semillas en model/scripts/dml/:")
    semilla_catalogos()
    semilla_usuarios()
    semilla_modelos()
    semilla_dataset()
    semilla_cargas()


if __name__ == "__main__":
    main()
