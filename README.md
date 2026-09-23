# BrainNeuroScan

Prototipo académico para clasificar imágenes MRI desde un tablero conectado a una API y un modelo empaquetado. No sustituye la interpretación clínica.

## Ejecutar el tablero, la API y el modelo

Consulte el [manual de instalación](docs/MANUAL_INSTALACION.md). Obtenga el paquete completo del modelo, colóquelo en `artifacts/classifier/`, complete `.env` a partir de `.env.example` y ejecute `docker compose up -d --build` desde la raíz. Compruebe `/ready` y la versión del motor antes de analizar imágenes.

- [Manual de usuario](docs/MANUAL_USUARIO.md)
- [Entrega del paquete del modelo](ml_project/ENTREGA_MODELO.md)
- [Contrato de inferencia](api/INFERENCIA.md)
- [Prueba del recorrido completo](docs/PRUEBA_INTEGRACION.md)

La API carga ONNX mediante MLflow pyfunc. Un paquete local permite servir predicciones aunque el servidor de tracking esté apagado. El modo de simulación requiere configuración explícita; una caída de la API no activa simulaciones en el tablero.

Las instrucciones siguientes permiten obtener el dataset para investigación. No son necesarias para instalar una solución que ya dispone de un modelo empaquetado.

## Descargar los datos

La fuente original de los datos se obtuvo de: [Brain Tumor (MRI Scans)](https://www.kaggle.com/datasets/rm1000/brain-tumor-mri-scans?resource=download).

1. Crea y activa un entorno virtual de python:

    ```bash
    $ python3 -m venv .venv
    $ source .venv/bin/activate
    (.venv) $ which python
    ```

2. Instala las dependencias para ejecutar DVC:

    ```bash
    (.venv) $ pip install -r requirements.dvc.txt
    (.venv) $ dvc --version
    ```

3. Descarga el archivo comprimido con los datos:

    ```bash
    (.venv) $ dvc pull -r public
    ```

    Verifica que el archivo `brain-tumor-mri-scans.zip` existe dentro de `data/`:

    ```bash
    (.venv) $ ls -al data/
    ```

4. Extrae los datos usando la herramienta de tu preferencia:

    ```bash
    (.venv) $ unzip -d data/ data/brain-tumor-mri-scans.zip
    ```

## Estructura del proyecto

El repositorio está organizado de la siguiente manera:

- `data/`: datos y referencias necesarias para la ejecución del proyecto.
- `notebooks/`: notebooks utilizados para exploración, análisis y experimentación.
- `prototype/`: implementación del prototipo de clasificación.
- `api/`: componentes asociados a la exposición del modelo mediante una API.
- `web/`: interfaz o componentes web del prototipo.
- `reports/`: resultados, análisis y documentación generada.
- `scripts/`: scripts auxiliares para procesamiento y ejecución.
- `tests/`: pruebas del proyecto.

## Investigación y entrenamiento

Los notebooks y `ml_project/` contienen los procesos de experimentación. Conserve el preprocesamiento y el orden de clases al empaquetar un modelo. No es necesario reentrenar para ejecutar un paquete aprobado.
