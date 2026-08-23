# MaIA Microproyecto

## Descargar los datos

La fuente original de los datos se obtuvo de: [Brain Tumor (MRI Scans)](https://www.kaggle.com/datasets/rm1000/brain-tumor-mri-scans?resource=download).

Se requiere Python 3.11 o superior. Las dependencias actuales de DVC no son compatibles con Python 3.10.

1. Crea y activa un entorno virtual:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux o macOS
    # .venv\Scripts\Activate.ps1  # Windows PowerShell
    ```

2. Instala las dependencias de DVC y de la exploración:

    ```bash
    python -m pip install -r requirements.dvc.txt
    python -m pip install -r requirements.eda.txt
    python -m dvc --version
    ```

3. Descarga el archivo comprimido con los datos:

    ```bash
    python -m dvc pull -r public
    ```

    Verifica que el archivo `brain-tumor-mri-scans.zip` existe dentro de `data/`:

    ```bash
    ls -al data/
    ```

4. Extrae los datos. El comando puede repetirse sin crear carpetas duplicadas:

    ```bash
    python -m zipfile -e data/brain-tumor-mri-scans.zip data/brain-tumor-mri-scans
    ```

El ZIP, las imágenes extraídas, la caché de DVC y el entorno virtual permanecen fuera de Git.

## Exploración de datos

La exploración verifica el inventario, las propiedades de las imágenes, los archivos defectuosos y los duplicados exactos. También genera tablas y figuras reproducibles en español.

Ejecuta el análisis desde la raíz del repositorio:

```bash
python scripts/run_eda.py \
  --data-dir data/brain-tumor-mri-scans \
  --output-dir reports \
  --seed 42
```

En Windows PowerShell puede escribirse el mismo comando en una sola línea. Los resultados quedan en:

- `reports/eda_summary.md`: hallazgos, conclusiones y limitaciones.
- `reports/figures/`: distribución de clases, dimensiones y mosaico por clase.
- `reports/tables/`: inventario, calidad, duplicados y metadatos técnicos.
- `notebooks/01_eda_brain_mri.ipynb`: recorrido narrativo que reutiliza el script.

Ejecuta la prueba independiente del dataset completo con:

```bash
pytest
```
