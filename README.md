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
