import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load environment variables from .env file explicitly
load_dotenv(os.path.join(BASE_DIR, '.env'))

ROOT_DIR = os.path.dirname(BASE_DIR)

class Config:
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5001))
    DEBUG = os.environ.get('ENV') != 'production'

    # Supabase (PostgreSQL)
    DB_URL = os.environ.get('SUPABASE_DATABASE_URL')

    # Hugging Face (Private Photo Storage)
    HF_TOKEN = os.environ.get('HF_TOKEN')
    HF_DATASET_ID = os.environ.get('HF_DATASET_ID')

    # Storage (Local Temp for processing)
    STORAGE_DIR = os.path.join(ROOT_DIR, 'storage')
    TEMP_DIR = os.path.join(STORAGE_DIR, 'temp')

    # Upload
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    MAX_PHOTOS_PER_BATCH = 120
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'bmp'}

    # Face Recognition
    SIMILARITY_THRESHOLD = 0.4   # InsightFace cosine similarity threshold (Lower = more recall)
    THUMBNAIL_SIZE = (400, 400)

    # InsightFace model cache dir
    INSIGHTFACE_DIR = os.path.join(ROOT_DIR, 'models_cache')


# Create directories on import
for d in [Config.TEMP_DIR, Config.INSIGHTFACE_DIR]:
    os.makedirs(d, exist_ok=True)
