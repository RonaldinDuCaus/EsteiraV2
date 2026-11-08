import io
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from ..config import settings


def image_url(filename):
    return f"/uploads/{filename}" if filename else None


def validate_image(data):
    if not data:
        raise HTTPException(400, "A imagem está vazia.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "A imagem ultrapassa o tamanho permitido.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > settings.max_image_pixels:
                raise HTTPException(413, "A resolução da imagem ultrapassa o limite configurado.")
            extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}.get(image.format)
            if not extension:
                raise HTTPException(400, "Use JPEG, PNG ou WebP.")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(400, "O arquivo enviado não é uma imagem válida.")
    return extension


def save_image(data, extension):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    (settings.upload_dir / filename).write_bytes(data)
    return filename


def image_path(filename):
    if Path(filename).name != filename:
        raise HTTPException(400, "Nome de arquivo inválido.")
    target = settings.upload_dir / filename
    if not target.is_file():
        raise HTTPException(404, "Imagem não encontrada.")
    return target
