import os
import sys

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# Local development reads secrets from .env; in production they come from the host's secret store.
load_dotenv(os.path.join(ROOT_DIR, '.env'))
load_dotenv(os.path.join(BASE_DIR, '.env'))


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('true', '1', 't', 'yes')


def _env_list(name, default):
    raw = os.environ.get(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(',') if item.strip()]


class Config:
    TESTING = 'pytest' in sys.modules or _env_bool('TESTING')
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5001))
    # Debug mode exposes an interactive debugger, so it must be asked for explicitly.
    DEBUG = os.environ.get('ENV') == 'development'

    # Supabase (PostgreSQL)
    DB_URL = os.environ.get('SUPABASE_DATABASE_URL')
    # Upper bound on simultaneous database connections; extra work waits its turn.
    DB_POOL_MAX = int(os.environ.get('DB_POOL_MAX', '10'))

    # Photo storage: 'hf' (private Hugging Face dataset) or 'local' (disk, for development and tests)
    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'hf')
    HF_TOKEN = os.environ.get('HF_TOKEN')
    HF_DATASET_ID = os.environ.get('HF_DATASET_ID')

    STORAGE_DIR = os.path.join(ROOT_DIR, 'storage')
    TEMP_DIR = os.path.join(STORAGE_DIR, 'temp')
    LOCAL_OBJECTS_DIR = os.path.join(STORAGE_DIR, 'objects')

    # Upload limits
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # one request (a chunk of photos)
    MAX_PHOTOS_PER_BATCH = 120
    MAX_PHOTO_BYTES = 25 * 1024 * 1024
    MAX_SELFIE_BYTES = 10 * 1024 * 1024
    MAX_IMAGE_PIXELS = 60_000_000
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'bmp'}
    ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP', 'BMP'}

    # Face recognition
    FACE_MODEL_PACK = os.environ.get('FACE_MODEL_PACK', 'buffalo_l')
    SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', '0.4'))
    THUMBNAIL_SIZE = (400, 400)
    INSIGHTFACE_DIR = os.path.join(ROOT_DIR, 'models_cache')

    # Secrets. APP_SECRET signs media URLs; without it a random per-process key is used,
    # which means links stop working after a restart.
    APP_SECRET = os.environ.get('APP_SECRET')
    # Admin endpoints stay disabled until ADMIN_SECRET is set.
    ADMIN_SECRET = os.environ.get('ADMIN_SECRET')

    # Link lifetimes (seconds)
    MEDIA_URL_TTL = int(os.environ.get('MEDIA_URL_TTL', 6 * 3600))
    DOWNLOAD_URL_TTL = int(os.environ.get('DOWNLOAD_URL_TTL', 600))
    SESSION_TTL_HOURS = int(os.environ.get('SESSION_TTL_HOURS', 7 * 24))

    # Retention: events older than this are eligible for purge. Automatic purge is opt-in.
    RETENTION_DAYS = int(os.environ.get('RETENTION_DAYS', '90'))
    RETENTION_AUTO_PURGE = _env_bool('RETENTION_AUTO_PURGE')

    # Number of reverse proxies in front of the app (needed for per-client rate limits).
    TRUSTED_PROXY_HOPS = int(os.environ.get('TRUSTED_PROXY_HOPS', '1'))

    CORS_ORIGINS = _env_list('CORS_ORIGINS', [
        'http://localhost:5173',
        'http://localhost:5174',
        'https://www.cwaya.me',
        'https://cwaya.me',
        'https://ai.cwaya.me',
    ])
    # Sites allowed to embed the app in an iframe.
    FRAME_ANCESTORS = _env_list('FRAME_ANCESTORS', [
        "'self'",
        'https://cwaya.me',
        'https://www.cwaya.me',
        'https://huggingface.co',
        'https://*.hf.space',
        'http://localhost:5173',
        'http://localhost:5174',
        'https://landing-page-redesign-beta.vercel.app',
    ])

    EVENT_TYPES = ('wedding', 'family', 'pooja', 'garba', 'other')


for d in [Config.TEMP_DIR, Config.INSIGHTFACE_DIR]:
    os.makedirs(d, exist_ok=True)
