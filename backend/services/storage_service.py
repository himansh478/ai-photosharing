"""Where photo files live.

Two backends share one interface:
  * HFStorage    - a private Hugging Face dataset (production today)
  * LocalStorage - a folder on disk (development, tests, staging without credentials)
Files are addressed by a storage key such as 'photos/<hex>.jpg' and are only ever
handed to browsers through signed links (see backend.security).
"""
import logging
import os
import shutil
import uuid

from PIL import Image, ImageOps

from backend.config import Config

logger = logging.getLogger(__name__)


# Explicit rather than mimetypes.guess_type(): older Pythons and some systems do not know .webp.
_CONTENT_TYPES = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
    'webp': 'image/webp', 'bmp': 'image/bmp',
}


def content_type_for(key):
    return _CONTENT_TYPES.get(key.rsplit('.', 1)[-1].lower(), 'application/octet-stream')


class ObjectNotFound(Exception):
    pass


class HFStorage:
    def __init__(self):
        self._api = None

    def _client(self):
        if not Config.HF_TOKEN or not Config.HF_DATASET_ID:
            raise RuntimeError('HF_TOKEN or HF_DATASET_ID is not set.')
        if self._api is None:
            from huggingface_hub import HfApi
            self._api = HfApi()
        return self._api

    def put(self, local_path, key):
        self._client().upload_file(
            path_or_fileobj=local_path,
            path_in_repo=key,
            repo_id=Config.HF_DATASET_ID,
            repo_type='dataset',
            token=Config.HF_TOKEN,
        )

    def open(self, key):
        """Return (chunk iterator, content type) for one object."""
        import requests
        self._client()
        url = f'https://huggingface.co/datasets/{Config.HF_DATASET_ID}/resolve/main/{key}'
        response = requests.get(
            url,
            headers={'Authorization': f'Bearer {Config.HF_TOKEN}'},
            stream=True,
            timeout=(5, 30),
        )
        if response.status_code == 404:
            response.close()
            raise ObjectNotFound(key)
        response.raise_for_status()
        return response.iter_content(chunk_size=64 * 1024), content_type_for(key)

    def delete_many(self, keys):
        """Delete objects; missing ones are ignored. Returns the number of keys removed."""
        keys = list(dict.fromkeys(keys))
        if not keys:
            return 0
        from huggingface_hub import CommitOperationDelete
        from huggingface_hub.utils import EntryNotFoundError
        api = self._client()
        try:
            # One commit for the whole batch instead of one per file.
            api.create_commit(
                repo_id=Config.HF_DATASET_ID,
                repo_type='dataset',
                operations=[CommitOperationDelete(path_in_repo=k) for k in keys],
                commit_message=f'Delete {len(keys)} objects',
                token=Config.HF_TOKEN,
            )
            return len(keys)
        except Exception as e:
            logger.warning(f'Batch delete failed ({e}); deleting one by one.')
        removed = 0
        for key in keys:
            try:
                api.delete_file(path_in_repo=key, repo_id=Config.HF_DATASET_ID,
                                repo_type='dataset', token=Config.HF_TOKEN)
                removed += 1
            except EntryNotFoundError:
                removed += 1
            except Exception as e:
                logger.error(f'Failed to delete {key}: {e}')
        return removed

    def compact(self):
        """Drop the dataset's git history so deleted photos cannot be recovered from it."""
        self._client().super_squash_history(
            repo_id=Config.HF_DATASET_ID, repo_type='dataset', token=Config.HF_TOKEN)


class LocalStorage:
    def __init__(self, root=None):
        self._root = root or Config.LOCAL_OBJECTS_DIR

    def _path(self, key):
        return os.path.join(self._root, *key.split('/'))

    def put(self, local_path, key):
        dest = self._path(key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(local_path, dest)

    def open(self, key):
        path = self._path(key)
        if not os.path.isfile(path):
            raise ObjectNotFound(key)

        def chunks():
            with open(path, 'rb') as f:
                while True:
                    block = f.read(64 * 1024)
                    if not block:
                        return
                    yield block

        return chunks(), content_type_for(key)

    def delete_many(self, keys):
        removed = 0
        for key in dict.fromkeys(keys):
            try:
                os.remove(self._path(key))
            except FileNotFoundError:
                pass
            removed += 1
        return removed

    def compact(self):
        pass


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        _storage = LocalStorage() if Config.STORAGE_BACKEND == 'local' else HFStorage()
    return _storage


def extension_for(filename):
    if filename and '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in Config.ALLOWED_EXTENSIONS:
            return ext
    return 'jpg'


def save_to_temp(file_storage):
    """Save an uploaded file to the temp folder for processing. Returns its path."""
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    dest = os.path.join(Config.TEMP_DIR, f'proc_{uuid.uuid4().hex}.{extension_for(file_storage.filename)}')
    file_storage.save(dest)
    return dest


def cleanup_temp(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError as e:
        logger.error(f'Failed to clean up temp file {path}: {e}')


def store_photo(local_path, filename):
    """Upload the photo itself. Returns its storage key."""
    key = f'photos/{uuid.uuid4().hex}.{extension_for(filename)}'
    get_storage().put(local_path, key)
    return key


def store_thumbnail(local_path):
    """Create and upload a thumbnail. Returns its storage key."""
    thumb_path = os.path.join(Config.TEMP_DIR, f'thumb_{uuid.uuid4().hex}.webp')
    try:
        with Image.open(local_path) as img:
            # Apply the camera's rotation flag, otherwise portrait photos show sideways.
            img = ImageOps.exif_transpose(img).convert('RGB')
            img.thumbnail(Config.THUMBNAIL_SIZE, Image.LANCZOS)
            img.save(thumb_path, format='WEBP', quality=80)
        key = f'thumbnails/{os.path.basename(thumb_path)}'
        get_storage().put(thumb_path, key)
        return key
    finally:
        cleanup_temp(thumb_path)
