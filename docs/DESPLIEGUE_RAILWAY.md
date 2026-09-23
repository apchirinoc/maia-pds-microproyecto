# Desplegar la inferencia real en Railway

Este procedimiento actualiza los servicios existentes del tablero y la API. No crea ni reemplaza la base de datos. La comprobación local con los pesos del equipo ya pasó; las comprobaciones de esta guía deben repetirse después del despliegue público.

## 1. Preparar código y modelo

Integre en `main` los cuatro frentes: modelo/MLflow, API, tablero y Docker. Despliegue una revisión que contenga todos. Si Railway tiene despliegue automático desde `main`, suspenda temporalmente ese automatismo mientras se integran los PRs para evitar desplegar una combinación incompleta.

Obtenga el paquete ONNX completo siguiendo [la guía del modelo](../ml_project/ENTREGA_RESNET18V1.md). El ZIP preparado por el equipo se llama `BrainNeuroScan-ResNet18-994b5e15-ONNX.zip`, contiene la carpeta `classifier/` y tiene SHA-256:

```text
b7fdb3720cddb3536a2b4b33038a8fb4e25209d40a4c53779eb2acd39880d8bd
```

Compruebe el archivo recibido y descomprímalo en un destino nuevo:

```powershell
Get-FileHash ./BrainNeuroScan-ResNet18-994b5e15-ONNX.zip -Algorithm SHA256
Expand-Archive ./BrainNeuroScan-ResNet18-994b5e15-ONNX.zip ./artifacts
Test-Path ./artifacts/classifier/MLmodel
```

El modelo PyTorch de `models:/m-994b5e15a2be4cd99280ca696ae54d8f` es la fuente. La API necesita el paquete convertido, incluidos `MLmodel`, `artifacts/`, `code/` y dependencias. No copie solo el ONNX ni use el modelo PyTorch directamente como `MLFLOW_MODEL_URI`.

## 2. Conservar el paquete en Railway

En el servicio de la API, agregue un volumen persistente montado en `/models`. Si ya tiene un volumen, conserve su contenido y utilice una subcarpeta disponible de ese volumen; ajuste la ruta del modelo en consecuencia.

La CLI Railway 5.59.0 admite la carga de carpetas a volúmenes. Desde la carpeta que contiene `artifacts/`, autentíquese y seleccione el proyecto y entorno correctos:

```powershell
npx --yes @railway/cli@5.59.0 login
npx --yes @railway/cli@5.59.0 link
npx --yes @railway/cli@5.59.0 volume list
npx --yes @railway/cli@5.59.0 volume files --volume VOLUME_ID upload ./artifacts/classifier /classifier
npx --yes @railway/cli@5.59.0 volume files --volume VOLUME_ID list /classifier
```

Sustituya `VOLUME_ID` por el volumen de la API, no el de PostgreSQL. Las rutas de `volume files` son relativas a la raíz del volumen: `/classifier` se verá como `/models/classifier` dentro del servicio. La carga rechaza un destino existente; para otra versión use otra carpeta y cambie la variable, conservando el paquete anterior.

Verifique que las carpetas y archivos sean legibles por el usuario `apiuser`, UID 10001, de la imagen. Los pesos no necesitan permisos de escritura durante la inferencia. Una vez cargado el volumen, el arranque no depende de que el laboratorio MLflow esté encendido.

## 3. Aplicar la migración en la base existente

Obtenga un respaldo con las herramientas del proveedor y conserve la configuración actual de conexión. Ejecute **solo** `data-platform/scripts/ddl/12_inferencia_real.sql` en la base que usa la API, antes de arrancar la nueva versión. No vuelva a ejecutar las semillas ni elimine el esquema.

Con `psql` instalado y la conexión cargada en una variable de entorno local:

```powershell
psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f ./data-platform/scripts/ddl/12_inferencia_real.sql
```

La migración permite métricas ausentes, análisis repetidos y versiones completas de MLflow. Recrea `vw_model_registry_summary` dentro de la misma transacción porque depende del tipo de la columna de versión. Debe ejecutarla el propietario de esos objetos. Si existen permisos específicos concedidos a otros roles sobre esa vista, conserve y restituya esos permisos.

## 4. Configurar y desplegar la API

En Settings del servicio: repositorio del proyecto, rama `main`, Root Directory `/api` y construcción con `Dockerfile`. Quite un Start Command antiguo que sustituya el del Dockerfile; la imagen ya inicia Uvicorn con `${PORT:-8000}`. Configure Healthcheck Path `/ready` y un tiempo de arranque de 300 segundos.

Conserve `DATABASE_URL` y `JWT_SECRET` actuales. El secreto JWT debe tener al menos 32 caracteres. Configure:

```dotenv
ENVIRONMENT=production
DEBUG=false
DATA_SOURCE=postgres
INFERENCE_ENGINE=onnx
MLFLOW_MODEL_URI=/models/classifier
MLFLOW_MODEL_NAME=ResNet18v1
EXPECTED_PREPROCESS_FINGERPRINT=3550069770ff4bc4
ALLOWED_ORIGINS=https://maia-pds-microproyecto-production.up.railway.app
```

Deje `MLFLOW_TRACKING_URI` y `MLFLOW_MODEL_VERSION` vacías para usar la identidad del paquete local. No establezca `DATABASE_URL` al contenedor `db` de Compose: conserve la conexión real del servicio. Mantenga los requisitos SSL del proveedor existente.

Despliegue y compruebe:

```powershell
Invoke-RestMethod https://maia-pds-microproyecto-api.up.railway.app/ready
Invoke-RestMethod https://maia-pds-microproyecto-api.up.railway.app/api/v1/classifications/model-info
```

`/ready` debe indicar `status: ok` y `simulatedInference: false`. La identidad debe corresponder a `m-994b5e15a2be4cd99280ca696ae54d8f` y a la huella `3550069770ff4bc4`. `/health` por sí solo no demuestra que el modelo esté cargado.

## 5. Configurar y desplegar el tablero

En su servicio: rama `main`, Root Directory `/web`, construcción con `Dockerfile` y Healthcheck Path `/nginx-health`. El Dockerfile inicia Nginx y su script adapta el puerto a `PORT`.

```dotenv
VITE_API_BASE_URL=https://maia-pds-microproyecto-api.up.railway.app
VITE_FORCE_MOCKS=false
VITE_API_TIMEOUT_MS=120000
```

Despliegue el tablero después de que la API esté disponible. `VITE_API_BASE_URL` debe ser accesible desde el navegador, por eso se utiliza el dominio público HTTPS y no el dominio privado entre servicios de Railway.

## 6. Verificar el recorrido público

Seleccione una muestra, elija un país y clasifique. Repita cargando un JPG o PNG desde el equipo. Compruebe que la respuesta declara inferencia real, conserva el hash de la imagen y devuelve `persisted: true`. Inicie sesión y verifique el registro en el historial y su exportación CSV. El mapa de influencia es opcional y aumenta el trabajo de inferencia.

Repita el procedimiento de [prueba de integración](PRUEBA_INTEGRACION.md). El script crea dos registros de prueba, por lo que debe ejecutarse conscientemente contra el entorno seleccionado. Compruebe que una pérdida de conexión muestra un error y no un resultado simulado.

Los conteos del dataset siguen siendo de referencia. Este run de publicación no tiene métricas de evaluación; que la exactitud aparezca vacía es correcto hasta vincular una evaluación verificable de estos mismos pesos.

Referencias oficiales: [Dockerfiles y variables de construcción](https://docs.railway.com/builds/dockerfiles), [servicios en monorepositorios](https://docs.railway.com/deployments/monorepo), [volúmenes persistentes](https://docs.railway.com/volumes), [CLI de volúmenes](https://docs.railway.com/cli/volume).
