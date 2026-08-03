import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from .config import settings

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

CHUNK = 1024 * 1024


def path_for(stored_name: str) -> Path:
    return settings.upload_dir / stored_name


def save_upload(file: UploadFile) -> tuple[str, int]:
    """Stream an upload to disk under a random name. Returns (stored_name, size)."""
    if file.content_type not in settings.allowed_content_types:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type: {file.content_type}",
        )

    stored_name = f"{uuid.uuid4().hex}{EXTENSIONS[file.content_type]}"
    destination = path_for(stored_name)
    size = 0

    try:
        with destination.open("wb") as out:
            while chunk := file.file.read(CHUNK):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"File exceeds {settings.max_upload_bytes // (1024 * 1024)} MB limit",
                    )
                out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")

    return stored_name, size


def delete_file(stored_name: str) -> None:
    path_for(stored_name).unlink(missing_ok=True)
