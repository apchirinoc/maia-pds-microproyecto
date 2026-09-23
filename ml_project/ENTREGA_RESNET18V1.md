# Descargar y preparar ResNet18 para BrainNeuroScan

El paquete PyTorch del equipo ya es descargable. La API utiliza su conversión a ONNX con preprocesamiento incluido; no configure el PyTorch original directamente en la API.

| Dato | Valor comprobado |
|---|---|
| Tracking | https://mlflow.alexchirino.online/ |
| Experimento | `3`, `brain-tumor-mri-v2` |
| Run de publicación | `f89f4f1604cd4c02b66b4d19155e4d24` |
| URI descargable | `models:/m-994b5e15a2be4cd99280ca696ae54d8f` |
| Arquitectura | ResNet18, cuatro salidas |
| SHA-256 de `data/model.pth` | `97cd677a1018be085d19b8b8682ab24c56dcabd47d6c4502b14066e851e5c0ac` |

La URI identifica un logged model. No presupone una versión del registro ResNet18v1; las versiones antiguas apuntan a otros artefactos. Este run no contiene métricas. Las métricas del run anterior `f2b05ec8c58649529b2338a17b0db96f` no se incorporan sin confirmar que corresponden a estos pesos.

## Descargar el original

Use Python 3.13 y MLflow 3.16.1. Desde la raíz del repositorio, en PowerShell:

```powershell
$env:MLFLOW_TRACKING_URI = 'https://mlflow.alexchirino.online/'
mlflow artifacts download `
  --artifact-uri 'models:/m-994b5e15a2be4cd99280ca696ae54d8f' `
  --dst-path ./modelo-recibido
Get-FileHash ./modelo-recibido/data/model.pth -Algorithm SHA256
```

Conserve toda la carpeta, incluidos MLmodel, data/, requirements.txt y archivos de entorno. La descarga necesita que MLflow esté encendido. El paquete descargado permite continuar sin conexión al laboratorio.

## Convertir para la API

Instale `ml_project/requirements-train.txt`. Para recuperar estos pesos se comprobaron Python 3.13, MLflow 3.16.1, PyTorch 2.11.0 y torchvision 0.26.0. Se pueden usar las distribuciones CPU; el contenedor final no necesita PyTorch.

Desde la raíz del repositorio:

```powershell
python ml_project/export_colab_model.py `
  --model-uri ./modelo-recibido `
  --run-id f89f4f1604cd4c02b66b4d19155e4d24 `
  --version m-994b5e15a2be4cd99280ca696ae54d8f `
  --architecture ResNet18 `
  --sample ./web/public/samples/Te-gl_0023.jpg ./web/public/samples/Te-no_0109.jpg ./web/public/samples/Te-me_0015.jpg ./web/public/samples/Te-pi_0204.jpg `
  --output ./artifacts/classifier
```

El destino debe estar libre. El exportador rechaza sobrescribir un paquete y solo crea el resultado después de comprobar la equivalencia. Usa RGB, resize bilineal a 224 × 224, ToTensor y normalización ImageNet, sin CLAHE. Conserva el orden glioma, healthy, meningioma, pituitary del notebook.

Las cuatro muestras superaron la comparación PyTorch/ONNX con `rtol=1e-4`, `atol=1e-5` y diferencia absoluta máxima `5.960464477539062e-07`. Esto verifica conversión, no una nueva medición de exactitud.

`validation.json` conserva procedencia, hash del ONNX y huella de preprocesamiento. En la conversión comprobada, el SHA-256 del ONNX fue `3a2a163e2c7775dbc56bd92d17d97db3c92c307aba52211ef219bf397c61e483` y la huella fue `3550069770ff4bc4`. Otras versiones de herramientas pueden generar otro archivo ONNX; compruebe siempre su propia validación.

## Ejecutar en Docker

Conserve completa `artifacts/classifier/`. Configure en `.env`:

```dotenv
MODEL_DIRECTORY=./artifacts
MLFLOW_MODEL_URI=/models/classifier
MLFLOW_MODEL_NAME=ResNet18v1
MLFLOW_MODEL_VERSION=
MLFLOW_TRACKING_URI=
EXPECTED_PREPROCESS_FINGERPRINT=3550069770ff4bc4
```

La versión se obtiene de los metadatos del paquete. La migración `data-platform/scripts/ddl/12_inferencia_real.sql` admite el identificador completo en el catálogo. Aplíquela en instalaciones anteriores siguiendo el manual.

La prueba local en Docker comprobó clasificación con estos pesos, guardado en PostgreSQL, exportación del historial, selección de muestras y carga de archivo desde el tablero. No acredita el despliegue público. Siga el [manual de instalación](../docs/MANUAL_INSTALACION.md) para arrancar y comprobar cada instalación.
