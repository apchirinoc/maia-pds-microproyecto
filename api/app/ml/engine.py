"""Puerto de inferencia.

El servicio de dominio depende de esta abstraccion, nunca de un motor
concreto. Nota deliberada: la firma recibe **bytes de imagen**, no un tensor.
El preprocesamiento no aparece en ningun punto de este contrato porque viaja
dentro del artefacto del modelo.

Lo mismo ocurre con la explicabilidad (patron «Explainable Predictions»): el
contrato solo dice *que* se puede pedir una explicacion y *que forma* tiene la
respuesta. El **como** (sensibilidad por oclusion, tamano de parche, paso de
la rejilla) es asunto del artefacto. Aqui no hay ni una linea del metodo, del
mismo modo que no hay ni una linea de CLAHE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

INFLUENCE_MAP_MEDIA_TYPE = "image/png"


@dataclass(frozen=True)
class ClassScore:
    tumor_class: str
    confidence: float


@dataclass(frozen=True)
class PredictionExplanation:
    """Justificacion espacial de una prediccion, calculada por el artefacto.

    Attributes:
        method: identificador estable del metodo (`occlusion`). Permite que la
            interfaz diga con que se ha explicado la prediccion y que el
            registro de auditoria lo conserve.
        method_label: etiqueta legible que declara el modelo, con sus
            parametros reales.
        influence_map_png: mapa de influencia normalizado a `[0, 1]`, como PNG
            en base64. La intensidad viaja en el canal alfa, de modo que el
            cliente lo superpone directamente sobre la MRI.
    """

    method: str
    method_label: str
    influence_map_png: str

    @property
    def data_uri(self) -> str:
        """Forma en que se entrega al navegador, lista para `<img>` o mascara CSS."""
        return f"data:{INFLUENCE_MAP_MEDIA_TYPE};base64,{self.influence_map_png}"


@dataclass(frozen=True)
class InferenceResult:
    predicted_class: str
    scores: tuple[ClassScore, ...]
    model_version: str
    preprocess_label: str
    explanation: PredictionExplanation | None = None
    """Presente solo cuando la peticion pidio explicacion: cuesta N pasadas extra."""

    @property
    def confidence(self) -> float:
        return next(
            score.confidence for score in self.scores if score.tumor_class == self.predicted_class
        )


@dataclass(frozen=True)
class ModelInfo:
    """Lo que el motor declara sobre el modelo que esta sirviendo."""

    model_version: str
    preprocess_label: str
    preprocess_fingerprint: str
    classes: tuple[str, ...]
    simulated: bool
    explanation_method: str = ""
    explanation_label: str = ""
    supports_explanation: bool = False
    """Lo decide el artefacto: es cierto si su firma declara el parametro `explain`."""


class ExplanationNotSupportedError(RuntimeError):
    """Se pidio una explicacion a un artefacto que no la sabe producir."""


class InferenceEngine(Protocol):
    """Contrato de inferencia."""

    def describe(self) -> ModelInfo:
        """Metadatos del modelo activo, expuestos por `GET /api/v1/meta`."""
        ...

    def classify(self, images: Sequence[bytes], *, explain: bool = False) -> list[InferenceResult]:
        """Clasifica imagenes crudas tal y como llegaron en la peticion.

        Args:
            images: bytes sin transformar.
            explain: pide ademas el mapa de influencia. Es opcional y viene
                apagado porque multiplica el coste de la inferencia; quien lo
                encienda debe saber que lo esta pagando.
        """
        ...
