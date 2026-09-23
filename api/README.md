# api — API de BrainNeuroScan

API REST en **FastAPI** que sirve la plataforma. Publica su contrato en
OpenAPI 3.1: Swagger en `/docs`, ReDoc en `/redoc` y el esquema en
`/openapi.json`.

> ⚠️ Prototipo de investigación. No es un dispositivo médico y no cuenta con
> certificaciones vigentes. Con `INFERENCE_ENGINE=simulated` la inferencia es
> simulada y así lo declara `GET /api/v1/meta`.

## Arranque

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload
```

Con Docker:

```bash
cp .env.example .env
docker compose up --build
```

## Variables de entorno

Ver `.env.example`. Las que más importan:

| Variable | Efecto |
|---|---|
| `ALLOWED_ORIGINS` | Orígenes CORS autorizados. Sin el origen del frontend, el navegador bloquea las respuestas |
| `JWT_SECRET` | Firma de los tokens. En `ENVIRONMENT=production` el arranque **falla** si conserva el valor de ejemplo |
| `DATA_SOURCE` | `seed` (memoria) o `postgres` (fases 9-15 del plan) |
| `INFERENCE_ENGINE` | `simulated` u `onnx` (artefacto de MLflow) |
| `MLFLOW_TRACKING_URI` | Servidor MLflow. **Obligatoria** con `INFERENCE_ENGINE=onnx`: sin ella el arranque falla |
| `MLFLOW_MODEL_NAME` / `MLFLOW_MODEL_ALIAS` | Modelo que se sirve (`brain-tumor-classifier@champion` por defecto) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` | Lectura del artifact store en S3 cuando no hay rol IAM (p. ej. Railway) |
| `DEMO_USERNAME` / `DEMO_PASSWORD` | Cuenta del prototipo; deben coincidir con las del frontend |

### Inferencia real

Con `INFERENCE_ENGINE=onnx` la API resuelve el alias en el registry, descarga
el artefacto empaquetado con `log_classifier` (ONNX + preprocesamiento) al
arrancar y lo usa en `POST /api/v1/classifications`, que entonces exige el
archivo de la imagen. Activar otra versión desde el tablero
(`POST /api/v1/models/registry/{version}/activate`) recarga el motor. La imagen
Docker instala `requirements-onnx.txt`, así que sirve en ambos modos.

## Contrato

Los esquemas se serializan en **camelCase** mediante un generador de alias, de
modo que el JSON encaja con los tipos TypeScript del frontend sin adaptadores.
El código Python conserva `snake_case`.

- Paginación con envolvente única `{items, total, page, pageSize}`.
- Errores normalizados según **RFC 7807** (`application/problem+json`).
- Cabecera `X-Process-Time-Ms` con la latencia real, que el frontend muestra.

## Endpoints

| Grupo | Rutas |
|---|---|
| Meta | `GET /health`, `GET /api/v1/meta` |
| Auth | `POST /api/v1/auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Catálogos | `GET /api/v1/countries` |
| Panel | `GET /api/v1/dashboard/{kpis,training-distribution,uploads-by-country,uploads-by-month,recent-profile,dataset-samples}` |
| Modelos | `GET /api/v1/models`, `/models/summary`, `/models/{id}`, `POST /models/{id}/deploy`, `POST /models/{id}/revert` |
| Cargas | `GET /api/v1/uploads`, `/uploads/summary`, `/uploads/export`, `POST /uploads/{id}/ground-truth`, `POST /uploads/add-to-dataset` |
| Clasificación | `POST /api/v1/classifications`, `GET /classifications/model-info` |

`/health` es deliberadamente barato y sin autenticación: el frontend lo consulta
al arrancar y de forma periódica para decidir si muestra datos reales o
simulados.

## Origen de datos

Con `DATA_SOURCE=seed` los datos viven en `app/seed/`. El generador de
`app/seed/cargas.py` es una **réplica exacta** del de
`web/src/mocks/uploads.mock.ts`: mismo generador congruencial, mismas
semillas y mismo orden de consumo. Conectar o desconectar el backend no cambia
los datos que se ven; sólo cambia su procedencia, que es justo lo que permite
comprobar que la conmutación funciona.

