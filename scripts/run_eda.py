"""Exploración reproducible del dataset Brain Tumor MRI Scans."""

from __future__ import annotations

import argparse
import hashlib
import logging
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, UnidentifiedImageError

matplotlib.use("Agg", force=True)


LOGGER = logging.getLogger("brain_mri_eda")

EXPECTED_CLASSES = ("glioma", "meningioma", "pituitary", "healthy")
EXPECTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PARTITION_ALIASES = {
    "train": "train",
    "training": "train",
    "val": "validation",
    "valid": "validation",
    "validation": "validation",
    "test": "test",
    "testing": "test",
}

METADATA_COLUMNS = [
    "relative_path",
    "partition",
    "class_name",
    "extension",
    "file_size_bytes",
    "sha256",
    "is_readable_image",
    "is_image_candidate",
    "is_empty_file",
    "has_unexpected_extension",
    "error",
    "format",
    "width",
    "height",
    "aspect_ratio",
    "pixel_count",
    "mode",
    "channels",
    "dimension_outlier",
]

DUPLICATE_COLUMNS = [
    "sha256",
    "duplicate_count",
    "classes",
    "partitions",
    "cross_class",
    "cross_partition",
    "paths",
]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Explora el dataset Brain Tumor MRI Scans y genera un reporte reproducible."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directorio extraído que contiene las carpetas de clases.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directorio de salida para el reporte, las figuras y las tablas.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla para seleccionar ejemplos del mosaico.",
    )
    return parser.parse_args(argv)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_labels(relative_path: Path) -> tuple[str, str]:
    directory_parts = [part.casefold() for part in relative_path.parts[:-1]]
    class_name = next(
        (part for part in directory_parts if part in EXPECTED_CLASSES),
        "sin_clase",
    )
    partition = next(
        (
            PARTITION_ALIASES[part]
            for part in directory_parts
            if part in PARTITION_ALIASES
        ),
        "sin_particion",
    )

    if class_name == "sin_clase":
        non_partition_parts = [
            part for part in directory_parts if part not in PARTITION_ALIASES
        ]
        if non_partition_parts:
            class_name = non_partition_parts[-1]

    return partition, class_name


def iter_dataset_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"No existe el directorio de datos: {data_dir}")
    if not data_dir.is_dir():
        raise NotADirectoryError(f"La ruta de datos no es un directorio: {data_dir}")

    files = sorted(
        (path for path in data_dir.rglob("*") if path.is_file()),
        key=lambda path: path.as_posix().casefold(),
    )
    if not files:
        raise ValueError(f"No se encontraron archivos dentro de {data_dir}")
    return files


def inspect_file(path: Path, data_dir: Path) -> tuple[dict[str, Any], np.ndarray]:
    relative_path = path.relative_to(data_dir)
    partition, class_name = infer_labels(relative_path)
    extension = path.suffix.casefold()
    file_size = path.stat().st_size
    expected_extension = extension in EXPECTED_EXTENSIONS
    histogram = np.zeros(256, dtype=np.int64)

    record: dict[str, Any] = {
        "relative_path": relative_path.as_posix(),
        "partition": partition,
        "class_name": class_name,
        "extension": extension or "sin_extension",
        "file_size_bytes": file_size,
        "sha256": sha256_file(path),
        "is_readable_image": False,
        "is_image_candidate": expected_extension,
        "is_empty_file": file_size == 0,
        "has_unexpected_extension": not expected_extension,
        "error": "",
        "format": "",
        "width": np.nan,
        "height": np.nan,
        "aspect_ratio": np.nan,
        "pixel_count": np.nan,
        "mode": "",
        "channels": np.nan,
        "dimension_outlier": False,
    }

    if file_size == 0:
        record["error"] = "archivo vacío"
        return record, histogram

    try:
        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:
            image.load()
            width, height = image.size
            grayscale = image.convert("L")
            histogram = np.asarray(grayscale.histogram(), dtype=np.int64)
            record.update(
                {
                    "is_readable_image": True,
                    "is_image_candidate": True,
                    "format": image.format or "desconocido",
                    "width": width,
                    "height": height,
                    "aspect_ratio": width / height if height else np.nan,
                    "pixel_count": width * height,
                    "mode": image.mode,
                    "channels": len(image.getbands()),
                }
            )
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"

    return record, histogram


def inspect_dataset(data_dir: Path) -> tuple[pd.DataFrame, np.ndarray]:
    files = iter_dataset_files(data_dir)
    records: list[dict[str, Any]] = []
    global_histogram = np.zeros(256, dtype=np.int64)

    LOGGER.info("Inspeccionando %d archivos", len(files))
    for index, path in enumerate(files, start=1):
        record, histogram = inspect_file(path, data_dir)
        records.append(record)
        global_histogram += histogram
        if index % 500 == 0 or index == len(files):
            LOGGER.info("Procesados %d/%d archivos", index, len(files))

    metadata = pd.DataFrame.from_records(records, columns=METADATA_COLUMNS)
    readable = metadata["is_readable_image"]
    if not readable.any():
        raise ValueError(
            "No se encontró ninguna imagen legible en el directorio indicado"
        )

    mark_dimension_outliers(metadata)
    return metadata, global_histogram


def mark_dimension_outliers(metadata: pd.DataFrame) -> None:
    readable_mask = metadata["is_readable_image"]
    areas = metadata.loc[readable_mask, "pixel_count"].astype(float)
    log_areas = np.log2(areas)
    q1, q3 = log_areas.quantile([0.25, 0.75])
    iqr = q3 - q1

    if iqr == 0:
        common_area = float(areas.mode().iloc[0])
        outliers = areas != common_area
    else:
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = (log_areas < lower) | (log_areas > upper)

    metadata.loc[readable_mask, "dimension_outlier"] = outliers.astype(bool)


def class_sort_key(class_name: str) -> tuple[int, str]:
    try:
        return EXPECTED_CLASSES.index(class_name), class_name
    except ValueError:
        return len(EXPECTED_CLASSES), class_name


def format_integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def format_percent(value: float) -> str:
    return f"{value:.1%}".replace(".", ",")


def build_inventory(metadata: pd.DataFrame) -> pd.DataFrame:
    candidates = metadata[metadata["is_image_candidate"]].copy()
    total = len(candidates)
    inventory = (
        candidates.groupby(["partition", "class_name"], dropna=False)
        .size()
        .rename("image_count")
        .reset_index()
    )
    inventory["percentage_dataset"] = inventory["image_count"] / total * 100
    inventory["_class_order"] = inventory["class_name"].map(class_sort_key)
    inventory = inventory.sort_values(
        ["partition", "_class_order"], kind="stable"
    ).drop(columns="_class_order")
    return inventory.reset_index(drop=True)


def build_duplicate_table(metadata: pd.DataFrame) -> pd.DataFrame:
    readable = metadata[metadata["is_readable_image"]]
    rows: list[dict[str, Any]] = []

    for file_hash, group in readable.groupby("sha256", sort=True):
        if len(group) < 2:
            continue
        classes = sorted(group["class_name"].unique(), key=class_sort_key)
        partitions = sorted(group["partition"].unique())
        rows.append(
            {
                "sha256": file_hash,
                "duplicate_count": len(group),
                "classes": " | ".join(classes),
                "partitions": " | ".join(partitions),
                "cross_class": len(classes) > 1,
                "cross_partition": len(partitions) > 1,
                "paths": " | ".join(sorted(group["relative_path"])),
            }
        )

    return pd.DataFrame.from_records(rows, columns=DUPLICATE_COLUMNS)


def histogram_quantile(histogram: np.ndarray, quantile: float) -> int | None:
    total = int(histogram.sum())
    if total == 0:
        return None
    target = max(1, int(np.ceil(total * quantile)))
    return int(np.searchsorted(np.cumsum(histogram), target, side="left"))


def build_property_summary(
    metadata: pd.DataFrame, global_histogram: np.ndarray
) -> pd.DataFrame:
    readable = metadata[metadata["is_readable_image"]].copy()
    readable["file_size_kib"] = readable["file_size_bytes"] / 1024
    metrics = {
        "ancho_px": readable["width"],
        "alto_px": readable["height"],
        "relacion_aspecto": readable["aspect_ratio"],
        "tamano_kib": readable["file_size_kib"],
    }

    rows: list[dict[str, Any]] = []
    for metric_name, values in metrics.items():
        rows.append(
            {
                "metric": metric_name,
                "minimum": values.min(),
                "p05": values.quantile(0.05),
                "p25": values.quantile(0.25),
                "median": values.median(),
                "p75": values.quantile(0.75),
                "p95": values.quantile(0.95),
                "maximum": values.max(),
            }
        )

    rows.append(
        {
            "metric": "intensidad_gris_global",
            "minimum": histogram_quantile(global_histogram, 0),
            "p05": histogram_quantile(global_histogram, 0.05),
            "p25": histogram_quantile(global_histogram, 0.25),
            "median": histogram_quantile(global_histogram, 0.50),
            "p75": histogram_quantile(global_histogram, 0.75),
            "p95": histogram_quantile(global_histogram, 0.95),
            "maximum": histogram_quantile(global_histogram, 1),
        }
    )
    return pd.DataFrame(rows)


def build_quality_summary(
    metadata: pd.DataFrame,
    duplicates: pd.DataFrame,
) -> pd.DataFrame:
    candidates = metadata[metadata["is_image_candidate"]]
    actual_classes = set(candidates["class_name"])
    expected_classes = set(EXPECTED_CLASSES)
    missing_classes = sorted(expected_classes - actual_classes, key=class_sort_key)
    unexpected_classes = sorted(actual_classes - expected_classes)
    real_partitions = set(candidates["partition"]) - {"sin_particion"}

    duplicate_file_count = (
        int(duplicates["duplicate_count"].sum()) if not duplicates.empty else 0
    )
    redundant_copy_count = (
        int((duplicates["duplicate_count"] - 1).sum()) if not duplicates.empty else 0
    )
    cross_class_count = (
        int(duplicates["cross_class"].sum()) if not duplicates.empty else 0
    )
    cross_partition_count = (
        int(duplicates["cross_partition"].sum()) if not duplicates.empty else 0
    )

    rows = [
        ("archivos_totales", len(metadata), "Todos los archivos encontrados"),
        (
            "archivos_de_imagen",
            len(candidates),
            "Archivos con extensión esperada o reconocidos por Pillow",
        ),
        (
            "imagenes_legibles",
            int(metadata["is_readable_image"].sum()),
            "Imágenes verificadas y decodificadas por Pillow",
        ),
        (
            "archivos_vacios",
            int(metadata["is_empty_file"].sum()),
            "Tamaño igual a 0 bytes",
        ),
        (
            "imagenes_no_legibles",
            int((~candidates["is_readable_image"]).sum()),
            "Archivos candidatos que Pillow no pudo verificar o decodificar",
        ),
        (
            "extensiones_no_esperadas",
            int(metadata["has_unexpected_extension"].sum()),
            "Extensiones distintas de .jpg, .jpeg y .png",
        ),
        (
            "clases_esperadas_vacias",
            len(missing_classes),
            " | ".join(missing_classes) if missing_classes else "Ninguna",
        ),
        (
            "clases_no_esperadas",
            len(unexpected_classes),
            " | ".join(unexpected_classes) if unexpected_classes else "Ninguna",
        ),
        (
            "dimensiones_atipicas",
            int(metadata["dimension_outlier"].sum()),
            "Área en log2 fuera de 1,5 IQR; si IQR=0, área distinta de la moda",
        ),
        ("grupos_duplicados_exactos", len(duplicates), "Grupos con el mismo SHA-256"),
        (
            "archivos_en_grupos_duplicados",
            duplicate_file_count,
            "Incluye el original y sus copias dentro de cada grupo",
        ),
        (
            "copias_redundantes_exactas",
            redundant_copy_count,
            "Archivos que sobran al conservar una copia por cada SHA-256",
        ),
        (
            "grupos_duplicados_entre_clases",
            cross_class_count,
            "Mismo SHA-256 asociado con más de una clase",
        ),
        (
            "grupos_duplicados_entre_particiones",
            cross_partition_count,
            (
                "Riesgo potencial de fuga entre particiones"
                if real_partitions
                else "No evaluable: el dataset no contiene particiones"
            ),
        ),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "detail"])


def save_class_distribution(inventory: pd.DataFrame, output_path: Path) -> None:
    class_counts = inventory.groupby("class_name")["image_count"].sum()
    ordered_classes = sorted(class_counts.index, key=class_sort_key)
    class_counts = class_counts.reindex(ordered_classes)
    colors = ["#38598B", "#42A5A5", "#F2A65A", "#66A182"]

    fig, axis = plt.subplots(figsize=(9, 5.2))
    bars = axis.bar(
        class_counts.index, class_counts.values, color=colors[: len(class_counts)]
    )
    axis.set_title("Distribución de imágenes por clase", fontsize=15, pad=14)
    axis.set_xlabel("Clase")
    axis.set_ylabel("Número de imágenes")
    axis.grid(axis="y", linestyle="--", alpha=0.3)
    axis.set_axisbelow(True)
    total = class_counts.sum()
    for bar, count in zip(bars, class_counts.values, strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{format_integer(int(count))}\n({format_percent(count / total)})",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    axis.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_dimension_distribution(metadata: pd.DataFrame, output_path: Path) -> None:
    readable = metadata[metadata["is_readable_image"]]
    resolution_counts = (
        readable.groupby(["width", "height"]).size().sort_values(ascending=False)
    )
    top_resolutions = resolution_counts.head(12).sort_values()
    labels = [f"{int(width)}×{int(height)}" for width, height in top_resolutions.index]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    axes[0].scatter(
        readable["width"],
        readable["height"],
        s=16,
        alpha=0.3,
        color="#38598B",
        edgecolors="none",
    )
    axes[0].set_title("Ancho y alto de las imágenes")
    axes[0].set_xlabel("Ancho (px)")
    axes[0].set_ylabel("Alto (px)")
    axes[0].grid(linestyle="--", alpha=0.25)

    axes[1].barh(labels, top_resolutions.values, color="#42A5A5")
    axes[1].set_title("Resoluciones más frecuentes")
    axes[1].set_xlabel("Número de imágenes")
    axes[1].grid(axis="x", linestyle="--", alpha=0.25)

    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Distribución de dimensiones", fontsize=15, y=1.01)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def choose_sample_paths(
    metadata: pd.DataFrame, seed: int, samples_per_class: int = 2
) -> dict[str, list[str]]:
    readable = metadata[metadata["is_readable_image"]]
    rng = np.random.default_rng(seed)
    samples: dict[str, list[str]] = {}

    for class_name in sorted(readable["class_name"].unique(), key=class_sort_key):
        paths = sorted(
            readable.loc[readable["class_name"] == class_name, "relative_path"]
        )
        sample_size = min(samples_per_class, len(paths))
        selected_indices = rng.choice(len(paths), size=sample_size, replace=False)
        samples[class_name] = [paths[index] for index in sorted(selected_indices)]
    return samples


def save_sample_mosaic(
    metadata: pd.DataFrame,
    data_dir: Path,
    output_path: Path,
    seed: int,
    samples_per_class: int = 2,
) -> None:
    samples = choose_sample_paths(metadata, seed, samples_per_class)
    class_names = list(samples)
    fig, axes = plt.subplots(
        len(class_names),
        samples_per_class,
        figsize=(3.3 * samples_per_class, 3.0 * len(class_names)),
        squeeze=False,
    )

    for row_index, class_name in enumerate(class_names):
        selected_paths = samples[class_name]
        for column_index in range(samples_per_class):
            axis = axes[row_index, column_index]
            axis.axis("off")
            if column_index >= len(selected_paths):
                continue
            relative_path = selected_paths[column_index]
            with Image.open(data_dir / relative_path) as image:
                axis.imshow(image.convert("RGB"))
            axis.set_title(f"{class_name} · muestra {column_index + 1}", fontsize=10)

    fig.suptitle(
        f"Ejemplos reproducibles por clase (semilla {seed})", fontsize=15, y=1.0
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def markdown_table(dataframe: pd.DataFrame, decimals: int = 2) -> str:
    return dataframe.to_markdown(index=False, floatfmt=f".{decimals}f")


def build_conclusions(
    metadata: pd.DataFrame,
    inventory: pd.DataFrame,
    duplicates: pd.DataFrame,
) -> list[str]:
    candidates = metadata[metadata["is_image_candidate"]]
    readable = metadata[metadata["is_readable_image"]]
    class_counts = inventory.groupby("class_name")["image_count"].sum().sort_values()
    most_common_resolution = (
        readable.groupby(["width", "height"])
        .size()
        .sort_values(ascending=False)
        .index[0]
    )
    resolution_count = readable.groupby(["width", "height"]).ngroups
    most_common_resolution_count = int(
        readable.groupby(["width", "height"]).size().max()
    )
    dimension_outlier_count = int(metadata["dimension_outlier"].sum())
    unreadable_count = int((~candidates["is_readable_image"]).sum())
    duplicate_group_count = len(duplicates)
    redundant_copy_count = (
        int((duplicates["duplicate_count"] - 1).sum()) if not duplicates.empty else 0
    )
    cross_class_count = (
        int(duplicates["cross_class"].sum()) if not duplicates.empty else 0
    )

    conclusions = [
        (
            f"El dataset contiene {format_integer(len(candidates))} archivos de imagen en "
            f"{len(class_counts)} clases; la clase más numerosa es {class_counts.index[-1]} "
            f"({format_integer(int(class_counts.iloc[-1]))}) y la menor es {class_counts.index[0]} "
            f"({format_integer(int(class_counts.iloc[0]))})."
        ),
        (
            f"Se encontraron {format_integer(resolution_count)} resoluciones distintas; la más frecuente es "
            f"{int(most_common_resolution[0])}×{int(most_common_resolution[1])} píxeles "
            f"({format_percent(most_common_resolution_count / len(readable))} de las imágenes). La regla "
            f"estadística marcó {format_integer(dimension_outlier_count)} dimensiones atípicas; "
            "esto describe heterogeneidad de tamaños y no archivos corruptos."
        ),
        (
            f"La validación de lectura encontró {unreadable_count} archivos de imagen no legibles "
            f"y {int(metadata['is_empty_file'].sum())} archivos vacíos."
        ),
        (
            f"El análisis SHA-256 identificó {duplicate_group_count} grupos de duplicados exactos; "
            f"equivalen a {format_integer(redundant_copy_count)} copias redundantes y "
            f"{cross_class_count} grupos aparecen asociados con más de una clase."
        ),
    ]

    real_partitions = set(candidates["partition"]) - {"sin_particion"}
    if not real_partitions:
        conclusions.append(
            "El dataset no incluye particiones de entrenamiento, validación o prueba; el riesgo "
            "de fuga entre particiones deberá controlarse cuando el equipo construya el split."
        )
    return conclusions


def write_report(
    output_path: Path,
    metadata: pd.DataFrame,
    inventory: pd.DataFrame,
    properties: pd.DataFrame,
    quality: pd.DataFrame,
    duplicates: pd.DataFrame,
    seed: int,
) -> None:
    candidates = metadata[metadata["is_image_candidate"]]
    readable = metadata[metadata["is_readable_image"]]
    class_counts = (
        inventory.groupby("class_name", as_index=False)["image_count"]
        .sum()
        .rename(columns={"class_name": "clase", "image_count": "imagenes"})
    )
    class_counts["porcentaje"] = (
        class_counts["imagenes"] / class_counts["imagenes"].sum() * 100
    )
    class_counts["_order"] = class_counts["clase"].map(class_sort_key)
    class_counts = class_counts.sort_values("_order").drop(columns="_order")

    partition_counts = (
        inventory.groupby("partition", as_index=False)["image_count"]
        .sum()
        .rename(columns={"partition": "particion", "image_count": "imagenes"})
    )
    extension_counts = Counter(candidates["extension"])
    mode_counts = Counter(readable["mode"])
    channel_counts = Counter(readable["channels"].astype(int))
    actual_classes = set(class_counts["clase"])
    missing = sorted(set(EXPECTED_CLASSES) - actual_classes, key=class_sort_key)
    unexpected = sorted(actual_classes - set(EXPECTED_CLASSES))

    conclusions = build_conclusions(metadata, inventory, duplicates)
    conclusion_text = "\n".join(
        f"{index}. {text}" for index, text in enumerate(conclusions, 1)
    )
    duplicate_note = (
        "No se encontraron grupos de duplicados exactos."
        if duplicates.empty
        else f"Se encontraron {len(duplicates)} grupos; el detalle está en `tables/exact_duplicates.csv`."
    )

    quality_for_report = quality.rename(
        columns={"metric": "métrica", "value": "valor", "detail": "detalle"}
    )
    properties_for_report = properties.rename(
        columns={
            "metric": "métrica",
            "minimum": "mínimo",
            "median": "mediana",
            "maximum": "máximo",
        }
    )

    report = f"""# Exploración del dataset Brain Tumor MRI Scans

## Alcance y método

Este análisis describe los archivos realmente encontrados en el dataset descargado mediante DVC. La ejecución inspeccionó cada archivo, verificó su lectura con Pillow, calculó SHA-256, resumió propiedades físicas y generó las visualizaciones con semilla fija `{seed}`. No se entrenaron modelos ni se realizaron interpretaciones médicas.

## Inventario

Se encontraron **{format_integer(len(candidates))} archivos de imagen**, de los cuales **{format_integer(int(readable.shape[0]))} son legibles**. Las clases reales son `{", ".join(sorted(actual_classes, key=class_sort_key))}`.

- Clases esperadas ausentes: {", ".join(missing) if missing else "ninguna"}.
- Clases no esperadas: {", ".join(unexpected) if unexpected else "ninguna"}.
- Extensiones encontradas: {", ".join(f"{extension} ({count})" for extension, count in sorted(extension_counts.items()))}.

{markdown_table(class_counts)}

### Particiones

{markdown_table(partition_counts)}

El valor `sin_particion` indica que los archivos están organizados directamente por clase y no incluyen un split original de entrenamiento, validación o prueba.

![Distribución de imágenes por clase](figures/class_distribution.png)

## Propiedades de las imágenes

{markdown_table(properties_for_report)}

- Modos de color: {", ".join(f"{mode} ({count})" for mode, count in sorted(mode_counts.items()))}.
- Número de canales: {", ".join(f"{channels} ({count})" for channels, count in sorted(channel_counts.items()))}.
- La intensidad global se calculó después de convertir cada imagen a escala de grises, acumulando un histograma exacto de 256 niveles.
- Las dimensiones atípicas se marcaron mediante la regla de 1,5 IQR sobre `log2(ancho × alto)`.

![Distribución de dimensiones](figures/image_dimensions.png)

## Calidad de los datos

{markdown_table(quality_for_report, decimals=0)}

{duplicate_note}

Como el dataset no trae particiones, no es posible comprobar todavía duplicados entre entrenamiento y prueba. Antes de entrenar, el equipo debe agrupar duplicados y posibles imágenes relacionadas antes de dividir los datos.

## Ejemplos por clase

La selección es determinista para la semilla `{seed}`. Las imágenes se muestran únicamente para describir el dataset; no constituyen diagnósticos ni interpretaciones clínicas.

![Ejemplos reproducibles por clase](figures/sample_images_by_class.png)

## Conclusiones

{conclusion_text}

## Limitaciones

- El dataset público no aporta identificadores de paciente ni metadatos clínicos. SHA-256 detecta copias exactas, pero no imágenes casi duplicadas, cortes del mismo estudio ni pacientes repetidos.
- La ausencia de particiones impide evaluar fuga entre entrenamiento, validación y prueba en esta fase.
- La revisión comprueba integridad técnica y estructura de archivos; no valida la calidad clínica de las etiquetas.
- Los resultados corresponden a los archivos descargados mediante la versión DVC actual del repositorio.

Este conjunto público se emplea exclusivamente para un prototipo académico y no constituye una validación clínica ni un sistema autorizado para diagnóstico.

## Archivos reproducibles

- Inventario: [`tables/dataset_inventory.csv`](tables/dataset_inventory.csv)
- Calidad: [`tables/data_quality_summary.csv`](tables/data_quality_summary.csv)
- Duplicados exactos: [`tables/exact_duplicates.csv`](tables/exact_duplicates.csv)
- Metadatos por archivo: [`tables/image_metadata.csv`](tables/image_metadata.csv)
- Resumen de propiedades: [`tables/image_properties_summary.csv`](tables/image_properties_summary.csv)
"""
    output_path.write_text(report, encoding="utf-8")


def run_analysis(data_dir: Path, output_dir: Path, seed: int = 42) -> dict[str, Any]:
    data_dir = data_dir.resolve()
    output_dir = output_dir.resolve()
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    metadata, histogram = inspect_dataset(data_dir)
    inventory = build_inventory(metadata)
    duplicates = build_duplicate_table(metadata)
    properties = build_property_summary(metadata, histogram)
    quality = build_quality_summary(metadata, duplicates)

    inventory_output = inventory.rename(
        columns={
            "partition": "particion",
            "class_name": "clase",
            "image_count": "numero_imagenes",
            "percentage_dataset": "porcentaje_dataset",
        }
    )
    inventory_output["porcentaje_dataset"] = inventory_output[
        "porcentaje_dataset"
    ].round(4)
    quality_output = quality.rename(
        columns={"metric": "metrica", "value": "valor", "detail": "detalle"}
    )
    duplicates_output = duplicates.rename(
        columns={
            "duplicate_count": "numero_archivos",
            "classes": "clases",
            "partitions": "particiones",
            "cross_class": "entre_clases",
            "cross_partition": "entre_particiones",
            "paths": "rutas_relativas",
        }
    )
    metadata_output = metadata.rename(
        columns={
            "relative_path": "ruta_relativa",
            "partition": "particion",
            "class_name": "clase",
            "extension": "extension",
            "file_size_bytes": "tamano_bytes",
            "is_readable_image": "imagen_legible",
            "is_image_candidate": "archivo_imagen",
            "is_empty_file": "archivo_vacio",
            "has_unexpected_extension": "extension_no_esperada",
            "error": "error_lectura",
            "format": "formato",
            "aspect_ratio": "relacion_aspecto",
            "pixel_count": "numero_pixeles",
            "mode": "modo_color",
            "channels": "canales",
            "dimension_outlier": "dimension_atipica",
        }
    )
    properties_output = properties.rename(
        columns={
            "metric": "metrica",
            "minimum": "minimo",
            "median": "mediana",
            "maximum": "maximo",
        }
    ).round(4)

    inventory_output.to_csv(tables_dir / "dataset_inventory.csv", index=False)
    quality_output.to_csv(tables_dir / "data_quality_summary.csv", index=False)
    duplicates_output.to_csv(tables_dir / "exact_duplicates.csv", index=False)
    metadata_output.to_csv(tables_dir / "image_metadata.csv", index=False)
    properties_output.to_csv(tables_dir / "image_properties_summary.csv", index=False)

    save_class_distribution(inventory, figures_dir / "class_distribution.png")
    save_dimension_distribution(metadata, figures_dir / "image_dimensions.png")
    save_sample_mosaic(
        metadata,
        data_dir,
        figures_dir / "sample_images_by_class.png",
        seed,
    )
    write_report(
        output_dir / "eda_summary.md",
        metadata,
        inventory,
        properties,
        quality,
        duplicates,
        seed,
    )

    summary = {
        "total_image_files": int(metadata["is_image_candidate"].sum()),
        "readable_images": int(metadata["is_readable_image"].sum()),
        "duplicate_groups": len(duplicates),
        "cross_class_duplicate_groups": (
            int(duplicates["cross_class"].sum()) if not duplicates.empty else 0
        ),
        "partitions": sorted(inventory["partition"].unique()),
    }
    LOGGER.info("EDA terminada: %s", summary)
    return {
        "summary": summary,
        "inventory": inventory_output,
        "quality": quality_output,
        "properties": properties_output,
        "duplicates": duplicates_output,
    }


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = parse_args(argv)
    try:
        run_analysis(args.data_dir, args.output_dir, args.seed)
    except Exception:
        LOGGER.exception("No fue posible completar la exploración")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
