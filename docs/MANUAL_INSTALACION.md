# Manual de instalación de BrainNeuroScan

## Qué instala este manual

Esta guía instala BrainNeuroScan con Docker: tablero web, API de inferencia y PostgreSQL. Los comandos se ejecutan desde PowerShell, en la raíz del repositorio. El navegador utiliza los puertos 8080 y 8000; PostgreSQL se comunica dentro de la red de contenedores.

La API necesita un paquete completo del modelo para arrancar. Recibe imágenes, ejecuta el motor ONNX y guarda los resultados. No necesita descargar el dataset ni repetir el entrenamiento para utilizar la solución.

Tablero publicado: https://maia-pds-microproyecto-production.up.railway.app/

Documentación de la API: https://maia-pds-microproyecto-api.up.railway.app/docs

Experimentos y modelos: https://mlflow.alexchirino.online/

Para actualizar los servicios existentes en la nube, siga [Despliegue en Railway](DESPLIEGUE_RAILWAY.md).

```xml
<pendiente id="validacion-despliegue-final" />
```

## Preparar el equipo y obtener el código

| Requisito | Uso |
| --- | --- |
| Git | Obtener la versión del código de la entrega. |
| Docker Desktop y Compose v2 | Ejecutar contenedores Linux. Mantenga Docker Desktop iniciado. |
| PowerShell y navegador | Ejecutar comandos y verificar la interfaz. |
| Internet y almacenamiento | Descargar imágenes, dependencias y el paquete del modelo. |
| Puertos 8000 y 8080 disponibles | Acceder a API y tablero desde el equipo. |
| Paquete del modelo | MLmodel, pesos, preprocesamiento, código y dependencias. |

Python, Node.js y PostgreSQL se incluyen en los contenedores. El motor ONNX funciona en CPU y no requiere GPU. La memoria necesaria depende del paquete del modelo.

```xml
<pendiente id="recursos-medidos-modelo-final" />
```

```powershell
git --version
docker version
docker compose version
```

Si Docker no muestra información del servidor, abra Docker Desktop y espere a que el motor esté disponible. Clone el repositorio conservando los finales de línea de los scripts Linux.

```powershell
git -c core.autocrlf=false clone `
  https://github.com/apchirinoc/maia-pds-microproyecto.git
Set-Location maia-pds-microproyecto
```

```xml
<pendiente id="revision-git-entrega3" />
```

La revisión utilizada debe incluir compose.yaml en la raíz y las carpetas api, web, data-platform y ml_project con la integración de inferencia. Los pesos no se descargan con git clone.

## Obtener e instalar el paquete del modelo

El modelo es ResNet18. El artefacto descargable es `models:/m-994b5e15a2be4cd99280ca696ae54d8f`, del run `f89f4f1604cd4c02b66b4d19155e4d24`. Es PyTorch; siga [la guía de descarga y conversión](../ml_project/ENTREGA_RESNET18V1.md) para obtener el paquete que utiliza la API. Las versiones antiguas del registro ResNet18v1 apuntan a otros artefactos.

```xml
<pendiente id="descarga-paquete-modelo" />
```

Obtenga el paquete aprobado y compruebe su versión y SHA-256. Descomprima la carpeta completa como artifacts/classifier/. Debe existir artifacts/classifier/MLmodel junto con artifacts/, code/, requirements.txt y los archivos de entorno del paquete. No copie únicamente el archivo ONNX.

El ZIP `BrainNeuroScan-ResNet18-994b5e15-ONNX.zip` comprobado tiene SHA-256 `b7fdb3720cddb3536a2b4b33038a8fb4e25209d40a4c53779eb2acd39880d8bd`. La guía del modelo permite regenerar el paquete desde los artefactos publicados en MLflow.

```powershell
Test-Path artifacts/classifier/MLmodel
Get-ChildItem artifacts/classifier
```

El primer comando debe devolver True. El montaje de Docker convierte artifacts/ del equipo en /models dentro de la API, por lo que la ruta del modelo será /models/classifier. El contenedor debe poder leer todos los archivos.

### Contrato del modelo entrenado

El notebook PdS_Training_Experiments.ipynb entrena ResNet18 con imágenes RGB, redimensionamiento bilineal a 224 × 224, ToTensor y normalización ImageNet. El orden de clases es glioma, healthy, meningioma y pituitary. No se aplica CLAHE a ese modelo.

Si se recibe el paquete PyTorch original, utilice ml_project/export_colab_model.py siguiendo ml_project/ENTREGA_MODELO.md. El exportador compara el preprocesamiento con torchvision y las probabilidades PyTorch/ONNX. Sólo debe distribuirse el paquete que supere esa comprobación; no requiere reentrenar.

La conversión se comprobó con los pesos descargados y cuatro muestras. La diferencia absoluta máxima entre probabilidades PyTorch y ONNX fue 5.960464477539062e-07. Esta prueba valida la conversión, no mide la exactitud del modelo en un nuevo conjunto de evaluación.

## Configurar la instalación local

Copie .env.example a .env sólo en una instalación nueva. Complete los secretos de PostgreSQL y JWT; este último debe tener al menos 32 caracteres. No publique .env ni incluya credenciales en variables VITE_, visibles para el navegador.

```powershell
Copy-Item .env.example .env
```

El siguiente bloque genera los secretos y sustituye únicamente sus campos vacíos. Si reutiliza una base existente, conserve su contraseña; no ejecute una generación nueva de credenciales.

```powershell
$pgBns = [guid]::NewGuid().ToString('N')
$jwtBns = [guid]::NewGuid().ToString('N') + `
  [guid]::NewGuid().ToString('N')
$configBns = Get-Content .env -Raw
$configBns = $configBns -replace '(?m)^POSTGRES_PASSWORD=\r?$', `
  ('POSTGRES_PASSWORD=' + $pgBns)
$configBns = $configBns -replace '(?m)^JWT_SECRET=\r?$', `
  ('JWT_SECRET=' + $jwtBns)
Set-Content -Path .env -Value $configBns -Encoding ascii
```

| Variable en .env | Valor o propósito |
| --- | --- |
| MODEL_DIRECTORY | ./artifacts, carpeta que Docker monta como /models. |
| MLFLOW_MODEL_URI | /models/classifier, ubicación del paquete dentro del contenedor. |
| MLFLOW_MODEL_NAME | ResNet18v1, nombre del modelo elegido. |
| MLFLOW_MODEL_VERSION | Versión numérica si se resuelve desde el registro remoto. El paquete local declara su versión en metadatos. |
| EXPECTED_PREPROCESS_FINGERPRINT | Huella del preprocesamiento aprobado; permite rechazar un paquete distinto. |
| API_PORT / WEB_PORT | 8000 / 8080. Cambie también las URL si cambia los puertos. |
| PUBLIC_API_URL | http://localhost:8000, URL accesible desde el navegador. |
| WEB_ORIGIN | http://localhost:8080, origen exacto permitido por CORS. |
| MLFLOW_TRACKING_URI | Vacío para servir el paquete local sin depender del servidor de MLflow. |

Para el paquete local, la versión declarada es m-994b5e15a2be4cd99280ca696ae54d8f y EXPECTED_PREPROCESS_FINGERPRINT debe ser 3550069770ff4bc4. Compruebe ambos datos en validation.json después de convertir los pesos; no confunda esta huella con el SHA-256 del archivo de pesos.

Compose configura INFERENCE_ENGINE=onnx, DATA_SOURCE=postgres y VITE_FORCE_MOCKS=false. También conecta la API con db:5432. No use db ni api como dominio de PUBLIC_API_URL: esos nombres sólo se resuelven entre contenedores.

Si localhost presenta problemas de resolución, use 127.0.0.1 tanto en PUBLIC_API_URL como en WEB_ORIGIN y en el navegador. El origen CORS debe coincidir exactamente con la dirección utilizada.

## Construir y ejecutar los servicios

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail=80 api
```

El primer arranque inicializa PostgreSQL, aplica el esquema y carga catálogos de referencia. No agrega modelos ficticios ni predicciones de demostración. La API carga el paquete antes de quedar disponible; el tablero espera la salud de la API.

Abra http://localhost:8080 y http://localhost:8000/docs. La configuración pública del tablero se inyecta al arrancar. Para comprobar qué URL recibió el navegador, consulte http://localhost:8080/env-config.js.

## Verificar el recorrido completo

1. Compruebe disponibilidad, origen de datos e identidad del modelo.

```powershell
Invoke-RestMethod http://localhost:8000/ready
Invoke-RestMethod http://localhost:8000/api/v1/meta
Invoke-RestMethod `
  http://localhost:8000/api/v1/classifications/model-info
```

ready debe responder status igual a ok y simulatedInference igual a false. Los metadatos deben indicar PostgreSQL y la identidad del paquete instalado. Compare la versión y la huella del preprocesamiento con las entregadas junto al modelo. /health por sí solo no verifica toda la integración.

2. Abra Analizar imagen, cargue un JPG o PNG y seleccione un país. Pulse Clasificar imagen y compruebe la clase, los cuatro porcentajes, el modelo y la confirmación de guardado. Repita con una muestra de la galería. Una respuesta de error no debe convertirse en una predicción simulada.

3. Descargue el informe TXT. Si solicita el mapa de influencia, compruebe que puede mostrarlo y ocultarlo. El mapa es una ayuda exploratoria, no una segmentación clínica.

4. Inicie sesión con una cuenta de la instalación. La base local incluye la cuenta demo con contraseña demo para comprobaciones; no representa las cuentas del despliegue público. En Histórico, busque el identificador del resultado y exporte el CSV.

5. Anote el identificador, reinicie la API y compruebe que el registro se conserva. El historial guarda resultados y huellas, no el archivo MRI original.

```powershell
docker compose restart api
```

### Prueba reproducible de la API

Desde la raíz del repositorio, esta prueba local envía dos veces una muestra, comprueba la huella, el resultado determinista, la persistencia y la exportación CSV. Crea dos registros; utilícela en una instalación de pruebas.

```powershell
$repoBns = (Get-Location).Path
docker compose run --rm --no-deps `
  -e BNS_TEST_PASSWORD=demo `
  --volume "${repoBns}:/workspace:ro" api `
  python /workspace/scripts/verify_inference.py `
  --api http://api:8000 `
  --image /workspace/web/public/samples/Te-gl_0023.jpg `
  --username demo
```

La salida debe incluir verified igual a true, la versión del modelo, dos identificadores distintos y la huella SHA-256 de la imagen. Complete además el recorrido en navegador; la prueba HTTP no verifica por sí sola la interfaz.

```xml
<pendiente id="evidencia-recorrido-modelo-entrenado" />
```

## Configurar MLflow y el despliegue

### Paquete local o registro remoto

Con el paquete local, la API puede funcionar aunque MLflow esté apagado. Para resolver una versión remota, deje MLFLOW_MODEL_URI vacío y configure MLFLOW_TRACKING_URI, MLFLOW_MODEL_NAME y MLFLOW_MODEL_VERSION. El registro debe contener el paquete pyfunc convertido, no el PyTorch original de ResNet18v1.

El servidor de tracking y el almacén de artefactos deben ser accesibles durante ese arranque. Que aparezcan las métricas del entrenamiento no demuestra que el paquete pueda descargarse. Conserve MLmodel y toda su estructura.

Si el almacén utiliza S3, configure las credenciales o el rol autorizado y su región en el servicio de API. Si MLflow requiere autenticación adicional, transmita también esas variables al contenedor; incluirlas únicamente en .env no basta si Compose no las declara.

### Publicación en la nube

Construya la API con api/Dockerfile y el tablero con web/Dockerfile. Configure PostgreSQL, JWT_SECRET, INFERENCE_ENGINE=onnx y la ubicación del paquete. La imagen de la API incluye requirements-onnx.txt; el paquete debe estar montado o descargado antes de arrancar.

En el servicio web, VITE_API_BASE_URL debe contener la URL HTTPS pública de la API, sin /docs ni /api/v1. Mantenga VITE_FORCE_MOCKS=false. En la API, ALLOWED_ORIGINS debe coincidir con el dominio HTTPS del tablero. Los contenedores admiten el puerto PORT asignado por la plataforma.

Configure /ready como comprobación de disponibilidad de la API y verifique el acceso a la base y al paquete desde el contenedor publicado. Una ruta local del servidor MLflow no es automáticamente accesible desde Railway.

```xml
<pendiente id="almacenamiento-modelo-en-nube" />
<pendiente id="configuracion-final-railway" />
```

## Conservar datos y actualizar la instalación

Para detener los servicios conservando los datos y volver a iniciarlos:

```powershell
docker compose down
docker compose up -d
```

El volumen database conserva el historial. No use down -v para reiniciar o actualizar. Si cambia variables, utilice docker compose up -d para recrear los servicios afectados; restart no actualiza su entorno.

Para respaldar PostgreSQL, genere el archivo dentro del contenedor y cópielo al equipo. El formato binario evita problemas de codificación de PowerShell.

```powershell
docker compose exec -T db pg_dump -U brainneuroscan `
  -d brainneuroscan -Fc -f /tmp/brainneuroscan.dump
docker compose cp db:/tmp/brainneuroscan.dump ./brainneuroscan.dump
```

### Base de datos existente

Los scripts de inicialización sólo se ejecutan sobre un volumen vacío. Para una base anterior, haga un respaldo y aplique la migración de inferencia usando la conexión autorizada. En una instalación gestionada por este Compose:

```powershell
docker compose cp `
  data-platform/scripts/ddl/12_inferencia_real.sql `
  db:/tmp/12_inferencia_real.sql
docker compose exec -T db psql -U brainneuroscan `
  -d brainneuroscan --set ON_ERROR_STOP=1 `
  --file /tmp/12_inferencia_real.sql
```

No elimine el volumen como sustituto de la migración. Para cambiar el modelo, conserve la versión anterior, instale el nuevo paquete aprobado, actualice su identidad y reinicie la API. Repita las verificaciones de disponibilidad y clasificación.

## Resolver problemas de instalación

| Síntoma | Comprobación |
| --- | --- |
| Docker no responde | Inicie Docker Desktop con contenedores Linux y repita docker version. |
| La API no arranca | Revise docker compose logs api, MLmodel, permisos, dependencias y conexión PostgreSQL. |
| No such artifact | Verifique la descarga de los archivos y el almacén de artefactos; la existencia de métricas no basta. |
| Tablero sin conexión | Revise PUBLIC_API_URL, env-config.js y la disponibilidad de /ready. Use una URL accesible al navegador. |
| Error CORS | WEB_ORIGIN o ALLOWED_ORIGINS debe coincidir con protocolo, dominio y puerto del tablero. Recree la API. |
| Clasificación 413, 415 o 422 | Revise tamaño, formato, dimensiones y país. No envíe hint para forzar una clase. |
| No se guarda el resultado | Revise PostgreSQL, migración y logs. No interprete una respuesta fallida como confirmación de guardado. |
| No permite iniciar sesión | Use una cuenta de esa base. demo/demo corresponde a la instalación local inicial. |
| Resultado marcado como simulado | Revise INFERENCE_ENGINE, VITE_FORCE_MOCKS y los metadatos. La integración documentada debe usar ONNX. |

## Referencias de operación

Repositorio: https://github.com/apchirinoc/maia-pds-microproyecto

Empaquetamiento y equivalencia: ml_project/ENTREGA_MODELO.md. Prueba completa: docs/PRUEBA_INTEGRACION.md.

Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/

Variables de Docker Compose: https://docs.docker.com/compose/how-tos/environment-variables/

Registro de modelos MLflow: https://mlflow.org/docs/latest/ml/model-registry/workflow/
