"""Puente entre el dataset en disco y la logica pura de `dataset.py`.

`dataset.py` no toca el sistema de ficheros a proposito: opera sobre
`RegistroImagen` (identificador estable + clase) para que la particion sea
reproducible en cualquier maquina. Este modulo es quien lee el disco y produce
esos registros, sin depender de torch ni de GPU.

Decisiones:

- **Identificador estable = SHA-256 de los bytes** de la imagen. Es el mismo
  criterio con el que la EDA detecto duplicados exactos, asi que dos copias del
  mismo archivo colapsan en un unico registro y nunca caen en particiones
  distintas.
- **Mapeo de clases configurable**: el dataset de Kaggle nombra la clase sin
  tumor como `notumor` (Entrega 1) o `healthy` (Entrega 2). Aqui se normaliza al
  literal canonico de `TUMOR_CLASSES` (`healthy`), de modo que el resto del
  sistema ve siempre los mismos cuatro nombres.
- **Recorrido recursivo**: la clase de una imagen se deduce de la carpeta de
  clase que aparezca en su ruta, asi funciona tanto con una estructura plana
  (`root/glioma/x.jpg`) como anidada (`root/Training/glioma/x.jpg`).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pipelines.config import TUMOR_CLASSES
from pipelines.dataset import RegistroImagen

EXTENSIONES_IMAGEN: Final[frozenset[str]] = frozenset({".jpg", ".jpeg", ".png"})

# Sinonimos de carpeta -> clase canonica. Las claves se comparan en minusculas.
ALIAS_CLASES: Final[dict[str, str]] = {
    "glioma": "glioma",
    "glioma_tumor": "glioma",
    "meningioma": "meningioma",
    "meningioma_tumor": "meningioma",
    "pituitary": "pituitary",
    "pituitary_tumor": "pituitary",
    "healthy": "healthy",
    "notumor": "healthy",
    "no_tumor": "healthy",
    "normal": "healthy",
}


class DatasetVacioError(RuntimeError):
    """No se encontro ninguna imagen etiquetable bajo el directorio dado."""


def normalizar_clase(nombre_carpeta: str) -> str | None:
    """Traduce el nombre de una carpeta a una clase canonica, o `None`.

    Devolver `None` (en vez de lanzar) permite que el recorrido ignore carpetas
    que no son de clase (`Training`, `Testing`, `.git`, ...) sin ruido.
    """
    return ALIAS_CLASES.get(nombre_carpeta.strip().lower())


def _clase_desde_ruta(ruta: Path, raiz: Path) -> str | None:
    """Busca, de la carpeta mas cercana a la mas lejana, una que sea de clase.

    Recorrer de dentro hacia fuera hace que `root/glioma/sub/x.jpg` se clasifique
    como `glioma` aunque haya subcarpetas intermedias.
    """
    for parte in reversed(ruta.relative_to(raiz).parts[:-1]):
        clase = normalizar_clase(parte)
        if clase is not None:
            return clase
    return None


def _sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def escanear_directorio(raiz: str | Path) -> tuple[list[RegistroImagen], dict[str, Path]]:
    """Recorre `raiz` y devuelve los registros y el indice `id -> ruta`.

    Los duplicados exactos (mismo SHA-256) se colapsan en un unico registro; se
    conserva la primera ruta vista, ordenando el recorrido para que esa eleccion
    sea determinista. Un mismo identificador con dos clases distintas es un error
    de etiquetado y se deja que `dataset.particionar` lo rechace mas adelante.
    """
    raiz = Path(raiz).resolve()
    if not raiz.is_dir():
        raise NotADirectoryError(f"No existe el directorio de datos: {raiz}")

    registros: dict[str, RegistroImagen] = {}
    indice: dict[str, Path] = {}

    for ruta in sorted(raiz.rglob("*")):
        if not ruta.is_file() or ruta.suffix.lower() not in EXTENSIONES_IMAGEN:
            continue
        clase = _clase_desde_ruta(ruta, raiz)
        if clase is None:
            continue
        identificador = _sha256(ruta.read_bytes())
        if identificador in registros:
            continue
        registros[identificador] = RegistroImagen(identificador=identificador, clase=clase)
        indice[identificador] = ruta

    if not registros:
        raise DatasetVacioError(
            f"No se hallaron imagenes de clases {sorted(set(ALIAS_CLASES.values()))} "
            f"bajo {raiz}. Verifica que el dataset este descomprimido."
        )

    return list(registros.values()), indice


def cargar_bytes(indice: Mapping[str, Path], identificador: str) -> bytes:
    """Lee los bytes crudos de una imagen por su identificador estable."""
    ruta = indice.get(identificador)
    if ruta is None:
        raise KeyError(f"El indice no contiene el identificador {identificador!r}")
    return Path(ruta).read_bytes()


def conteo_por_clase(registros: list[RegistroImagen]) -> dict[str, int]:
    """Resumen rapido para registrar en el log del entrenamiento."""
    conteos = {clase: 0 for clase in TUMOR_CLASSES}
    for registro in registros:
        conteos[registro.clase] += 1
    return conteos
