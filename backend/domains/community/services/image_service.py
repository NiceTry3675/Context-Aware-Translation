
import hashlib
import uuid
from pathlib import Path

from backend.config.settings import get_settings

class ImageService:
    def __init__(self):
        self.settings = get_settings()

    def validate_image_upload(self, file_content: bytes, content_type: str) -> None:
        if len(file_content) > self.settings.max_file_size:
            raise ValueError(f"File size exceeds maximum of {self.settings.max_file_size} bytes")

        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if content_type not in allowed_types:
            raise ValueError(f"Invalid image type: {content_type}")

        signatures = {
            b'\xff\xd8\xff': 'image/jpeg',
            b'\x89\x50\x4e\x47': 'image/png',
            b'\x47\x49\x46\x38': 'image/gif',
            b'RIFF': 'image/webp'
        }

        for sig, expected_type in signatures.items():
            if file_content.startswith(sig) and content_type == expected_type:
                return

        raise ValueError("File signature doesn't match content type")

    def save_uploaded_image(self, file_content: bytes, filename: str) -> dict:
        file_ext = Path(filename).suffix
        file_hash = hashlib.md5(file_content).hexdigest()
        unique_name = f"{uuid.uuid4().hex}_{file_hash}{file_ext}"

        upload_dir = Path(self.settings.upload_dir) / "community"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / unique_name
        file_path.write_bytes(file_content)

        return {
            'url': f"/uploads/community/{unique_name}",
            'filename': unique_name,
            'size': len(file_content),
            'hash': file_hash
        }

    def init_upload_directory(self) -> None:
        upload_dir = Path(self.settings.upload_dir) / "community"
        upload_dir.mkdir(parents=True, exist_ok=True)
