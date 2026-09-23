# Manual de instalación del tablero

BrainNeuroScan

Descargas de esta entrega: [manuales en Word y PDF, paquete del modelo y comprobaciones](https://github.com/apchirinoc/maia-pds-microproyecto/releases/tag/entrega3).

## Alcance y versión de la solución

Este manual permite instalar BrainNeuroScan con Docker, ejecutar el modelo ResNet18v1 desde la API y consultar sus predicciones en el tablero. El procedimiento principal usa PowerShell, contenedores Linux y PostgreSQL local. La sección de Railway describe el despliegue con PostgreSQL administrado en Supabase.

No es necesario entrenar de nuevo ni descargar el dataset completo. Se necesita el código y el paquete portable del modelo que acompaña a estos manuales. La API carga ese paquete desde disco y puede funcionar aunque el servidor de MLflow esté apagado.

Tablero: https://maia-pds-microproyecto-production.up.railway.app/

API y documentación interactiva: https://maia-pds-microproyecto-api.up.railway.app/docs

Experimentos: https://mlflow.alexchirino.online/

La versión documentada corresponde al commit f72dbe3 de main. El recorrido con imagen local, predicción, mapa, descarga e histórico se verificó en el despliegue publicado. BrainNeuroScan es un prototipo académico y no sustituye la interpretación clínica.

## Preparar el equipo y obtener el código

| Requisito | Uso |
| --- | --- |
| Git | Descargar la revisión del código de esta entrega. |
| Docker Desktop y Compose v2 | Construir y ejecutar contenedores Linux. Mantenga Docker Desktop iniciado. |
| PowerShell y navegador | Ejecutar los comandos y utilizar el tablero. |
| Conexión a Internet | Descargar repositorio, imágenes base y dependencias durante la construcción. |
| Puertos 8000 y 8080 libres | API y tablero locales. PostgreSQL no se publica al equipo. |
| Paquete portable del modelo | ZIP de 39,7 MiB incluido junto a los manuales. Reserve además espacio para las imágenes Docker y la base de datos. |

Python, Node.js y PostgreSQL están incluidos en los contenedores. La inferencia usa ONNX Runtime en CPU; no requiere GPU ni instalar PyTorch en el equipo que sirve la aplicación.

```powershell
git --version
docker version
docker compose version
```

Si docker version no muestra la sección del servidor, inicie Docker Desktop. Ejecute los siguientes comandos desde una carpeta de trabajo nueva. Todos los comandos posteriores parten de la raíz del repositorio.

```powershell
git -c core.autocrlf=false clone `
  https://github.com/apchirinoc/maia-pds-microproyecto.git
Set-Location maia-pds-microproyecto
git checkout f72dbe30e9e277f2c3ebf531ab5656fe51dfe44b
```

Fijar esta revisión evita mezclar instrucciones con cambios posteriores. Las carpetas principales son api/, web/, ml_project/ y data-platform/; compose.yaml está en la raíz. Los pesos no forman parte de git clone.

## Instalar el paquete del modelo

Copie BrainNeuroScan-ResNet18-994b5e15-ONNX.zip, incluido junto a este documento, a la raíz del repositorio. Conserve el ZIP y el manual juntos al distribuir la entrega. El paquete contiene el modelo ya convertido, el preprocesamiento y su código; no necesita volver a conectarse a MLflow para instalarlo.

Compruebe la integridad antes de extraer. El script se detiene si el SHA-256 no corresponde al paquete de esta entrega o si ya existe una instalación del modelo.

```powershell
$paqueteBns = './BrainNeuroScan-ResNet18-994b5e15-ONNX.zip'
$shaBns = 'b7fdb3720cddb3536a2b4b33038a8fb4e25209d40a4c53779eb2acd39880d8bd'
if ((Get-FileHash $paqueteBns -Algorithm SHA256).Hash `
    -ne $shaBns) { throw 'El paquete no coincide' }
if (Test-Path ./artifacts/classifier) {
  throw 'La carpeta del modelo ya existe'
}
Expand-Archive $paqueteBns -DestinationPath ./artifacts
Test-Path ./artifacts/classifier/MLmodel
```

El último comando debe devolver True. Evite una carpeta duplicada como artifacts/classifier/classifier. Docker monta artifacts/ como /models; por eso la API encuentra el modelo en /models/classifier.

| Archivo o carpeta | Contenido |
| --- | --- |
| classifier/MLmodel | Contrato MLflow, identidad, clases y referencias a los artefactos. |
| classifier/artifacts/ | Pesos ONNX y configuración de preprocesamiento. |
| classifier/code/ y python_model.pkl | Código del paquete pyfunc que recibe la imagen y ejecuta la inferencia. |
| classifier/requirements.txt y entornos | Dependencias declaradas por el paquete. |
| classifier/validation.json | Origen, hashes y comprobación de equivalencia PyTorch/ONNX. |

### Identidad y preprocesamiento

El nombre visible es ResNet18v1. La identidad del paquete desplegado es m-994b5e15a2be4cd99280ca696ae54d8f, procedente del run f89f4f1604cd4c02b66b4d19155e4d24. No confunda esta identidad con otra versión del registro que tenga el mismo nombre.

Run de origen: https://mlflow.alexchirino.online/#/experiments/3/runs/f89f4f1604cd4c02b66b4d19155e4d24/artifacts

La entrada se convierte a RGB, se redimensiona a 224 × 224 con interpolación bilineal y se normaliza con ImageNet. No se aplica CLAHE. El orden aprendido es glioma, healthy, meningioma y pituitary; la huella del preprocesamiento es 3550069770ff4bc4.

La conversión se verificó con cuatro muestras, una por clase. La diferencia máxima entre probabilidades PyTorch y ONNX fue 5,96 × 10⁻⁷. Es una comprobación de equivalencia técnica, no una evaluación de exactitud. El paquete no incluye métricas de evaluación y no deben copiarse de otro run.

Si necesita reconstruir el paquete desde el artefacto PyTorch, use ml_project/export_colab_model.py con la URI models:/m-994b5e15a2be4cd99280ca696ae54d8f y el run anterior. Esa operación requiere las dependencias de entrenamiento y acceso al almacén de artefactos. La instalación descrita aquí utiliza el ZIP convertido.

## Configurar la instalación local

Copie .env.example a .env sólo en la instalación nueva y genere secretos propios. No publique .env ni incluya contraseñas en variables VITE_, porque el navegador puede leerlas.

```powershell
Copy-Item .env.example .env
$claveDbBns = ([guid]::NewGuid().ToString('N')) + `
              ([guid]::NewGuid().ToString('N'))
$claveJwtBns = ([guid]::NewGuid().ToString('N')) + `
               ([guid]::NewGuid().ToString('N'))
$textoBns = Get-Content .env -Raw
$textoBns = $textoBns -replace '(?m)^POSTGRES_PASSWORD=.*$', `
  ('POSTGRES_PASSWORD=' + $claveDbBns)
$textoBns = $textoBns -replace '(?m)^JWT_SECRET=.*$', `
  ('JWT_SECRET=' + $claveJwtBns)
Set-Content .env $textoBns -Encoding utf8
```

| Variable de .env | Valor para esta instalación |
| --- | --- |
| MODEL_DIRECTORY | ./artifacts |
| MLFLOW_MODEL_URI | /models/classifier |
| MLFLOW_MODEL_NAME | ResNet18v1 |
| MLFLOW_MODEL_VERSION | Vacío. La identidad viene en los metadatos del paquete local. |
| MLFLOW_TRACKING_URI | Vacío. No se consulta MLflow para cargar el paquete local. |
| EXPECTED_PREPROCESS_FINGERPRINT | 3550069770ff4bc4 |
| API_PORT / WEB_PORT | 8000 / 8080 |
| PUBLIC_API_URL | http://localhost:8000 |
| WEB_ORIGIN | http://localhost:8080 |

Compose fija INFERENCE_ENGINE=onnx, DATA_SOURCE=postgres y VITE_FORCE_MOCKS=false. La API usa db:5432 dentro de la red Docker. PUBLIC_API_URL debe ser accesible desde el navegador; no utilice api ni db como dominio público.

Si cambia puertos, cambie también PUBLIC_API_URL y WEB_ORIGIN. localhost y 127.0.0.1 son orígenes diferentes para CORS; use la misma forma en la configuración y en el navegador.

## Construir y ejecutar

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=80 api
```

En el primer arranque, PostgreSQL aplica los scripts del esquema y carga catálogos, usuarios de prueba y datos de referencia del dataset. El Compose de esta entrega excluye modelos ficticios y cargas de demostración. La API carga el modelo antes de estar lista y el tablero espera la salud de la API.

Abra http://localhost:8080 para el tablero y http://localhost:8000/docs para la API. En docker compose ps, db y api deben estar saludables y web en ejecución. La primera construcción puede tardar varios minutos; revise los logs si un servicio se reinicia.

La configuración pública del tablero se genera al iniciar su contenedor. http://localhost:8080/env-config.js permite comprobar la URL de la API; no debe contener secretos.

## Verificar la instalación completa

### Disponibilidad e identidad

```powershell
$apiBns = 'http://localhost:8000'
Invoke-RestMethod "$apiBns/ready"
Invoke-RestMethod "$apiBns/api/v1/meta"
Invoke-RestMethod `
  "$apiBns/api/v1/classifications/model-info"
```

/ready debe devolver status: ok y simulatedInference: false. model-info debe identificar ResNet18v1, el paquete m-994b5e15a2be4cd99280ca696ae54d8f, la huella 3550069770ff4bc4 y supportsExplanation: true. evaluationMetrics vacío es válido para este paquete. /health por sí solo no comprueba toda la integración.

### Prueba en el navegador

1. Abra Analizar imagen, seleccione un JPG o PNG y un país. Pulse Clasificar imagen. Compruebe la predicción, los porcentajes por clase, la identidad del modelo y Guardado en historial. Repita el recorrido con una muestra de la galería.

2. Active Incluir mapa de influencia antes de analizar para comprobar el mapa por oclusión. Descargue el informe TXT y compare su identificador con el resultado en pantalla.

3. Inicie sesión. La instalación local inicial incluye demo con contraseña demo; en la aplicación publicada use la cuenta asignada. Abra Histórico, localice el identificador y exporte el CSV. Los usuarios de prueba sirven para validar la instalación académica; antes de habilitar otros accesos, el administrador debe gestionarlos en la base de datos.

4. Anote el identificador, reinicie sólo la API y confirme que sigue en el histórico. El volumen database conserva PostgreSQL. El historial almacena resultados, metadatos y huellas; no guarda el archivo MRI original.

```powershell
docker compose restart api
```

### Comprobación automática

La prueba siguiente crea dos registros de prueba y comprueba imagen, respuesta determinista, modelo, persistencia y CSV. Ejecútela en la instalación local; no sustituye la revisión de la interfaz.

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

La salida debe incluir verified: true, el modelo y dos identificadores distintos. Un archivo que no contenga una imagen válida debe rechazarse, sin crear una predicción simulada. Consulte docs/PRUEBA_INTEGRACION.md para las comprobaciones del contrato.

## Desplegar en Railway y conectar PostgreSQL

La instalación publicada utiliza dos servicios Docker en Railway, un volumen persistente unido a la API y PostgreSQL en Supabase. No se ejecuta el Compose completo dentro de Railway. Necesita permisos de edición y despliegue en el proyecto.

| Servicio | Configuración |
| --- | --- |
| API · honest-optimism | Repositorio del proyecto, rama main, Root Directory /api y Dockerfile api/Dockerfile del repositorio. Deje Start Command vacío para usar el CMD de la imagen. |
| Web · maia-pds-microproyecto | Mismo repositorio y rama, Root Directory /web y Dockerfile web/Dockerfile. Deje Start Command vacío. |
| Volumen de la API | Monte en /models. El paquete completo debe quedar en /models/classifier/MLmodel. |
| Healthcheck | API: /ready. Web: /. Configure un tiempo de arranque de 300 segundos. |

Railway puede detectar el Dockerfile dentro de cada Root Directory. Si indica una ruta personalizada, use la ruta del archivo correspondiente al servicio. No utilice un comando de desarrollo de Vite para el tablero: la imagen sirve la compilación con Nginx.

### Conectar una base administrada

En el servicio API, configure los valores privados de PostgreSQL suministrados por el administrador. El modo por variables separadas evita errores con contraseñas que contienen símbolos. POSTGRES_SSL=require es necesario para la conexión administrada documentada.

| Variable de API | Valor |
| --- | --- |
| ENVIRONMENT / DEBUG | production / false |
| DATA_SOURCE | postgres |
| POSTGRES_HOST / POSTGRES_PORT | Host y puerto del pooler de Supabase proporcionados al proyecto. |
| POSTGRES_USER / POSTGRES_DB | Usuario completo del pooler y nombre de la base de datos. |
| POSTGRES_PASSWORD | Contraseña privada de la base; no la incluya en documentos ni en Git. |
| POSTGRES_SSL | require |
| DATABASE_URL | Déjela vacía al utilizar las variables separadas. Si usa una URI, codifique los caracteres reservados de la contraseña y configure SSL. |
| JWT_SECRET | Secreto propio de al menos 32 caracteres. |

Una base nueva necesita el esquema. Ejecute los SQL de data-platform/scripts/ddl/ en orden numérico con psql y ON_ERROR_STOP=1. Después cargue dml/01_catalogos.sql, dml/02_usuarios.sql y dml/04_dataset.sql. No cargue dml/03_modelos.sql ni dml/05_cargas.sql si no desea registros de demostración. Los scripts usan extensiones y permisos de PostgreSQL; ejecútelos con la cuenta administradora de la base.

En la base Supabase del proyecto, el esquema y la migración 12 ya están aplicados. No vuelva a inicializarla ni a reemplazar sus datos. Para una base anterior distinta, respalde primero y siga la sección de mantenimiento.

### Cargar el modelo en el volumen

Cree o seleccione el volumen de la API y establezca Mount Path en /models. Una ruta del servidor de MLflow no es una ruta del contenedor Railway: debe transferir la carpeta classifier completa al volumen. Redeploy conserva el volumen, pero no copia los archivos desde su computador.

Para administrar los archivos desde PowerShell, instale Node.js LTS y use Railway CLI. Inicie sesión y seleccione su proyecto, entorno y servicio API con railway link. No seleccione el servicio web.

```powershell
npx --yes @railway/cli@5.59.0 login
npx --yes @railway/cli@5.59.0 link
npx --yes @railway/cli@5.59.0 volume list --json
```

La CLI solicita una clave SSH registrada para operar sobre el volumen. Complete ese registro con la cuenta administradora. En los comandos siguientes, sustituya ID_DEL_VOLUMEN por el identificador que devuelve volume list.

```powershell
$volumenBns = 'ID_DEL_VOLUMEN'
npx --yes @railway/cli@5.59.0 volume files `
  --volume $volumenBns upload ./artifacts/classifier /classifier
npx --yes @railway/cli@5.59.0 volume files `
  --volume $volumenBns list /classifier --json
```

Las rutas de volume files son relativas al volumen: /classifier corresponde a /models/classifier dentro de la API. Confirme MLmodel, artifacts/, code/ y los demás archivos. En la imagen de API, el proceso usa UID 10001; necesita permiso de lectura de archivos y acceso a las carpetas.

Si el volumen está vacío y la API se cae antes de permitir la transferencia, use un arranque temporal sólo para cargarlo. En Settings, quite temporalmente Healthcheck Path, cambie Start Command por el comando siguiente y despliegue. Una vez subido el modelo, borre ese Start Command, restablezca /ready y vuelva a desplegar. El proceso temporal no sirve predicciones.

```powershell
python -c "import time; time.sleep(3600)"
```

Si la transferencia indica que el destino existe, compruebe sus archivos y su identidad. Para una actualización, use una carpeta nueva y cambie MLFLOW_MODEL_URI; no sobrescriba un paquete que la API esté usando.

### Configurar modelo y comunicación entre servicios

| Variable de API | Valor |
| --- | --- |
| INFERENCE_ENGINE | onnx |
| MLFLOW_MODEL_URI | /models/classifier |
| MLFLOW_MODEL_NAME | ResNet18v1 |
| MLFLOW_MODEL_VERSION y MLFLOW_TRACKING_URI | Vacías para el paquete local. |
| EXPECTED_PREPROCESS_FINGERPRINT | 3550069770ff4bc4 |
| ALLOWED_ORIGINS | URL HTTPS del tablero, sin barra final ni rutas adicionales. |

| Variable de Web | Valor |
| --- | --- |
| VITE_API_BASE_URL | https://maia-pds-microproyecto-api.up.railway.app |
| VITE_FORCE_MOCKS | false |
| VITE_API_TIMEOUT_MS | 120000 |

En otro proyecto, sustituya los dominios por los generados para sus servicios. No añada /docs ni /api/v1 a VITE_API_BASE_URL. Los Dockerfiles atienden el puerto PORT de la plataforma; si fija un puerto, el dominio público debe dirigir el tráfico a ese mismo puerto.

Despliegue primero la API. Compruebe /ready y model-info en su dominio público. Después despliegue el tablero y repita la prueba del navegador. El estado Success de Railway no sustituye la comprobación de predicción y guardado.

### Consultar MLflow sin depender de su disponibilidad

MLflow conserva el experimento y los artefactos de origen. La aplicación publicada sirve la copia portable en el volumen; apagar MLflow no detiene una inferencia que usa ese paquete. Las versiones del registro no cambian automáticamente el motor activo.

Si opta por cargar desde un registro remoto, éste debe contener el paquete pyfunc convertido y permitir descargar todos sus artefactos. Configure tracking, nombre y versión explícita, y deje MLFLOW_MODEL_URI vacío. No apunte la API al modelo PyTorch del notebook: su contrato es distinto. La instalación local y la publicada usan el paquete portable descrito aquí.

## Conservar datos y actualizar

```powershell
docker compose down
docker compose up -d
```

Estos comandos detienen y reinician conservando el volumen. No use down -v para una actualización. Si cambia variables o imágenes, ejecute docker compose up -d --build; restart no actualiza las variables del contenedor.

### Respaldo local

```powershell
docker compose exec -T db pg_dump -U brainneuroscan `
  -d brainneuroscan -Fc -f /tmp/brainneuroscan.dump
docker compose cp db:/tmp/brainneuroscan.dump ./brainneuroscan.dump
```

Guarde el respaldo fuera del repositorio y compruebe su restauración en una base de prueba. Contiene datos de cuentas e historial y no debe publicarse con la entrega.

### Base anterior a la inferencia real

Los scripts de inicialización sólo se ejecutan automáticamente en un volumen vacío. En una base anterior, aplique data-platform/scripts/ddl/12_inferencia_real.sql después del respaldo. Use una transacción para revertir el cambio si un SQL falla.

```powershell
docker compose cp `
  data-platform/scripts/ddl/12_inferencia_real.sql `
  db:/tmp/12_inferencia_real.sql
docker compose exec -T db psql -U brainneuroscan `
  -d brainneuroscan --set ON_ERROR_STOP=1 `
  --single-transaction --file /tmp/12_inferencia_real.sql
```

La migración recrea la vista uploads_summary. En una base con permisos personalizados, conserve sus GRANT, opciones y comentarios antes de aplicarla y restáurelos dentro de la misma transacción. El comando anterior corresponde a la base local administrada por Compose; no lo ejecute sin adaptación sobre Supabase.

### Cambiar el modelo

Conserve la carpeta del paquete anterior. Instale el nuevo paquete en otra carpeta, verifique su SHA-256 y metadatos y actualice MLFLOW_MODEL_URI y EXPECTED_PREPROCESS_FINGERPRINT. Recree la API local o despliegue de nuevo en Railway. Repita las pruebas antes de retirar la versión anterior. Los botones del tablero no sustituyen este procedimiento.

## Resolver problemas de instalación

| Síntoma | Comprobación |
| --- | --- |
| Docker no responde | Inicie Docker Desktop con contenedores Linux y repita docker version. |
| API reiniciándose | Revise logs, conexión PostgreSQL, MLmodel y lectura del volumen. |
| No such artifact | Compruebe el archivo real en el almacén, no sólo la existencia del experimento. Use el ZIP portable si MLflow está apagado. |
| Volumen vacío tras Redeploy | La creación del volumen no copia el paquete. Transfiera classifier y confirme la ruta /models/classifier. |
| Permission denied | La API usa UID 10001. Corrija permisos de lectura y acceso del paquete, sin habilitar escritura pública. |
| Tablero sin conexión | Revise env-config.js, VITE_API_BASE_URL y /ready. La URL debe ser accesible desde el navegador. |
| Error CORS | El origen autorizado debe coincidir en protocolo, dominio y puerto con el tablero. Recree o despliegue la API. |
| Tiempo de espera del análisis | Revise logs y VITE_API_TIMEOUT_MS=120000. El mapa por oclusión necesita más tiempo que la clasificación. |
| Imagen rechazada | Respete JPG/PNG, 8 MiB, 8192 píxeles por lado y 16 megapíxeles. Revise también el país. |
| Falla el historial | Compruebe conexión, permisos y migración de PostgreSQL. Una respuesta fallida no confirma guardado. |
| No inicia sesión | Use una cuenta de esa base. demo/demo corresponde a las cuentas locales iniciales. |
| Aparece inferencia simulada | Compruebe INFERENCE_ENGINE=onnx, VITE_FORCE_MOCKS=false e identidad en model-info. |

##  Referencias de operación

Código: https://github.com/apchirinoc/maia-pds-microproyecto

Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/

Volúmenes de Railway: https://docs.railway.com/volumes

CLI para volúmenes: https://docs.railway.com/cli/volume
