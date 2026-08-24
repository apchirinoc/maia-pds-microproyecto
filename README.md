# MaIA Microproyecto

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

## Flujo general de ejecución

1. Descargar los datos mediante DVC.
2. Instalar las dependencias del proyecto.
3. Ejecutar los notebooks de exploración y preparación de datos.
4. Ejecutar o entrenar el modelo desde los componentes definidos en `prototype/`.
5. Revisar los resultados y reportes generados.
6. Ejecutar las pruebas disponibles en `tests/`.
