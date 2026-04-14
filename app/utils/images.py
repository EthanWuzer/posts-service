import os
import boto3
from fastapi import HTTPException, UploadFile, status

ALLOWED_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png"}

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        account_id = os.environ["R2_ACCOUNT_ID"]
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
    return _s3_client


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
    """Upload image to R2. Returns the full public URL."""
    filename = f"{post_id}.{ext}"
    data = await file.read()
    bucket = os.environ["R2_BUCKET_NAME"]
    _get_s3_client().put_object(
        Bucket=bucket,
        Key=filename,
        Body=data,
        ContentType=file.content_type,
    )
    public_url = os.environ["R2_PUBLIC_URL"].rstrip("/")
    return f"{public_url}/{filename}"


def delete_image(key: str) -> None:
    """Delete object from R2. Accepts bare filename or full URL."""
    object_key = key.split("/")[-1]
    try:
        _get_s3_client().delete_object(
            Bucket=os.environ["R2_BUCKET_NAME"], Key=object_key
        )
    except Exception:
        pass
