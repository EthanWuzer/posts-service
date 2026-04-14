import os

import boto3
from fastapi import HTTPException, UploadFile, status

ALLOWED_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png"}

_R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


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
    """Upload image to R2. Returns bare filename e.g. '<post_id>.jpg'."""
    filename = f"{post_id}.{ext}"
    data = await file.read()
    _s3().put_object(
        Bucket=os.environ["R2_BUCKET_NAME"],
        Key=filename,
        Body=data,
        ContentType=file.content_type,
    )
    return filename


def get_image_url(filename: str) -> str:
    """Return the stable public R2 URL for a filename."""
    return f"{_R2_PUBLIC_URL}/{filename}"


def delete_image(filename: str) -> None:
    """Delete object from R2; silently ignores errors."""
    try:
        _s3().delete_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=filename)
    except Exception:
        pass
