# ml_project — ciclo de vida del modelo

Pipeline de ML de BrainNeuroScan. Implementa el patrón **Transform** (*Machine
Learning Design Patterns*, cap. 6): el preprocesamiento viaja **dentro** del
artefacto del modelo, de modo que entrenamiento e inferencia ejecutan
exactamente el mismo código.

> Estado: implementados el contrato de preprocesamiento, el empaquetado y el
> **pipeline de entrenamiento** (`pipelines/training.py`, `pipelines/train.py`).
> El entrenamiento se ejecuta en una máquina con datos y GPU (típicamente EC2)
> siguiendo `docs/runbook-entrenamiento-ec2-mlflow-s3.md`.

## El problema que resuelve

Antes, el preprocesamiento `224×224 · CLAHE` existía en tres sitios distintos:
una cadena escrita a mano en la interfaz, el código de entrenamiento y el
código del servicio. Cualquier cambio en uno sin replicarlo en los otros
degrada el modelo en producción **en silencio**: no hay error, solo peores
predicciones. Es la desviación entrenamiento-servicio.

Ahora hay un único lugar:

```
pipelines/preprocessing.py     ← única definición del preprocesamiento
        │
        ├─ entrenamiento: lo importa directamente
        └─ artefacto MLflow: lo empaqueta vía `code_paths`
                  │
                  └─ servicio: lo recibe con el modelo, no lo reimplementa
```

El servicio (`api/app/ml/mlflow_engine.py`) entrega **bytes de imagen**
al modelo y recibe probabilidades. No conoce el tamaño de entrada, ni CLAHE, ni
la normalización.

## Contrato del modelo empaquetado

| Aspecto | Definición |
|---|---|
| Entrada | DataFrame con una columna `image` de bytes (JPG o PNG) |
| Salida | DataFrame con una columna por clase (`glioma`, `meningioma`, `pituitary`, `healthy`) y su probabilidad |
| Artefactos | pesos ONNX, `preprocess_config.json`, `classifier_meta.json`, y el paquete `pipelines/` completo |
| Metadatos | `preprocess_fingerprint`, `preprocess_label`, `classes` |

La **huella** (`preprocess_fingerprint`) es un SHA-256 de la configuración. El
motor de inferencia puede exigir una huella concreta al arrancar y negarse a
servir si el artefacto declara otra: defensa en profundidad frente a un
empaquetado incorrecto.

La **etiqueta** (`preprocess_label`) es la cadena que muestra la interfaz. Se
deriva de la configuración real, así que la pantalla nunca puede mentir sobre
qué preprocesamiento se aplicó.

## Uso

```python
import mlflow
from pipelines.packaging import log_classifier
from pipelines.preprocessing import PreprocessConfig

with mlflow.start_run():
    log_classifier(
        "artifacts/effnetb3_bt_v2.5.onnx",
        sample_image=open("muestra.png", "rb").read(),
        preprocess_config=PreprocessConfig(),
        output_is_probability=False,
        registered_model_name="brain-tumor-classifier",
    )
```

Consumo desde el servicio:

```python
model = mlflow.pyfunc.load_model("models:/brain-tumor-classifier@champion")
probabilidades = model.predict(pd.DataFrame({"image": [bytes_de_la_imagen]}))
```

## Entrenamiento

Instala las dependencias de entrenamiento (torch/torchvision/scikit-learn, aparte
del runtime de servicio, que sigue siendo liviano):

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-train.txt
```

Ejecuta el pipeline apuntando a un servidor MLflow (el existente o uno nuevo en EC2):

```bash
.venv/bin/python -m pipelines.train \
    --data-dir ../data/brain-tumor-mri-scans \
    --arch cnn_simple --arch resnet18 --epochs 5 \
    --tracking-uri "$MLFLOW_TRACKING_URI" \
    --experiment brain-tumor-mri-classification
```

Cada arquitectura (CNN simple + ResNet18) se entrena en su propio run reutilizando
`preprocessing.py` (patrón «Transform») y la partición reproducible de
`dataset.py`. Se registran `params` y `metrics` (accuracy, precision, **recall**,
**F1 macro**), se empaqueta el ONNX con `log_classifier` y se elige **campeón** por
F1 macro fijando el alias `champion` (y `challenger` al segundo). El servidor es
parametrizable por `--tracking-uri` / `MLFLOW_TRACKING_URI`: el mismo comando sirve
para el existente (`https://mlflow.alexchirino.online`) o para uno nuevo en EC2.
Guía completa en [`docs/runbook-entrenamiento-ec2-mlflow-s3.md`](docs/runbook-entrenamiento-ec2-mlflow-s3.md).

## Pruebas

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

`tests/test_transform_parity.py` es la prueba que sostiene el patrón:

1. Verifica que `preprocessing.py` **viaja físicamente dentro** del artefacto.
2. Compara, sobre varias imágenes, el resultado del camino de entrenamiento
   (preprocesador local más sesión ONNX) contra el del camino de servicio
   (modelo cargado desde MLflow). Deben coincidir.
3. **Control negativo**: comprueba que un preprocesamiento distinto produce un
   resultado distinto. Sin esta comprobación, el punto 2 podría pasar por
   casualidad con un modelo insensible a la entrada.

El modelo ONNX de prueba se genera al vuelo y proyecta la entrada completa con
una matriz densa: cualquier píxel que difiera cambia la salida.

## Decisiones de diseño

- **Orden fijo**: escala de grises → redimensionado → CLAHE → normalización.
  CLAHE se aplica *después* del redimensionado para que la rejilla de teselas
  sea consistente sea cual sea el tamaño original de la imagen.
- **Replicado a 3 canales**: las MRI son monocromas, pero los backbones
  preentrenados en ImageNet esperan RGB. Se replica el canal y se normaliza con
  la media y desviación de ImageNet.
- **Robustez de entrada**: se aceptan 8 y 16 bits, escala de grises, RGB y RGBA.
  Las MRI de 16 bits se reescalan a 8 bits antes de CLAHE, que lo exige.
- **`PreprocessConfig` es inmutable**: cambiar un parámetro produce otra huella,
  y por tanto otro modelo. No hay forma silenciosa de alterar el preprocesamiento.
