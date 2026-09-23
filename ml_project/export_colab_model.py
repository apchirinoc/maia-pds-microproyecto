"""Exporta los pesos ya entrenados del notebook Colab. No inicia entrenamiento."""
import argparse
import io
import json
import tempfile
from pathlib import Path

import mlflow
import mlflow.pytorch
import numpy as np
import pandas as pd
import torch
from PIL import Image
from torchvision import transforms

from pipelines.packaging import log_classifier
from pipelines.preprocessing import PreprocessConfig, MriPreprocessor
from pipelines.training import exportar_onnx

# Orden publicado por dataset.classes en PdS_Training_Experiments.ipynb, celda 6.
COLAB_CLASSES = ("glioma", "healthy", "meningioma", "pituitary")


def export_package(model, images, output, *, version, run_id, metrics=None, architecture=None):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"El destino ya existe: {output}")
    if not images:
        raise ValueError("Incluya al menos una imagen para comprobar la exportación")
    config = PreprocessConfig(mode="rgb_imagenet")
    reference = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize(config.mean, config.std),
    ])
    tensors = []
    for content in images:
        with Image.open(io.BytesIO(content)) as image:
            tensor = reference(image.convert("RGB"))
        np.testing.assert_allclose(MriPreprocessor(config).from_bytes(content), tensor.numpy(), atol=1e-6)
        tensors.append(tensor)
    model = model.cpu().eval()
    with torch.no_grad():
        expected = torch.softmax(model(torch.stack(tensors)), dim=1).numpy()
    if expected.shape != (len(images), 4):
        raise ValueError("El modelo del notebook debe producir cuatro logits por imagen")
    if not np.isfinite(expected).all():
        raise ValueError("El modelo produjo probabilidades no finitas")
    output.parent.mkdir(parents=True, exist_ok=True)
    # No dejar un paquete distribuible cuando falle la comparación de salidas.
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".export-") as temporary:
        weights = exportar_onnx(model, Path(temporary) / "classifier.onnx")
        package = Path(temporary) / "classifier"
        log_classifier(
            weights, sample_image=images[0], preprocess_config=config, classes=COLAB_CLASSES,
            output_directory=package,
            extra_metadata={
                "model_version": version, "source_run_id": run_id,
                "architecture": architecture or type(model).__name__, "evaluation_metrics": metrics or {},
                "metric_averaging": "weighted",
                "training_notebook_commit": "0c761332916d25432dffea70fbf7481457330999",
            },
        )
        loaded = mlflow.pyfunc.load_model(str(package))
        actual = loaded.predict(pd.DataFrame({"image": images}))
        if tuple(actual.columns) != COLAB_CLASSES:
            raise ValueError("El paquete cambió el orden de clases")
        np.testing.assert_allclose(actual.to_numpy(), expected, rtol=1e-4, atol=1e-5)
        result = {"classes": list(COLAB_CLASSES), "preprocess_fingerprint": config.fingerprint,
                  "model_version": version, "source_run_id": run_id,
                  "weights_sha256": loaded.metadata.metadata["weights_sha256"],
                  "sample_count": len(images),
                  "max_probability_difference": float(np.max(np.abs(actual.to_numpy() - expected)))}
        (package / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        package.rename(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-uri", required=True)
    parser.add_argument("--tracking-uri")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--architecture", help="Arquitectura declarada por el entrenamiento")
    parser.add_argument("--metrics", type=Path, help="JSON de métricas del run para exportar sin MLflow")
    parser.add_argument("--sample", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.tracking_uri:
        mlflow.set_tracking_uri(args.tracking_uri)
    # Sólo leer artefactos confiables del equipo: el notebook los guardó con pickle.
    model = mlflow.pytorch.load_model(args.model_uri, map_location="cpu")
    if args.metrics:
        metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
        if not isinstance(metrics, dict):
            parser.error("--metrics debe contener un objeto JSON de métricas")
    else:
        metrics = mlflow.tracking.MlflowClient().get_run(args.run_id).data.metrics if args.tracking_uri else {}
    result = export_package(model, [sample.read_bytes() for sample in args.sample], args.output,
                            version=args.version, run_id=args.run_id, metrics=metrics,
                            architecture=args.architecture)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
