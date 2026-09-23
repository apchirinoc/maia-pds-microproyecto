# Ejecutar y verificar la inferencia

`POST /api/v1/classifications` ejecuta el paquete cargado al arrancar cuando `INFERENCE_ENGINE=onnx`. Si el paquete falta o incumple el contrato, el arranque falla. No se sustituye por una clasificación simulada.

## Configuración

Instale `requirements-onnx.txt` y configure:

```dotenv
INFERENCE_ENGINE=onnx
MLFLOW_MODEL_URI=/ruta/al/paquete/classifier
MLFLOW_MODEL_NAME=nombre-del-modelo
DATA_SOURCE=postgres
DATABASE_URL=postgresql://usuario:clave@servidor:5432/base
ALLOWED_ORIGINS=http://localhost:8080
ENVIRONMENT=production
DEBUG=false
JWT_SECRET=SECRETO_ALEATORIO_DE_AL_MENOS_32_CARACTERES
```

`MLFLOW_MODEL_URI` puede señalar un paquete local o una URI MLflow accesible. Si está vacío, se resuelve `MLFLOW_MODEL_VERSION` o el alias configurado del registro. `EXPECTED_PREPROCESS_FINGERPRINT` permite exigir la huella aprobada durante la evaluación. `INFERENCE_CONCURRENCY` limita las inferencias simultáneas por proceso, con valor inicial 2.

Use el Compose de la raíz para instalar conjuntamente la base, la API y el tablero. La migración `data-platform/scripts/ddl/12_inferencia_real.sql` permite métricas ausentes y varias cargas de una misma imagen. Aplíquela antes de arrancar sobre una base existente, con respaldo y la autorización de su administrador.

## Solicitud y respuesta

```sh
curl -f http://localhost:8000/ready
curl -f -F countryCode=CO -F file=@muestra.png http://localhost:8000/api/v1/classifications
```

El archivo es obligatorio en modo ONNX. Se admiten JPG y PNG válidos, hasta 8 MiB, 8192 píxeles por lado y 16 millones de píxeles. El tipo declarado debe corresponder al contenido. El país debe existir en el catálogo y sólo se usa como metadato; `hint` se rechaza en modo real.

La respuesta conserva las probabilidades del modelo expresadas en porcentaje e incluye `modelVersion`, `modelUri`, `runId`, `preprocessFingerprint`, `imageSha256`, `simulatedInference`, `persisted` y `uploadId`. `explain=true` solicita un mapa de influencia si el paquete declara esa capacidad. No se genera un mapa de reemplazo.

El historial guarda la predicción, sus cuatro valores, la identidad del modelo y la huella del archivo. La respuesta confirma `persisted=true` después del commit de base de datos. Los bytes originales no se conservan; por eso la incorporación al dataset está deshabilitada. El CSV incluye la procedencia de las predicciones.

| Respuesta | Significado |
|---|---|
| 413 | Archivo o dimensiones superiores al límite |
| 415 | Formato no admitido o tipo que no corresponde al archivo |
| 422 | Archivo ausente, vacío o corrupto; país o parámetros inválidos |
| 503 | Motor no disponible, fallo de inferencia o de almacenamiento |

`GET /health` comprueba el proceso; `GET /ready` comprueba modelo y base. `GET /api/v1/classifications/model-info` describe el motor cargado. Las métricas no disponibles se devuelven como `null` o se omiten del mapa de métricas, nunca se sustituyen por precisión de referencia.

## Pruebas

Instale `requirements-dev.txt` además de las dependencias ONNX. `pytest` ejecuta los contratos existentes. Para incluir ONNX, genere el paquete sintético indicado en `ml_project/ENTREGA_MODELO.md` y defina `BNS_TEST_MODEL_PACKAGE` con su ruta absoluta.

Las pruebas PostgreSQL requieren una base desechable inicializada con los scripts del proyecto, accesible en `127.0.0.1:5432`, y `DATABASE_URL` apuntando a ella. No ejecute esta suite contra una base compartida o de producción. `test_real_inference.py` verifica paridad, rechazos, repetición de imágenes, persistencia, fallos del motor, fallo de commit y catálogo del modelo activo.

El modo `INFERENCE_ENGINE=simulated` permanece disponible únicamente como demostración explícita. `DATA_SOURCE=seed` no conserva nuevas predicciones. Ambos modos se declaran en la respuesta.
