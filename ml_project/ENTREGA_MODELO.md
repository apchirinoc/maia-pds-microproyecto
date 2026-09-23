# Entregar el modelo para inferencia

La API consume un paquete MLflow `pyfunc` que recibe bytes de JPG o PNG y devuelve probabilidades. El paquete debe incluir los pesos, el código de preprocesamiento y sus dependencias. Un registro con métricas en MLflow no basta si sus artefactos no se pueden descargar.

## Contrato que debe conservarse

| Elemento | Requisito |
|---|---|
| Entrada | DataFrame con columna `image`, una imagen codificada por fila |
| Salida | Una fila por imagen y cuatro columnas de probabilidades finitas entre 0 y 1, cuya suma sea 1 |
| Clases | `glioma`, `meningioma`, `pituitary`, `healthy`, en el orden exacto aprendido por el modelo |
| Preprocesamiento | Tamaño, canales, normalización y transformaciones de la evaluación del entrenamiento |
| Identidad | Versión, run de origen, arquitectura y SHA-256 de los pesos |
| Metadatos MLflow | `classes`, `preprocess_label`, `preprocess_fingerprint`, `weights_sha256`, `model_version`; métricas de evaluación si están disponibles |

No deduzca el orden de clases por orden alfabético ni aplique CLAHE a un modelo que no se entrenó con esa transformación. El empaquetador de este repositorio implementa `pipelines/preprocessing.py`; úselo solamente si coincide con el entrenamiento. Un modelo entrenado con otro preprocesamiento necesita su propio wrapper compatible con el contrato de entrada y salida.

## Paquete portable

Para los pesos del notebook `notebooks/PdS_Training_Experiments.ipynb`, incorporado en el PR #28, use `export_colab_model.py`. Ese entrenamiento utiliza RGB con resize bilinear a 224×224 y normalización ImageNet, sin CLAHE. La salida guardada de `dataset.classes` es `glioma`, `healthy`, `meningioma`, `pituitary`.

Instale `requirements-train.txt` para la conversión. El notebook registra PyTorch 2.11.0 y Torchvision 0.26.0; use esas versiones al recuperar los pesos. Este ejemplo lee el logged model seleccionado y exporta el paquete, sin reentrenar:

```sh
python export_colab_model.py --tracking-uri https://mlflow.alexchirino.online --model-uri models:/m-3ffa1794dfcc403e84d962aa00221599 --run-id 59d7f03737964b7e9d3fcb3bcf0f8e58 --version resnet18-1 --sample /ruta/glioma.jpg /ruta/healthy.jpg /ruta/meningioma.jpg /ruta/pituitary.jpg --output /ruta/entrega/classifier
```

El comando necesita acceso efectivo a los artefactos. También admite una carpeta MLflow local mediante `--model-uri`, omitiendo `--tracking-uri`. Verifica el tensor frente a las transformaciones del notebook y compara probabilidades PyTorch/ONNX antes de confirmar la exportación. Si falla la comparación, no utilice el paquete generado. Las métricas del notebook usan promedio `weighted`; no deben presentarse como métricas macro.

Para otros pesos ONNX cuyo preprocesamiento ya coincida con el pipeline del repositorio:

En un entorno Python 3.13, instale `pip install -r ml_project/requirements.txt`. Desde `ml_project/`, ejecute con los archivos reales del entrenamiento:

```sh
python package_model.py --onnx /ruta/classifier.onnx --preprocess-config /ruta/preprocess_config.json --classes glioma meningioma pituitary healthy --sample /ruta/muestra.png --output /ruta/entrega/classifier --version 1 --run-id RUN_ID_REAL --architecture ARQUITECTURA_REAL
```

Sustituya el orden del ejemplo por el orden comprobado. `--probabilities` indica que ONNX ya devuelve probabilidades; omítalo si devuelve logits. `--metrics` acepta un JSON con métricas entre 0 y 1, por ejemplo las claves `test_accuracy`, `test_precision`, `test_recall` y `test_f1_score` exportadas del run. La versión debe ser estable y caber en 20 caracteres para el catálogo de la API.

El comando guarda el paquete completo en disco y valida una predicción. No reentrena ni escribe en el servidor de MLflow. Conserve toda la carpeta, incluyendo `MLmodel`, `artifacts/`, `code/`, `requirements.txt` y los archivos del entorno. Copiar sólo el `.onnx` pierde el contrato y el preprocesamiento.

Comprima esa carpeta y distribúyala mediante almacenamiento persistente accesible al equipo. Al instalar, descomprímala como `artifacts/classifier/` y configure `MLFLOW_MODEL_URI=/models/classifier` en Docker. El volumen se monta en modo de sólo lectura. Los paquetes Python serializados deben provenir del equipo responsable del modelo.

## Verificación antes de entregar

Compare la salida del paquete con la del código de evaluación sobre las mismas imágenes, una por clase como mínimo. Conserve las probabilidades esperadas, el orden de clases, la huella del preprocesamiento y una tolerancia numérica justificada. No basta con que coincida la clase ganadora.

Pruebe el paquete después de moverlo a otra carpeta y sin acceso a MLflow. `tests/test_portable_package.py` comprueba esta portabilidad y rechaza pesos alterados; usa pesos sintéticos para probar la infraestructura, no para medir precisión clínica.

Para generar exclusivamente un paquete de integración:

```sh
python tests/create_fixture_package.py /ruta/qa/artifacts/classifier
```

Requiere las dependencias de pruebas. Su versión es `fixture-1` y su arquitectura `SYNTHETIC TEST ONLY`. Nunca lo entregue como modelo entrenado.

## Carga desde MLflow

La API admite `MLFLOW_TRACKING_URI`, `MLFLOW_MODEL_NAME` y `MLFLOW_MODEL_VERSION`. Deje `MLFLOW_MODEL_URI` vacío para resolver el registro. Una versión explícita es reproducible; si usa un alias, se resuelve una vez al arrancar y se fija su versión durante la vida del proceso.

El servidor de tracking y su almacenamiento de artefactos deben ser accesibles en ese arranque. Para un laboratorio que se apaga, distribuya primero el paquete portable. Cambiar un alias no recarga automáticamente una API en ejecución.
