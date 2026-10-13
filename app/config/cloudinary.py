import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# CONFIGURE CLOUDINARY
# ============================================================
def configure_cloudinary():
    """
    Configure Cloudinary with environment variables.
    """
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise RuntimeError(
            "Cloudinary credentials are not configured in the .env file"
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

    return cloudinary


cloudinary_instance = configure_cloudinary()


# ============================================================
# UPLOAD IMAGE — Returns dict with url + public_id
# ============================================================
async def upload_image(
    file_data: bytes,
    folder: str = "ai-jewellery-shop",
    transformation: list = None,
) -> dict:
    """
    Upload an image to Cloudinary.

    Returns:
        dict: {
            "url": "https://res.cloudinary.com/...",
            "public_id": "ai-jewellery-shop/...",
        }
    """
    try:
        upload_options = {
            "folder": folder,
            "resource_type": "image",
        }

        if transformation:
            upload_options["transformation"] = transformation

        result = cloudinary_instance.uploader.upload(
            file_data,
            **upload_options,
        )

        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }

    except Exception as e:
        raise Exception(f"Failed to upload image: {str(e)}")


# ============================================================
# UPLOAD MULTIPLE IMAGES — Returns list of dicts
# ============================================================
async def upload_multiple_images(
    files_data: list,
    folder: str = "ai-jewellery-shop",
) -> list:
    """
    Upload multiple images to Cloudinary.

    Returns:
        list: [
            {"url": "...", "public_id": "..."},
            ...
        ]
    """
    uploaded = []

    for file_data in files_data:
        result = await upload_image(
            file_data,
            folder,
            transformation=[
                {"width": 1000, "height": 1000, "crop": "limit"},
                {"quality": "auto"},
            ],
        )
        uploaded.append(result)

    return uploaded


# ============================================================
# DELETE IMAGE
# ============================================================
async def delete_image(public_id: str) -> dict:
    """
    Delete an image from Cloudinary.
    """
    try:
        result = cloudinary_instance.uploader.destroy(public_id)
        return result
    except Exception as e:
        raise Exception(f"Failed to delete image: {str(e)}")


# ============================================================
# EXTRACT PUBLIC ID FROM URL
# ============================================================
def extract_public_id(image_url: str) -> str:
    """
    Extract public_id from a Cloudinary URL.

    Example:
        Input:  https://res.cloudinary.com/cloud/image/upload/v123/ai-jewellery-shop/products/abc.jpg
        Output: ai-jewellery-shop/products/abc
    """
    if not image_url:
        return None

    try:
        parts = image_url.split("/")

        # Find the "upload" segment
        for i, part in enumerate(parts):
            if part == "upload":
                # public_id starts after the version (v123456)
                if i + 2 < len(parts):
                    public_id_with_ext = "/".join(parts[i + 2:])
                    # Remove file extension
                    public_id = public_id_with_ext.rsplit(".", 1)[0]
                    return public_id

        return None

    except Exception:
        return None