import os
import sys
import uuid
import logging
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger(__name__)

class UploadService:
    def __init__(self):
        # Lazy import so it doesn't crash if HF isn't installed during build
        try:
            from huggingface_hub import HfApi
            self.api = HfApi()
        except ImportError:
            self.api = None

    def upload_to_hf(self, file_path: str, repo_path: str) -> str:
        """Uploads a local file to Hugging Face Private Dataset"""
        if not Config.HF_TOKEN or not Config.HF_DATASET_ID:
            logger.error("HF_TOKEN or HF_DATASET_ID is not set.")
            raise ValueError("Cloud storage API key missing.")
        
        if not self.api:
            raise RuntimeError("huggingface_hub is not installed.")

        try:
            self.api.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=repo_path,
                repo_id=Config.HF_DATASET_ID,
                repo_type="dataset",
                token=Config.HF_TOKEN
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upload to Hugging Face: {e}")
            raise

    def save_photo(self, file_path: str, filename: str) -> str:
        """
        Upload the main photo to Hugging Face.
        Returns the internal proxy safe URL.
        """
        ext = self._get_ext(filename)
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        path_in_repo = f"photos/{unique_name}"
        
        self.upload_to_hf(file_path, path_in_repo)
        
        # Return the proxy URL so frontend never sees the direct HF link
        return f"/api/proxy/{path_in_repo}"

    def generate_thumbnail(self, local_path: str) -> str:
        """
        Create a thumbnail locally and upload it to Hugging Face.
        Returns the internal proxy safe URL.
        """
        try:
            img = Image.open(local_path).convert('RGB')
            # Create thumbnail keeping aspect ratio
            img.thumbnail(Config.THUMBNAIL_SIZE if hasattr(Config, 'THUMBNAIL_SIZE') else (400,400), Image.LANCZOS)
            
            # Save thumbnail to a temporary local path
            thumb_filename = f"thumb_{uuid.uuid4().hex}.jpg"
            thumb_local_path = os.path.join(Config.TEMP_DIR, thumb_filename)
            img.save(thumb_local_path, format='JPEG', quality=85)

            # Upload thumbnail
            path_in_repo = f"thumbnails/{thumb_filename}"
            self.upload_to_hf(thumb_local_path, path_in_repo)
            
            # Cleanup local thumb
            self.cleanup_temp(thumb_local_path)

            return f"/api/proxy/{path_in_repo}"
        except Exception as e:
            logger.error(f"Thumbnail generation/upload failed: {e}")
            return ""

    def save_to_temp(self, file_storage) -> str:
        """Save file to local TEMP_DIR for processing. Returns absolute path."""
        os.makedirs(Config.TEMP_DIR, exist_ok=True)
        ext = self._get_ext(file_storage.filename)
        filename = f"proc_{uuid.uuid4().hex}.{ext}"
        dest = os.path.join(Config.TEMP_DIR, filename)
        file_storage.save(dest)
        return dest

    def save_temp_photo(self, file_storage) -> str:
        """Save user selfie to local TEMP_DIR for processing."""
        return self.save_to_temp(file_storage)

    def cleanup_temp(self, path: str):
        """Delete a temporary file."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Failed to cleanup temp file {path}: {e}")

    def _get_ext(self, filename: str) -> str:
        if filename and '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            if ext in Config.ALLOWED_EXTENSIONS:
                return ext
        return 'jpg'
