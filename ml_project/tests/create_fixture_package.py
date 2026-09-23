"""Genera un paquete ONNX sintético para integración. No es un modelo entrenado."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import build_dense_onnx_model, encode_synthetic_mri
from pipelines.packaging import log_classifier
from pipelines.preprocessing import PreprocessConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    config = PreprocessConfig(target_size=32)
    weights = build_dense_onnx_model(args.output.parent / "fixture.onnx", config)
    sample = encode_synthetic_mri()
    log_classifier(
        weights, sample_image=sample, preprocess_config=config,
        output_directory=args.output,
        extra_metadata={"model_version": "fixture-1", "architecture": "SYNTHETIC TEST ONLY"},
    )
    (args.output.parent / "fixture.png").write_bytes(sample)
    print(f"Synthetic integration fixture only: {args.output}")


if __name__ == "__main__":
    main()
