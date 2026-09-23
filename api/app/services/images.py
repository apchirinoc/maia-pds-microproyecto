"""Validación de archivos sin transformar los píxeles que recibirá el modelo."""
import io
import warnings

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000
MAX_DIMENSION = 8192
FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG"}


def verify_image(content: bytes, declared_type: str) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format != FORMATS[declared_type]:
                    raise HTTPException(415, "El contenido no coincide con el formato JPG o PNG declarado")
                width, height = image.size
                if max(width, height) > MAX_DIMENSION or width * height > MAX_PIXELS:
                    raise HTTPException(413, "La imagen supera las dimensiones permitidas")
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise HTTPException(422, "El archivo está vacío, dañado o no es una imagen válida") from error


async def read_image(file: UploadFile) -> bytes:
    try:
        if file.content_type not in FORMATS:
            raise HTTPException(415, "Sólo se aceptan imágenes JPG o PNG")
        content = await file.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise HTTPException(413, "La imagen supera los 8 MiB")
        if not content:
            raise HTTPException(422, "La imagen está vacía")
        await run_in_threadpool(verify_image, content, file.content_type)
        return content
    finally:
        await file.close()
