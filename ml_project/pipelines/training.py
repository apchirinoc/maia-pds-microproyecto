"""Entrenamiento de los clasificadores (PyTorch).

Este modulo concentra lo unico que depende de un framework de deep learning; el
resto del pipeline (`preprocessing`, `dataset`, `packaging`) es agnostico. Por
eso torch y torchvision solo se necesitan aqui y viven en
`requirements-train.txt`, no en el runtime de servicio.

Piezas:

- `SimpleCNN`  : baseline convolucional con Dropout (≈ `CNN_Simple_Dropout`).
- `build_resnet18` : transfer learning sobre ImageNet (≈ `ResNet18_TransferLearning`).
- `MriTorchDataset` : lee bytes y aplica el MISMO `MriPreprocessor` que viaja en
  el artefacto de MLflow. Esta es la clave del patron «Transform»: entrenamiento
  e inferencia comparten preprocesamiento y no puede haber desviacion.
- `entrenar` / `evaluar` / `exportar_onnx` : el ciclo y su salida ONNX.

El modelo emite **logits** (sin softmax): el envoltorio de servicio
(`model_wrapper.py`) aplica softmax porque se empaqueta con
`output_is_probability=False`.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader, Dataset

from pipelines.config import TUMOR_CLASSES
from pipelines.dataset import RegistroImagen
from pipelines.dataset_io import cargar_bytes
from pipelines.preprocessing import MriPreprocessor, PreprocessConfig

Arquitectura = Literal["cnn_simple", "resnet18"]

CLASE_A_INDICE: dict[str, int] = {clase: indice for indice, clase in enumerate(TUMOR_CLASSES)}


@dataclass(frozen=True)
class TrainConfig:
    """Hiperparametros de una corrida de entrenamiento.

    Los valores por defecto reproducen el orden de magnitud de la Entrega 2
    (Adam, 5 epocas). `learning_rate` se deja configurable porque la ResNet18 uso
    `1e-5` y la CNN admite tasas mayores.
    """

    arch: Arquitectura = "cnn_simple"
    epochs: int = 5
    batch_size: int = 32
    learning_rate: float = 1e-4
    seed: int = 42
    val_fraction: float = 0.1
    num_workers: int = 0
    device: str | None = None
    pretrained: bool = True


class SimpleCNN(nn.Module):
    """Baseline: dos bloques convolucionales, aplanado, Dropout y capa densa.

    Con entrada `224×224` y dos `MaxPool2d(2)` el mapa cae a `56×56`; de ahi el
    tamano de la capa densa. Sale un vector de logits por clase.
    """

    def __init__(self, num_classes: int = len(TUMOR_CLASSES), dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        lado = PreprocessConfig().target_size // 4
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(64 * lado * lado, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def build_resnet18(num_classes: int = len(TUMOR_CLASSES), *, pretrained: bool = True) -> nn.Module:
    """ResNet18 con la ultima capa reemplazada para `num_classes` clases.

    torchvision se importa aqui dentro para que un entorno con torch pero sin
    torchvision pueda seguir usando `SimpleCNN`.
    """
    from torchvision import models as tv_models

    weights = tv_models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
    model = tv_models.resnet18(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def construir_modelo(config: TrainConfig) -> nn.Module:
    if config.arch == "cnn_simple":
        return SimpleCNN()
    if config.arch == "resnet18":
        return build_resnet18(pretrained=config.pretrained)
    raise ValueError(f"Arquitectura desconocida: {config.arch!r}")


class MriTorchDataset(Dataset):
    """Adapta `RegistroImagen` + indice de rutas al `Dataset` de PyTorch.

    En cada acceso lee los bytes por identificador y les aplica el preprocesador
    compartido, devolviendo `(tensor (3,S,S), indice_de_clase)`.
    """

    def __init__(
        self,
        registros: Sequence[RegistroImagen],
        indice: dict[str, Path],
        preprocessor: MriPreprocessor,
    ) -> None:
        self._registros = list(registros)
        self._indice = indice
        self._preprocessor = preprocessor

    def __len__(self) -> int:
        return len(self._registros)

    def __getitem__(self, posicion: int) -> tuple[torch.Tensor, int]:
        registro = self._registros[posicion]
        tensor = self._preprocessor.from_bytes(cargar_bytes(self._indice, registro.identificador))
        return torch.from_numpy(np.ascontiguousarray(tensor)), CLASE_A_INDICE[registro.clase]


def _resolver_device(config: TrainConfig) -> torch.device:
    if config.device:
        return torch.device(config.device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def separar_validacion(
    train_records: Sequence[RegistroImagen], val_fraction: float, seed: int
) -> tuple[list[RegistroImagen], list[RegistroImagen]]:
    """Talla una validacion del train de forma determinista.

    `dataset.py` particiona en train/test; la validacion se obtiene aqui barajando
    con semilla fija sobre los identificadores ordenados, de modo que dos
    ejecuciones con la misma semilla vean exactamente la misma validacion.
    """
    if val_fraction <= 0:
        return list(train_records), []
    ordenados = sorted(train_records, key=lambda registro: registro.identificador)
    random.Random(seed).shuffle(ordenados)
    corte = int(len(ordenados) * val_fraction)
    return ordenados[corte:], ordenados[:corte]


@torch.no_grad()
def evaluar(
    model: nn.Module,
    registros: Sequence[RegistroImagen],
    indice: dict[str, Path],
    *,
    device: torch.device | None = None,
    batch_size: int = 32,
) -> dict[str, float]:
    """Metricas macro sobre un conjunto: accuracy, precision, recall y F1.

    Se priorizan recall y F1 macro, las metricas que la Entrega 2 declaro
    criticas para el dominio clinico.
    """
    if not registros:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
    device = device or torch.device("cpu")
    model.eval()
    cargador = DataLoader(
        MriTorchDataset(registros, indice, MriPreprocessor()), batch_size=batch_size
    )
    y_true: list[int] = []
    y_pred: list[int] = []
    for lote, etiquetas in cargador:
        salidas = model(lote.to(device))
        y_pred.extend(salidas.argmax(dim=1).cpu().numpy().tolist())
        y_true.extend(etiquetas.numpy().tolist())

    etiquetas_posibles = list(range(len(TUMOR_CLASSES)))
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", labels=etiquetas_posibles, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def entrenar(
    config: TrainConfig,
    train_records: Sequence[RegistroImagen],
    indice: dict[str, Path],
    *,
    val_records: Sequence[RegistroImagen] | None = None,
    al_terminar_epoca: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[nn.Module, list[dict[str, Any]]]:
    """Entrena `config.arch` y devuelve el modelo y el historial por epoca.

    Si no se pasa `val_records`, se talla una validacion del train con
    `separar_validacion`. El historial guarda la perdida de entrenamiento y las
    metricas de validacion de cada epoca.
    """
    device = _resolver_device(config)
    torch.manual_seed(config.seed)

    if val_records is None:
        train_records, val_records = separar_validacion(
            train_records, config.val_fraction, config.seed
        )

    cargador = DataLoader(
        MriTorchDataset(train_records, indice, MriPreprocessor()),
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
    )
    model = construir_modelo(config).to(device)
    optimizador = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterio = nn.CrossEntropyLoss()

    historial: list[dict[str, Any]] = []
    for epoca in range(1, config.epochs + 1):
        model.train()
        acumulada, total = 0.0, 0
        for lote, etiquetas in cargador:
            lote, etiquetas = lote.to(device), etiquetas.to(device)
            optimizador.zero_grad()
            perdida = criterio(model(lote), etiquetas)
            perdida.backward()
            optimizador.step()
            acumulada += float(perdida.item()) * lote.size(0)
            total += lote.size(0)

        registro_epoca: dict[str, Any] = {
            "epoch": epoca,
            "train_loss": acumulada / max(total, 1),
        }
        if val_records:
            for clave, valor in evaluar(
                model, val_records, indice, device=device, batch_size=config.batch_size
            ).items():
                registro_epoca[f"val_{clave}"] = valor
        historial.append(registro_epoca)
        if al_terminar_epoca is not None:
            al_terminar_epoca(registro_epoca)

    return model, historial


def exportar_onnx(
    model: nn.Module,
    destino: str | Path,
    *,
    opset: int = 13,
    device: torch.device | None = None,
) -> Path:
    """Exporta el modelo a ONNX con eje de lote dinamico.

    La firma resultante (`input: float32[N,3,S,S]` -> `output: float32[N,C]`)
    coincide con lo que espera `model_wrapper.py`: el envoltorio pasa el tensor
    ya preprocesado y lee logits.
    """
    device = device or torch.device("cpu")
    model = model.to(device).eval()
    lado = PreprocessConfig().target_size
    ejemplo = torch.zeros(1, 3, lado, lado, device=device)

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # `dynamo=False` usa el exportador clasico (TorchScript): produce un unico
    # `.onnx` con los pesos embebidos —imprescindible porque `log_classifier`
    # empaqueta un solo fichero— y respeta `dynamic_axes` para el eje de lote.
    # El exportador dynamo, en cambio, puede externalizar los pesos a un fichero
    # aparte que no viajaria en el artefacto.
    torch.onnx.export(
        model,
        ejemplo,
        str(destino),
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        opset_version=opset,
        dynamo=False,
    )
    return destino
