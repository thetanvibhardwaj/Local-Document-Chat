"""File upload validation: extension whitelist and max size enforcement."""
from fastapi import HTTPException, UploadFile, status

from app.config import settings


def validate_upload(file: UploadFile) -> str:
    """
    Validate an uploaded file's extension and size.
    Returns the normalized (lowercase, no dot) file extension on success.
    Raises HTTPException(400) on any validation failure.
    """
    if not file.filename or "." not in file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must have a valid extension.")

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file type '.{extension}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # file.size is populated by Starlette when using UploadFile with spooled temp files.
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    return extension
