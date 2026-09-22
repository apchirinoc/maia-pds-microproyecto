"""Explicabilidad de las predicciones: sensibilidad por oclusion.

Patron «Explainable Predictions» (Machine Learning Design Patterns, cap. 7):
la explicacion no es un servicio aparte ni un cuaderno de analisis, sino una
capacidad del propio artefacto. Viaja empaquetada con el modelo, igual que el
preprocesamiento, de modo que el servicio nunca reimplementa el metodo.

Por que oclusion y no Grad-CAM
------------------------------
El modelo se sirve como **ONNX** a traves de `onnxruntime`, un motor de
inferencia que solo ejecuta pasadas hacia adelante: no construye grafo de
retropropagacion ni expone gradientes intermedios. Grad-CAM necesita
exactamente eso (el gradiente de la clase objetivo respecto a los mapas de
activacion de la ultima convolucion), asi que **no es implementable sobre el
artefacto que realmente se sirve**. Implementarlo obligaria a mantener una
segunda copia del modelo en el framework de entrenamiento, es decir, a
reintroducir la desviacion entrenamiento-servicio que el patron «Transform»
elimina.

La sensibilidad por oclusion (Zeiler & Fergus, 2014, *Visualizing and
Understanding Convolutional Networks*) responde a la misma pregunta con solo
pasadas hacia adelante: se tapa sistematicamente un parche de la imagen y se
mide cuanto cae la probabilidad de la clase predicha. Si tapar una region
derrumba la prediccion, esa region sostenia la prediccion.

Compromiso asumido
------------------
- **A favor**: no requiere gradientes, es agnostico al modelo (sirve para
  cualquier ONNX, TensorRT o endpoint remoto) y explica el modelo que de
  verdad esta en produccion, no una replica suya.
- **En contra**: cuesta N pasadas adicionales por imagen en lugar de una sola
  retropropagacion, y la resolucion del mapa esta limitada por el paso de la
  rejilla, no por el pixel. `OcclusionConfig` acota ambos costes: `max_passes`
  rechaza configuraciones desmedidas y `batch_size` agrupa las oclusiones en
  lotes para amortizar la sobrecarga por invocacion de `onnxruntime`.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from typing import Any, Final

import cv2
import numpy as np

OCCLUSION_METHOD_ID: Final[str] = "occlusion"
"""Identificador estable del metodo, replicado en la API y el frontend."""

INFLUENCE_MAP_MEDIA_TYPE: Final[str] = "image/png"


@dataclass(frozen=True)
class OcclusionConfig:
    """Parametros del analisis de sensibilidad por oclusion.

    Es inmutable y serializable, igual que `PreprocessConfig`: se registra en
    los metadatos del modelo para que la explicacion mostrada al usuario sea
    reproducible y auditable.

    Attributes:
        patch_size: lado del parche cuadrado que se ocluye, en pixeles del
            tensor ya preprocesado.
        stride: desplazamiento de la rejilla. Al ser menor que `patch_size`,
            los parches se solapan y el mapa resultante es mas suave.
        occlusion_value: valor con el que se rellena el parche. Cero en el
            espacio normalizado equivale a la media de ImageNet, es decir, al
            «gris neutro» del modelo: la oclusion elimina informacion en lugar
            de introducir un borde artificial de alto contraste.
        batch_size: numero de oclusiones que se envian juntas a `onnxruntime`.
        max_passes: cota dura de pasadas por imagen. Protege al servicio de una
            configuracion que dispare el coste sin que nadie lo note.
    """

    patch_size: int = 32
    stride: int = 16
    occlusion_value: float = 0.0
    batch_size: int = 32
    max_passes: int = 1024

    def __post_init__(self) -> None:
        if self.patch_size <= 0:
            raise ValueError("patch_size debe ser positivo")
        if self.stride <= 0:
            raise ValueError("stride debe ser positivo")
        if self.stride > self.patch_size:
            raise ValueError(
                "stride no puede superar patch_size: la rejilla dejaria franjas "
                "de la imagen sin ocluir y el mapa tendria huecos"
            )
        if self.batch_size <= 0:
            raise ValueError("batch_size debe ser positivo")
        if self.max_passes <= 0:
            raise ValueError("max_passes debe ser positivo")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def label(self) -> str:
        """Etiqueta legible que la interfaz muestra junto al mapa."""
        return f"Oclusión {self.patch_size} px · paso {self.stride} px"

    def offsets(self, extent: int) -> tuple[int, ...]:
        """Posiciones iniciales de los parches a lo largo de un eje.

        Siempre incluye el borde final, de manera que ningun pixel de la imagen
        se queda fuera de la rejilla aunque `extent` no sea multiplo de `stride`.
        """
        if extent < self.patch_size:
            raise ValueError(
                f"La imagen mide {extent} px y el parche {self.patch_size} px: el parche no cabe"
            )
        last = extent - self.patch_size
        positions = list(range(0, last + 1, self.stride))
        if positions[-1] != last:
            positions.append(last)
        return tuple(positions)

    def passes_for(self, height: int, width: int) -> int:
        """Numero de pasadas hacia adelante que costara explicar una imagen."""
        return len(self.offsets(height)) * len(self.offsets(width))


DEFAULT_OCCLUSION_CONFIG: Final[OcclusionConfig] = OcclusionConfig()


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum(axis=1, keepdims=True)


def _probabilities(
    session: Any,
    input_name: str,
    batch: np.ndarray,
    *,
    output_is_probability: bool,
) -> np.ndarray:
    outputs = np.asarray(session.run(None, {input_name: batch})[0], dtype=np.float32)
    if output_is_probability:
        return outputs
    return _softmax(outputs)


def compute_occlusion_map(
    tensor: np.ndarray,
    session: Any,
    target_index: int,
    *,
    config: OcclusionConfig = DEFAULT_OCCLUSION_CONFIG,
    output_is_probability: bool = False,
    input_name: str | None = None,
) -> np.ndarray:
    """Calcula el mapa de influencia de una imagen ya preprocesada.

    Args:
        tensor: tensor `(C, H, W)` float32 tal y como lo produce
            `MriPreprocessor`, es decir, ya normalizado.
        session: sesion de `onnxruntime` que sirve el modelo.
        target_index: indice de la clase cuya evidencia se quiere explicar,
            normalmente la clase predicha.
        config: parametros de la rejilla de oclusion.
        output_is_probability: si el modelo ya devuelve probabilidades. Cuando
            es falso se aplica softmax, igual que hace el envoltorio pyfunc.
        input_name: nombre del tensor de entrada; si no se indica se toma el
            primero declarado por el modelo.

    Returns:
        Array `(H, W)` float32 con la influencia normalizada a `[0, 1]`. El
        valor 1 marca la region cuya oclusion mas derrumba la probabilidad de
        `target_index`; el 0, regiones irrelevantes o que incluso favorecen a
        la clase al taparlas.

    Es determinista: el mismo tensor, la misma sesion y la misma configuracion
    producen siempre exactamente el mismo mapa.
    """
    tensor = np.asarray(tensor, dtype=np.float32)
    if tensor.ndim != 3:
        raise ValueError(f"Se esperaba un tensor (C, H, W); recibido {tensor.shape}")

    _, height, width = tensor.shape
    rows = config.offsets(height)
    columns = config.offsets(width)
    total_passes = len(rows) * len(columns)
    if total_passes > config.max_passes:
        raise ValueError(
            f"La configuracion exige {total_passes} pasadas por imagen y el limite "
            f"es {config.max_passes}. Aumenta stride o eleva max_passes de forma "
            "consciente: cada pasada es una inferencia completa"
        )

    resolved_input = input_name or session.get_inputs()[0].name
    baseline_batch = tensor[np.newaxis, ...]
    baseline = float(
        _probabilities(
            session, resolved_input, baseline_batch, output_is_probability=output_is_probability
        )[0, target_index]
    )

    accumulated = np.zeros((height, width), dtype=np.float64)
    coverage = np.zeros((height, width), dtype=np.float64)

    patch = config.patch_size
    positions = [(row, column) for row in rows for column in columns]

    for start in range(0, len(positions), config.batch_size):
        chunk = positions[start : start + config.batch_size]
        occluded = np.repeat(baseline_batch, len(chunk), axis=0)
        for index, (row, column) in enumerate(chunk):
            occluded[index, :, row : row + patch, column : column + patch] = config.occlusion_value

        scores = _probabilities(
            session, resolved_input, occluded, output_is_probability=output_is_probability
        )[:, target_index]

        for index, (row, column) in enumerate(chunk):
            # Influencia = cuanto cae la probabilidad al tapar la region.
            caida = baseline - float(scores[index])
            accumulated[row : row + patch, column : column + patch] += caida
            coverage[row : row + patch, column : column + patch] += 1.0

    averaged = accumulated / np.maximum(coverage, 1.0)
    # Solo la evidencia a favor de la clase interesa: si tapar una region sube
    # la probabilidad, esa region no sostiene la prediccion.
    positive = np.clip(averaged, 0.0, None)
    peak = float(positive.max())
    if peak <= 0.0:
        return np.zeros((height, width), dtype=np.float32)
    return (positive / peak).astype(np.float32)


def encode_influence_map(influence_map: np.ndarray) -> str:
    """Serializa el mapa como PNG RGBA en base64.

    Formato elegido y por que:

    - **PNG** frente a una lista anidada de flotantes: un mapa de 224x224 son
      50 176 numeros, unos 600 KB de JSON por prediccion; el mismo mapa
      comprimido sin perdida ocupa entre 3 y 15 KB. La respuesta de la API
      sigue siendo pequena aunque se clasifique un lote.
    - **base64** porque la respuesta viaja como JSON, que no admite binario.
    - **La influencia va en el canal alfa** (los tres canales de color son
      blanco constante). Asi el cliente lo consume tal cual, sin decodificar ni
      recolorear: sirve como `mask-image` de CSS o como `<img>` superpuesto, y
      la cuantizacion a 8 bits (error maximo 1/255) es intachable para una
      visualizacion.
    """
    influence_map = np.asarray(influence_map, dtype=np.float32)
    if influence_map.ndim != 2:
        raise ValueError(f"Se esperaba un mapa 2D; recibido {influence_map.shape}")

    alpha = np.rint(np.clip(influence_map, 0.0, 1.0) * 255.0).astype(np.uint8)
    white = np.full_like(alpha, 255)
    bgra = np.dstack([white, white, white, alpha])

    success, buffer = cv2.imencode(".png", bgra)
    if not success:
        raise RuntimeError("No se pudo codificar el mapa de influencia como PNG")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


def decode_influence_map(encoded: str) -> np.ndarray:
    """Inverso de `encode_influence_map`, usado por las pruebas y el analisis."""
    raw = np.frombuffer(base64.b64decode(encoded), dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim != 3 or image.shape[2] != 4:
        raise ValueError("El contenido no es un PNG RGBA valido")
    return (image[:, :, 3].astype(np.float32) / 255.0).astype(np.float32)


def influence_map_data_uri(encoded: str) -> str:
    """Envuelve el PNG en base64 como data URI listo para el navegador."""
    return f"data:{INFLUENCE_MAP_MEDIA_TYPE};base64,{encoded}"
