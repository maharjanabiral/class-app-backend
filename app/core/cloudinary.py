import cloudinary
import cloudinary.uploader
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

async def upload_file(file_bytes: bytes, filename: str, folder: str = "assignments") -> str:
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="auto",
        public_id=filename,
        overwrite=True,
    )
    return result["secure_url"]

async def delete_file(public_id: str) -> None:
    cloudinary.uploader.destroy(public_id, resource_type="auto")