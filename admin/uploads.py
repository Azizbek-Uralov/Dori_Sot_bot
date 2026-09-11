import os
import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOAD_DIR = Path("static/uploads/products")
ALLOWED_CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


async def save_product_image(file: UploadFile) -> str:
    ext = ALLOWED_CONTENT_TYPES.get(file.content_type or "")
    if ext is None:
        raise ValueError(f"Unsupported image type: {file.content_type}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / filename
    content = await file.read()
    path.write_bytes(content)
    return str(path)


def delete_product_image(image_path: str | None) -> None:
    if not image_path:
        return
    try:
        os.remove(image_path)
    except OSError:
        pass
