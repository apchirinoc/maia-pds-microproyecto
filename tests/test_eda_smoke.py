from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from PIL import Image

from scripts.run_eda import run_analysis


def create_image(
    path: Path, color: tuple[int, int, int], size: tuple[int, int]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path, format="PNG")


def test_eda_smoke_with_temporary_images(tmp_path: Path) -> None:
    data_dir = tmp_path / "dataset"
    output_dir = tmp_path / "reports"

    source = data_dir / "train" / "glioma" / "source.png"
    duplicate = data_dir / "test" / "meningioma" / "duplicate.png"
    create_image(source, (20, 40, 60), (32, 24))
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, duplicate)
    create_image(
        data_dir / "train" / "pituitary" / "sample.png", (80, 10, 30), (24, 32)
    )
    create_image(data_dir / "train" / "healthy" / "sample.png", (10, 80, 30), (32, 32))
    corrupt = data_dir / "train" / "healthy" / "corrupt.jpg"
    corrupt.write_bytes(b"not an image")

    result = run_analysis(data_dir, output_dir, seed=7)

    assert result["summary"]["total_image_files"] == 5
    assert result["summary"]["readable_images"] == 4
    assert result["summary"]["duplicate_groups"] == 1
    assert result["summary"]["cross_class_duplicate_groups"] == 1
    assert set(result["summary"]["partitions"]) == {"test", "train"}

    expected_outputs = [
        output_dir / "eda_summary.md",
        output_dir / "figures" / "class_distribution.png",
        output_dir / "figures" / "image_dimensions.png",
        output_dir / "figures" / "sample_images_by_class.png",
        output_dir / "tables" / "dataset_inventory.csv",
        output_dir / "tables" / "data_quality_summary.csv",
        output_dir / "tables" / "exact_duplicates.csv",
        output_dir / "tables" / "image_metadata.csv",
        output_dir / "tables" / "image_properties_summary.csv",
    ]
    assert all(path.is_file() and path.stat().st_size > 0 for path in expected_outputs)

    duplicates = pd.read_csv(output_dir / "tables" / "exact_duplicates.csv")
    assert bool(duplicates.loc[0, "entre_clases"])
    assert bool(duplicates.loc[0, "entre_particiones"])
    assert all(
        not Path(path).is_absolute()
        for path in duplicates.loc[0, "rutas_relativas"].split(" | ")
    )
