"""Empaqueta pesos existentes; no entrena ni escribe en MLflow remoto."""
import argparse
import json
from pathlib import Path

import mlflow
import pandas as pd
import numpy as np

from pipelines.packaging import log_classifier
from pipelines.preprocessing import PreprocessConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", type=Path, required=True)
    parser.add_argument("--preprocess-config", type=Path, required=True)
    parser.add_argument("--classes", nargs=4, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--probabilities", action="store_true")
    args = parser.parse_args()
    if set(args.classes) != {"glioma", "meningioma", "pituitary", "healthy"}:
        parser.error("Declare las cuatro clases en el orden de salida del modelo entrenado")
    config = PreprocessConfig.from_json(args.preprocess_config.read_text(encoding="utf-8"))
    metrics = json.loads(args.metrics.read_text(encoding="utf-8")) if args.metrics else {}
    image = args.sample.read_bytes()
    log_classifier(
        args.onnx, sample_image=image, preprocess_config=config, classes=args.classes,
        output_is_probability=args.probabilities, output_directory=args.output,
        extra_metadata={
            "model_version": args.version, "source_run_id": args.run_id,
            "architecture": args.architecture, "evaluation_metrics": metrics,
        },
    )
    loaded = mlflow.pyfunc.load_model(str(args.output))
    predictions = loaded.predict(pd.DataFrame({"image": [image]}))
    scores = predictions.to_numpy()
    if not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1) or not np.allclose(scores.sum(axis=1), 1):
        raise ValueError("El paquete no devuelve probabilidades válidas")
    print(predictions.to_json(orient="records"))
    print(f"Paquete portable: {args.output.resolve()}")


if __name__ == "__main__":
    main()
