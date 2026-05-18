from __future__ import annotations

import os
from typing import Iterable

from utils.constants import MIN_JD_LENGTH


def validate_upload(
    uploaded_file,
    allowed_extensions: Iterable[str],
    allowed_mime_types: Iterable[str],
    max_upload_mb: int,
) -> list[str]:
    errors: list[str] = []
    if uploaded_file is None:
        errors.append("Please upload a PDF resume.")
        return errors

    filename = getattr(uploaded_file, "name", "")
    if not filename:
        errors.append("Uploaded file has no name.")
    extension = os.path.splitext(filename)[1].lower()
    if extension not in allowed_extensions:
        errors.append("Only PDF files are supported.")

    mime_type = getattr(uploaded_file, "type", "")
    if mime_type and mime_type not in allowed_mime_types:
        errors.append("Invalid file type. Please upload a PDF.")

    size = getattr(uploaded_file, "size", None)
    if size is None:
        try:
            size = len(uploaded_file.getvalue())
        except Exception:
            size = 0

    max_bytes = max_upload_mb * 1024 * 1024
    if size <= 0:
        errors.append("Uploaded file is empty.")
    elif size > max_bytes:
        errors.append(f"File exceeds {max_upload_mb} MB limit.")

    return errors


def validate_job_description(text: str) -> list[str]:
    errors: list[str] = []
    if not text or not text.strip():
        errors.append("Job description is required.")
        return errors
    if len(text.strip()) < MIN_JD_LENGTH:
        errors.append(
            f"Job description must be at least {MIN_JD_LENGTH} characters."
        )
    return errors
