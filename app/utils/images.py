import os
from pathlib import Path
from fastapi import HTTPException, UploadFile, status

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
ALLOWED_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png"}


def validate_image(file: UploadFile) -> str:
    """Raises 400 if not JPEG/PNG. Returns the resolved extension."""
    ext = ALLOWED_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{file.content_type}'. Only JPEG and PNG are accepted.",
        )
    return ext


async def save_image(file: UploadFile, post_id: str, ext: str) -> str:
    """Write upload to disk. Returns bare filename e.g. '<post_id>.jpg'."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{post_id}.{ext}"
    (UPLOAD_DIR / filename).write_bytes(await file.read())
    return filename


def delete_image(filename: str) -> None:
    """Delete file from UPLOAD_DIR; silently ignores missing files."""
    try:
        (UPLOAD_DIR / filename).unlink()
    except FileNotFoundError:
        pass
