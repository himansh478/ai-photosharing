"""Run the app locally without the real face model, for working on the pages and the API.

The InsightFace model is large and needs native libraries, so this swaps in a toy engine:
an image's "face" is simply its average colour. Photos of one colour therefore behave like
photos of one person, and grey images behave like photos without faces. Never use it for
anything but local development.

    SUPABASE_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres?sslmode=disable \
        python scripts/dev_server.py

Photos are stored on disk under storage/objects (STORAGE_BACKEND=local).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('STORAGE_BACKEND', 'local')
os.environ.setdefault('TRUSTED_PROXY_HOPS', '0')

from PIL import Image  # noqa: E402

from backend.models import face_engine  # noqa: E402


class ColourEngine:
    """Stands in for FaceEngine: one 'face' per colourful image, none for grey ones."""

    model_version = 'dev-colour'

    def is_ready(self):
        return True

    def state(self):
        return 'ready'

    def load(self):
        pass

    def load_in_background(self):
        pass

    def get_load_error(self):
        return None

    def _embedding(self, image_path):
        try:
            with Image.open(image_path) as img:
                r, g, b = img.convert('RGB').resize((1, 1)).getpixel((0, 0))
        except OSError:
            raise face_engine.ImageUnreadable(image_path)
        if max(r, g, b) - min(r, g, b) < 30:
            return None
        norm = (r * r + g * g + b * b) ** 0.5
        return [r / norm, g / norm, b / norm]

    def detect_and_embed(self, image_path):
        embedding = self._embedding(image_path)
        return [embedding] if embedding else []

    def get_user_embedding(self, image_path):
        return self._embedding(image_path)


face_engine._engine_instance = ColourEngine()

from backend.app import app  # noqa: E402

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f'Dev server with the toy colour engine on http://127.0.0.1:{port}')
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
