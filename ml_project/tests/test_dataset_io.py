"""Pruebas de `dataset_io`: escaneo de carpetas -> `RegistroImagen`.

No dependen de torch: validan el mapeo de clases, la estabilidad de los
identificadores y la integracion con la particion.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.dataset import particionar
from pipelines.dataset_io import (
    DatasetVacioError,
    cargar_bytes,
    conteo_por_clase,
    escanear_directorio,
    normalizar_clase,
)
from tests.conftest import encode_synthetic_mri


def _escribir(dir_clase: Path, nombre: str, seed: int) -> Path:
    dir_clase.mkdir(parents=True, exist_ok=True)
    ruta = dir_clase / nombre
    ruta.write_bytes(encode_synthetic_mri(seed=seed))
    return ruta


def test_normalizar_clase_mapea_sinonimos() -> None:
    assert normalizar_clase("notumor") == "healthy"
    assert normalizar_clase("NoTumor") == "healthy"
    assert normalizar_clase("glioma_tumor") == "glioma"
    assert normalizar_clase(" Meningioma ") == "meningioma"
    assert normalizar_clase("desconocida") is None


def test_escanea_estructura_plana_y_mapea_notumor(tmp_path: Path) -> None:
    _escribir(tmp_path / "glioma", "a.png", 1)
    _escribir(tmp_path / "meningioma", "b.png", 2)
    _escribir(tmp_path / "pituitary", "c.png", 3)
    _escribir(tmp_path / "notumor", "d.png", 4)

    registros, indice = escanear_directorio(tmp_path)

    assert len(registros) == 4
    assert conteo_por_clase(registros) == {
        "glioma": 1,
        "meningioma": 1,
        "pituitary": 1,
        "healthy": 1,
    }
    assert set(indice) == {registro.identificador for registro in registros}


def test_ids_estables_y_deterministas(tmp_path: Path) -> None:
    _escribir(tmp_path / "glioma", "a.png", 7)
    _escribir(tmp_path / "healthy", "b.png", 8)

    primeros = [registro.identificador for registro in escanear_directorio(tmp_path)[0]]
    segundos = [registro.identificador for registro in escanear_directorio(tmp_path)[0]]

    assert primeros == segundos


def test_duplicados_exactos_colapsan(tmp_path: Path) -> None:
    contenido = encode_synthetic_mri(seed=9)
    carpeta = tmp_path / "glioma"
    carpeta.mkdir(parents=True)
    (carpeta / "original.png").write_bytes(contenido)
    (carpeta / "copia.png").write_bytes(contenido)

    registros, _ = escanear_directorio(tmp_path)

    assert len(registros) == 1


def test_estructura_anidada_training_testing(tmp_path: Path) -> None:
    _escribir(tmp_path / "Training" / "glioma", "a.png", 1)
    _escribir(tmp_path / "Testing" / "notumor", "b.png", 2)

    registros, _ = escanear_directorio(tmp_path)
    conteos = conteo_por_clase(registros)

    assert conteos["glioma"] == 1
    assert conteos["healthy"] == 1


def test_directorio_sin_imagenes_lanza(tmp_path: Path) -> None:
    (tmp_path / "otros").mkdir()
    with pytest.raises(DatasetVacioError):
        escanear_directorio(tmp_path)


def test_cargar_bytes_y_alimenta_particion(tmp_path: Path) -> None:
    _escribir(tmp_path / "glioma", "a.png", 1)
    _escribir(tmp_path / "healthy", "b.png", 2)

    registros, indice = escanear_directorio(tmp_path)
    crudos = cargar_bytes(indice, registros[0].identificador)
    assert isinstance(crudos, bytes) and crudos

    particion = particionar(registros)
    assert particion.total == 2
