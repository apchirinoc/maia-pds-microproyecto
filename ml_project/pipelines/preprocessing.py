"""Preprocesamiento de imagenes MRI: fuente unica de verdad.

Este modulo es el unico lugar del sistema donde se define como se transforma
una imagen antes de llegar al modelo. Se empaqueta dentro del artefacto de
MLflow mediante `code_paths`, de modo que el entrenamiento y la inferencia
ejecutan exactamente el mismo codigo.

Patron «Transform» (Machine Learning Design Patterns, cap. 6): el
preprocesamiento viaja con el modelo, nunca se reimplementa en el servicio.
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Final

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

IMAGENET_MEAN: Final[tuple[float, float, float]] = (0.485, 0.456, 0.406)
IMAGENET_STD: Final[tuple[float, float, float]] = (0.229, 0.224, 0.225)

_INTERPOLATIONS: Final[dict[str, int]] = {
    "bilinear": cv2.INTER_LINEAR,
    "bicubic": cv2.INTER_CUBIC,
    "area": cv2.INTER_AREA,
}


class InvalidImageError(ValueError):
    """La entrada no pudo decodificarse como imagen."""


@dataclass(frozen=True)
class PreprocessConfig:
    """Parametros del preprocesamiento.

    Es inmutable y serializable: se guarda como artefacto junto al modelo y
    su huella permite detectar cualquier divergencia entre entrenamiento y
    servicio.
    """

    target_size: int = 224
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: tuple[int, int] = (8, 8)
    mean: tuple[float, float, float] = IMAGENET_MEAN
    std: tuple[float, float, float] = IMAGENET_STD
    interpolation: str = "bilinear"
    mode: str = "clahe"

    def __post_init__(self) -> None:
        if self.mode not in ("clahe", "rgb_imagenet"):
            raise ValueError("mode debe ser clahe o rgb_imagenet")
        if self.mode == "rgb_imagenet" and self.interpolation != "bilinear":
            raise ValueError("El contrato RGB de Colab requiere interpolación bilinear")
        if self.target_size <= 0:
            raise ValueError("target_size debe ser positivo")
        if self.clahe_clip_limit <= 0:
            raise ValueError("clahe_clip_limit debe ser positivo")
        if self.interpolation not in _INTERPOLATIONS:
            raise ValueError(
                f"interpolation debe ser una de {sorted(_INTERPOLATIONS)}, "
                f"recibido {self.interpolation!r}"
            )
        if any(value <= 0 for value in self.std):
            raise ValueError("std no puede contener ceros ni negativos")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Mantener la huella de los paquetes CLAHE existentes.
        if self.mode == "clahe":
            data.pop("mode")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PreprocessConfig:
        return cls(
            target_size=int(data["target_size"]),
            clahe_clip_limit=float(data["clahe_clip_limit"]),
            clahe_tile_grid=tuple(data["clahe_tile_grid"]),  # type: ignore[arg-type]
            mean=tuple(data["mean"]),  # type: ignore[arg-type]
            std=tuple(data["std"]),  # type: ignore[arg-type]
            interpolation=str(data["interpolation"]),
            mode=str(data.get("mode", "clahe")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> PreprocessConfig:
        return cls.from_dict(json.loads(raw))

    @property
    def fingerprint(self) -> str:
        """Huella estable de la configuracion.

        Se registra como parametro del run y se guarda en el artefacto. El
        motor de inferencia la compara para garantizar que sirve exactamente
        el preprocesamiento con el que se entreno.
        """
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()[:16]

    @property
    def label(self) -> str:
        """Etiqueta legible que muestra la interfaz.

        La cadena «224x224 - CLAHE» deja de estar escrita a mano en el
        frontend: se deriva de la configuracion real del artefacto.
        """
        transform = "RGB · ImageNet" if self.mode == "rgb_imagenet" else "CLAHE"
        return f"{self.target_size}×{self.target_size} · {transform}"


class MriPreprocessor:
    """Aplica el preprocesamiento definido por `PreprocessConfig`.

    Orden de las operaciones (fijo y compartido por entrenamiento e inferencia):

    1. Decodificacion y conversion a escala de grises de 8 bits.
    2. Redimensionado a `target_size` cuadrado.
    3. CLAHE sobre la imagen ya redimensionada, para que la rejilla de teselas
       sea consistente con independencia del tamano original.
    4. Escalado a [0, 1], replicado a 3 canales (los backbones preentrenados en
       ImageNet esperan RGB) y normalizacion por media y desviacion.
    """

    def __init__(self, config: PreprocessConfig | None = None) -> None:
        self.config = config or PreprocessConfig()
        self._clahe = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip_limit,
            tileGridSize=tuple(self.config.clahe_tile_grid),
        )
        self._mean = np.asarray(self.config.mean, dtype=np.float32).reshape(3, 1, 1)
        self._std = np.asarray(self.config.std, dtype=np.float32).reshape(3, 1, 1)

    @staticmethod
    def decode(raw: bytes) -> np.ndarray:
        """Decodifica bytes de imagen (JPG/PNG) a un array de OpenCV."""
        if not raw:
            raise InvalidImageError("El contenido de la imagen esta vacio")
        buffer = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise InvalidImageError("No se pudo decodificar la imagen")
        return image

    @staticmethod
    def to_uint8_grayscale(image: np.ndarray) -> np.ndarray:
        """Normaliza cualquier entrada a escala de grises de 8 bits.

        Cubre MRI de 16 bits, PNG con canal alfa y JPG en color.
        """
        if image.ndim == 3:
            channels = image.shape[2]
            if channels == 4:
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            elif channels == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif channels == 1:
                image = image[:, :, 0]
            else:
                raise InvalidImageError(f"Numero de canales no soportado: {channels}")
        elif image.ndim != 2:
            raise InvalidImageError(f"Se esperaba una imagen 2D o 3D, recibido {image.ndim}D")

        if image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return image

    def __call__(self, image: np.ndarray) -> np.ndarray:
        """Transforma una imagen decodificada en un tensor (3, S, S) float32."""
        if self.config.mode == "rgb_imagenet":
            raise ValueError("El contrato RGB debe decodificarse desde bytes con Pillow")
        gray = self.to_uint8_grayscale(image)
        size = self.config.target_size
        resized = cv2.resize(
            gray, (size, size), interpolation=_INTERPOLATIONS[self.config.interpolation]
        )
        equalized = self._clahe.apply(resized)
        scaled = equalized.astype(np.float32) / 255.0
        stacked = np.repeat(scaled[np.newaxis, :, :], 3, axis=0)
        return (stacked - self._mean) / self._std

    def from_bytes(self, raw: bytes) -> np.ndarray:
        if self.config.mode == "rgb_imagenet":
            try:
                # Igual a ImageFolder + Resize(PIL) + ToTensor + Normalize.
                with Image.open(io.BytesIO(raw)) as source:
                    rgb = source.convert("RGB").resize(
                        (self.config.target_size, self.config.target_size),
                        resample=Image.Resampling.BILINEAR,
                    )
                    tensor = np.asarray(rgb, dtype=np.float32).transpose(2, 0, 1) / 255.0
                return (tensor - self._mean) / self._std
            except (UnidentifiedImageError, OSError, ValueError) as error:
                raise InvalidImageError("No se pudo decodificar la imagen RGB") from error
        return self(self.decode(raw))

    def batch(self, images: Iterable[bytes]) -> np.ndarray:
        """Construye un lote (N, 3, S, S) a partir de bytes de imagen."""
        tensors = [self.from_bytes(raw) for raw in images]
        if not tensors:
            raise InvalidImageError("El lote no contiene imagenes")
        return np.stack(tensors).astype(np.float32)
