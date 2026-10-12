from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from minio import Minio

MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "root"
MINIO_SECRET_KEY = "rootpassword"
MINIO_BUCKET = "gas-media"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)


def ensure_bucket_exists() -> None:
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)


def generate_latin_filename(file: UploadFile) -> str:
    extension = Path(file.filename or "").suffix.lower()

    if not extension:
        extension = ".bin"

    return f"{uuid4().hex}{extension}"


def upload_file_to_minio(file: UploadFile) -> str:
    ensure_bucket_exists()

    filename = generate_latin_filename(file)

    minio_client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=filename,
        data=file.file,
        length=file.size or -1,
        part_size=10 * 1024 * 1024,
        content_type=file.content_type or "application/octet-stream",
    )

    return f"http://localhost:9000/{MINIO_BUCKET}/{filename}"
