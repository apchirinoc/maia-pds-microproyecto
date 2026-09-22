"""CLI de entrenamiento y versionamiento con MLflow.

Encadena el pipeline completo:

  escanear dataset -> particionar (Repeatable Splitting) -> snapshot + guard
  anti-fuga -> entrenar cada arquitectura -> evaluar en test -> registrar
  parametros, metricas y el artefacto ONNX empaquetado en MLflow -> elegir
  campeon por F1 macro y fijar los alias `champion`/`challenger`.

El servidor MLflow es **parametrizable**: `--tracking-uri` (o la variable de
entorno `MLFLOW_TRACKING_URI`) permite apuntar al servidor existente
(`https://mlflow.alexchirino.online`) o a uno nuevo montado en EC2, sin cambiar
el codigo.

Uso tipico (ver `ml_project/docs/runbook-entrenamiento-ec2-mlflow-s3.md`):

    python -m pipelines.train \\
        --data-dir ../data/brain-tumor-mri-scans \\
        --arch cnn_simple --arch resnet18 --epochs 5 \\
        --tracking-uri "$MLFLOW_TRACKING_URI" \\
        --experiment brain-tumor-mri-classification
"""

from __future__ import annotations

import argparse
import logging
import tempfile
from pathlib import Path
from typing import Any, Sequence

import mlflow
from mlflow.tracking import MlflowClient

from pipelines.config import CHALLENGER_ALIAS, CHAMPION_ALIAS, REGISTERED_MODEL_NAME
from pipelines.dataset import (
    DatasetSnapshot,
    ParticionDataset,
    SplitConfig,
    guard_antes_de_entrenar,
    particionar,
)
from pipelines.dataset_io import cargar_bytes, conteo_por_clase, escanear_directorio
from pipelines.packaging import log_classifier
from pipelines.preprocessing import PreprocessConfig

logger = logging.getLogger("pipelines.train")

ARQUITECTURAS_VALIDAS: tuple[str, ...] = ("cnn_simple", "resnet18")


def _parsear_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entrena y versiona los clasificadores de BrainNeuroScan en MLflow."
    )
    parser.add_argument("--data-dir", required=True, help="Directorio con las carpetas de clase.")
    parser.add_argument(
        "--arch",
        action="append",
        choices=ARQUITECTURAS_VALIDAS,
        dest="arch",
        help="Arquitectura a entrenar; repetible. Por defecto ambas.",
    )
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--tracking-uri",
        default=None,
        help="URI del servidor MLflow (o usa la variable MLFLOW_TRACKING_URI).",
    )
    parser.add_argument("--experiment", default="brain-tumor-mri-classification")
    parser.add_argument("--registered-model-name", default=REGISTERED_MODEL_NAME)
    parser.add_argument(
        "--no-register",
        action="store_true",
        help="Entrena y registra metricas, pero no empaqueta ni versiona en el registry.",
    )
    args = parser.parse_args(argv)
    if not args.arch:
        args.arch = list(ARQUITECTURAS_VALIDAS)
    return args


def _entrenar_una(
    training: Any,
    arch: str,
    config: Any,
    particion: ParticionDataset,
    indice: dict[str, Path],
    snapshot: DatasetSnapshot,
    muestra: bytes,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Una corrida completa dentro de su propio run de MLflow."""
    with mlflow.start_run(run_name=arch) as run:
        model, historial = training.entrenar(config, particion.train, indice)
        metricas = training.evaluar(model, particion.test, indice)

        mlflow.log_params(
            {
                "arch": arch,
                "epochs": config.epochs,
                "batch_size": config.batch_size,
                "learning_rate": config.learning_rate,
                "seed": config.seed,
                "preprocess_fingerprint": PreprocessConfig().fingerprint,
                "dataset_snapshot": snapshot.snapshot_id,
                "dataset_huella": snapshot.huella,
                "train_size": len(particion.train),
                "test_size": len(particion.test),
            }
        )
        mlflow.log_metrics({f"test_{clave}": valor for clave, valor in metricas.items()})
        for fila in historial:
            mlflow.log_metrics(
                {clave: valor for clave, valor in fila.items() if clave != "epoch"},
                step=int(fila["epoch"]),
            )

        version: str | None = None
        with tempfile.TemporaryDirectory() as staging:
            onnx_path = training.exportar_onnx(model, Path(staging) / f"{arch}.onnx")
            snapshot_path = Path(staging) / "dataset_snapshot.json"
            snapshot_path.write_text(snapshot.to_json(indent=2), encoding="utf-8")
            mlflow.log_artifact(str(snapshot_path))

            if not args.no_register:
                info = log_classifier(
                    onnx_path,
                    sample_image=muestra,
                    preprocess_config=PreprocessConfig(),
                    output_is_probability=False,
                    registered_model_name=args.registered_model_name,
                    extra_metadata={
                        "arch": arch,
                        "dataset_snapshot": snapshot.snapshot_id,
                        "dataset_huella": snapshot.huella,
                        **{f"test_{clave}": valor for clave, valor in metricas.items()},
                    },
                )
                version = getattr(info, "registered_model_version", None)

        logger.info("[%s] test=%s version=%s", arch, metricas, version)
        return {"arch": arch, "run_id": run.info.run_id, "metrics": metricas, "version": version}


def _asignar_aliases(resultados: list[dict[str, Any]], registered_model_name: str) -> None:
    """Fija `champion` al mejor por F1 macro (desempate por recall) y `challenger` al siguiente."""
    con_version = [resultado for resultado in resultados if resultado["version"] is not None]
    if not con_version:
        logger.warning("Ningun modelo se registro; no se asignan alias.")
        return

    ordenados = sorted(
        con_version,
        key=lambda resultado: (resultado["metrics"]["f1"], resultado["metrics"]["recall"]),
        reverse=True,
    )
    cliente = MlflowClient()
    cliente.set_registered_model_alias(
        registered_model_name, CHAMPION_ALIAS, ordenados[0]["version"]
    )
    logger.info(
        "champion -> version %s (%s, F1=%.4f)",
        ordenados[0]["version"],
        ordenados[0]["arch"],
        ordenados[0]["metrics"]["f1"],
    )
    if len(ordenados) > 1:
        cliente.set_registered_model_alias(
            registered_model_name, CHALLENGER_ALIAS, ordenados[1]["version"]
        )
        logger.info("challenger -> version %s (%s)", ordenados[1]["version"], ordenados[1]["arch"])


def main(argv: Sequence[str] | None = None) -> list[dict[str, Any]]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parsear_args(argv)

    # torch se importa aqui: si falta, el error aparece al ejecutar, no al
    # importar el modulo (asi `--help` y los tests de otras piezas no lo exigen).
    from pipelines import training

    registros, indice = escanear_directorio(args.data_dir)
    logger.info("Imagenes etiquetadas: %s %s", len(registros), conteo_por_clase(registros))

    particion = particionar(registros, SplitConfig())
    snapshot = DatasetSnapshot.desde_particion(particion)
    guard_antes_de_entrenar(snapshot)
    logger.info(
        "Snapshot %s (huella %s) | train=%s test=%s",
        snapshot.snapshot_id,
        snapshot.huella,
        len(particion.train),
        len(particion.test),
    )

    if args.tracking_uri:
        mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment)

    muestra = cargar_bytes(indice, particion.train[0].identificador)

    resultados: list[dict[str, Any]] = []
    for arch in args.arch:
        config = training.TrainConfig(
            arch=arch,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            seed=args.seed,
        )
        resultados.append(
            _entrenar_una(training, arch, config, particion, indice, snapshot, muestra, args)
        )

    if not args.no_register:
        _asignar_aliases(resultados, args.registered_model_name)

    return resultados


if __name__ == "__main__":  # pragma: no cover
    main()
