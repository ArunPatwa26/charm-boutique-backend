from fastapi import UploadFile, HTTPException, status
from typing import List

from app.config.cloudinary import (
    upload_image,
    upload_multiple_images,
)


# ============================================================
# CONFIGURATION
# ============================================================

ALLOWED_EXTENSIONS = {
    "jpg", "jpeg", "png", "webp", "gif", "bmp",
}

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/jpg", "image/png",
    "image/webp", "image/gif", "image/bmp",
}

MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB (default)
MAX_PROOF_SIZE = 3 * 1024 * 1024  # 3 MB (payment proofs)


# ============================================================
# VALIDATE IMAGE
# ============================================================

def validate_image(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE,
) -> None:
    """
    Validate uploaded image file.
    """

    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has no filename",
        )

    # Check extension
    filename = file.filename.lower()
    extension = filename.rsplit(".", 1)[-1] if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File type '.{extension}' is not allowed. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # Check MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: {file.content_type}",
        )

    # Check size
    file.file.seek(0, 2)          # seek to end
    file_size = file.file.tell()
    file.file.seek(0)             # seek back to start

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {max_mb:.0f}MB",
        )


# ============================================================
# UPLOAD SINGLE IMAGE
# ============================================================

async def upload_single_image(
    file: UploadFile,
    folder: str = "ai-jewellery-shop",
    transformation: list = None,
    max_size: int = MAX_FILE_SIZE,
) -> dict:
    """
    Validate + upload a single image.

    Returns:
        dict: {
            "url": "https://res.cloudinary.com/...",
            "public_id": "ai-jewellery-shop/...",
        }
    """

    validate_image(file, max_size=max_size)

    file_data = await file.read()

    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has no content",
        )

    # Default transformation if none provided
    if not transformation:
        transformation = [
            {"width": 1000, "height": 1000, "crop": "limit"},
            {"quality": "auto"},
        ]

    try:
        result = await upload_image(
            file_data,
            folder=folder,
            transformation=transformation,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )

    if not result or not result.get("url"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary did not return a valid URL",
        )

    return result


# ============================================================
# UPLOAD MULTIPLE IMAGES
# ============================================================

async def upload_multiple_images_middleware(
    files: List[UploadFile],
    folder: str = "ai-jewellery-shop",
) -> List[str]:
    """
    Validate + upload multiple images.

    Returns:
        List[str]: List of Cloudinary URLs (for backward compatibility)
    """

    if not files:
        return []

    # Filter valid files
    valid_files = [f for f in files if f is not None and f.filename]

    if not valid_files:
        return []

    # Validate each
    for file in valid_files:
        validate_image(file)

    # Read file data
    files_data = []
    for file in valid_files:
        try:
            file_data = await file.read()
            if file_data:
                files_data.append(file_data)
        except Exception as e:
            print(f"⚠️ Failed to read file {file.filename}: {e}")

    if not files_data:
        return []

    # Upload all
    try:
        uploaded = await upload_multiple_images(
            files_data,
            folder=folder,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )

    # Return list of URLs (backward compatible)
    urls = [item["url"] for item in uploaded if item and item.get("url")]

    return urls


# ============================================================
# UPLOAD PAYMENT PROOF
# ============================================================

async def upload_payment_proof(
    file: UploadFile,
) -> dict:
    """
    Upload a UPI payment screenshot.

    Returns:
        dict: {"url": ..., "public_id": ...}
    """

    return await upload_single_image(
        file,
        folder="ai-jewellery-shop/payment-proofs",
        transformation=[
            {"width": 1200, "height": 1200, "crop": "limit"},
            {"quality": "auto"},
        ],
        max_size=MAX_PROOF_SIZE,
    )