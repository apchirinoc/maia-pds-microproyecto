# Runbook — Entrenamiento y versionamiento con MLflow en EC2 + S3

Guía paso a paso para **entrenar los modelos en una máquina EC2**, **versionarlos
en S3** (artifact store de MLflow) y **disponibilizarlos en la solución** (la API
los carga desde S3 y la interfaz permite seleccionarlos).

El servidor MLflow es **parametrizable**: puedes usar el **existente**
(`https://mlflow.alexchirino.online`) o **montar uno nuevo en EC2**. Todo se
controla con la variable `MLFLOW_TRACKING_URI`; el código no cambia.

```
EC2 (entrenamiento)                     S3                         API (FastAPI)            Web
────────────────────                    ──                         ─────────────            ───
git clone + dvc pull                    s3://<bucket>/mlflow-...    INFERENCE_ENGINE=onnx    Admin → Gestión de modelos
python -m pipelines.train ──runs/artefactos──►  pesos ONNX + code  ◄── models:/…@champion    "Seleccionar del registro" → Activar
   · CNN + ResNet18                     Model Registry             (MlflowInferenceEngine)   (fija alias champion)
   · elige champion por F1              brain-tumor-classifier
MLflow Tracking ── MLFLOW_TRACKING_URI ──►  existente  ó  nuevo en EC2 (:5000)
```

---

## 0. Prerrequisitos AWS

- Cuenta AWS con permiso para crear EC2, S3 e IAM.
- **Bucket S3** para artefactos de MLflow, p. ej. `s3://brainneuroscan-mlflow/` (y,
  si usas DVC con remoto S3, el bucket de datos).
- **Rol IAM** para la instancia EC2 con acceso al bucket (política mínima:
  `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` sobre ese bucket). Preferir rol
  IAM a llaves en disco.
- **Security group**: 22 (SSH). Si montas MLflow nuevo y quieres ver su UI, 5000
  (restringido a tu IP o vía túnel SSH / VPN; nunca 0.0.0.0/0 abierto).

## 1. Provisionar la instancia EC2

- **AMI**: *Deep Learning AMI (Ubuntu)* si usarás GPU, o Ubuntu 22.04 + drivers.
- **Tipo**: `g4dn.xlarge` (GPU T4) para ResNet18; una CPU (`c6i.xlarge`) basta para
  la CNN simple pero ResNet18 será lenta.
- Adjunta el **rol IAM** del paso 0 y tu **key pair**.
- Conéctate: `ssh -i clave.pem ubuntu@<IP_EC2>`.

## 2. Preparar la instancia

```bash
sudo apt-get update && sudo apt-get install -y git python3-venv python3-pip
# Si es GPU, verifica el driver:  nvidia-smi
python3 -m venv ~/venv && source ~/venv/bin/activate
```

## 3. Clonar el repositorio

```bash
git clone https://github.com/apchirinoc/maia-pds-microproyecto.git
cd maia-pds-microproyecto
git checkout feature/prototype-brain-mri   # o la rama correspondiente
```

## 4. Credenciales AWS

Con **rol IAM** en la instancia no hace falta nada. Si no, exporta:

```bash
export AWS_DEFAULT_REGION=us-east-1
# (solo si no hay rol IAM) export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...
```

## 5. Elegir el servidor MLflow (parametrizable)

### Opción 1 · Reutilizar el servidor existente

No montas nada; solo apuntas a él:

```bash
export MLFLOW_TRACKING_URI=https://mlflow.alexchirino.online
```

Asegúrate de tener credenciales del bucket S3 que ese servidor use como artifact
store (paso 4).

### Opción 2 · Montar un MLflow nuevo en EC2

```bash
pip install "mlflow>=3,<4" boto3 psycopg2-binary
# Backend store: Postgres (RDS o local) o, para pruebas, sqlite.
mlflow server \
  --backend-store-uri postgresql://usuario:clave@host:5432/mlflow \
  --default-artifact-root s3://brainneuroscan-mlflow/mlflow-artifacts \
  --host 0.0.0.0 --port 5000
# Déjalo como servicio systemd para producción.
export MLFLOW_TRACKING_URI=http://<IP_EC2>:5000
```

> Compatibilidad: el pipeline registra siempre bajo
> `REGISTERED_MODEL_NAME=brain-tumor-classifier` y en el experimento que indiques
> con `--experiment`. Si reutilizas el servidor existente, los nuevos runs y el
> modelo conviven con los de la Entrega 2 (`mri-cnn-simple-model`,
> `ResNet18_TransferLearning`) sin colisionar.

## 6. Descargar los datos (DVC)

```bash
pip install -r requirements.dvc.txt
dvc pull -r public                       # o el remoto S3 configurado
unzip -d data/ data/brain-tumor-mri-scans.zip
```

Verifica que existan carpetas de clase (`glioma`, `meningioma`, `pituitary`,
`notumor`/`healthy`) bajo `data/brain-tumor-mri-scans/`.

## 7. Instalar dependencias de entrenamiento

```bash
cd ml_project
pip install -r requirements-train.txt    # torch, torchvision, scikit-learn + runtime
```

## 8. Ejecutar el entrenamiento

```bash
python -m pipelines.train \
  --data-dir ../data/brain-tumor-mri-scans \
  --arch cnn_simple --arch resnet18 \
  --epochs 5 \
  --tracking-uri "$MLFLOW_TRACKING_URI" \
  --experiment brain-tumor-mri-classification
```

Qué hace: escanea el dataset, particiona de forma reproducible (con guard
anti-fuga), entrena cada arquitectura en su propio run, registra `params` y
`metrics` (accuracy, precision, **recall**, **F1 macro**), empaqueta el modelo
campeón/candidato en el Model Registry (`brain-tumor-classifier`) y fija los alias
`champion` (mejor F1) y `challenger`.

Banderas útiles: `--lr`, `--batch-size`, `--seed`, `--no-register` (ensayo local
sin tocar el registry).

## 9. Verificar

- **MLflow UI**: dos runs con métricas; el modelo `brain-tumor-classifier` con sus
  versiones y el alias `champion`.
- **S3**: artefactos bajo `s3://<bucket>/mlflow-artifacts/...` (pesos ONNX +
  `preprocess_config.json` + el paquete `pipelines/`).

## 10. Conectar la API (servir desde S3)

En el entorno de la API:

```bash
export INFERENCE_ENGINE=onnx
export MLFLOW_TRACKING_URI="$MLFLOW_TRACKING_URI"   # el mismo servidor
export MLFLOW_MODEL_NAME=brain-tumor-classifier
export MLFLOW_MODEL_ALIAS=champion
export AWS_DEFAULT_REGION=us-east-1                 # + credenciales/rol para S3
pip install -r requirements-onnx.txt               # onnxruntime, opencv, numpy, pandas
```

Reinicia la API. `MlflowInferenceEngine` cargará `models:/brain-tumor-classifier@champion`
desde S3 y servirá inferencia real.

## 11. Seleccionar el modelo desde la interfaz

En el tablero: **Admin → Gestión de modelos → «Seleccionar del registro»**. Se
listan las versiones versionadas en S3/MLflow (`GET /api/v1/models/registry`); al
pulsar **Activar** en una versión se fija su alias `champion`
(`POST /api/v1/models/registry/{version}/activate`) y la API pasa a servir esa
versión. Ya **no se sube un archivo**: se elige uno de los ya versionados.

## 12. Costos, seguridad y apagado

- **Apaga o termina la EC2** al acabar (la GPU cuesta por hora).
- **No** guardes credenciales en el repo ni en la imagen; usa rol IAM.
- Expón MLflow tras VPN/túnel SSH o con autenticación; evita el puerto 5000 abierto.
- Política IAM mínima sobre el bucket; separa el bucket de datos del de artefactos si
  quieres permisos más finos.
