import logging
import threading

from backend.config import Config

logger = logging.getLogger(__name__)


class EngineNotReady(RuntimeError):
    """The model is still loading or failed to load; nothing can be detected yet."""


class ImageUnreadable(ValueError):
    """The file could not be decoded as an image."""


class FaceEngine:
    """InsightFace face detection + embedding extraction.

    Creating the object is cheap. The model is loaded by load(), which is meant to run
    in a background thread so the web server can start answering immediately.
    """

    def __init__(self, model_dir=None, model_pack=None):
        self._app = None
        self._model_dir = model_dir
        self._model_pack = model_pack or Config.FACE_MODEL_PACK
        self._state = 'not_loaded'   # not_loaded | loading | ready | failed
        self._load_error = None
        self._load_lock = threading.Lock()
        self._state_lock = threading.Lock()

    @property
    def model_version(self):
        """Stored with every embedding: embeddings from different models cannot be compared."""
        return self._model_pack

    def load(self):
        """Load the model once. Safe to call from several threads; later calls are no-ops."""
        with self._load_lock:
            if self._state == 'ready':
                return
            self._state = 'loading'
            try:
                from insightface.app import FaceAnalysis
                kwargs = {}
                if self._model_dir:
                    kwargs['root'] = self._model_dir
                # Only detection and recognition are used. The model pack also ships
                # gender/age and two landmark models; loading them would run three
                # extra networks on every face for results nobody reads.
                app = FaceAnalysis(name=self._model_pack,
                                   allowed_modules=['detection', 'recognition'], **kwargs)
                # ctx_id=0 → GPU, ctx_id=-1 → CPU
                try:
                    import torch
                    ctx = 0 if torch.cuda.is_available() else -1
                except ImportError:
                    ctx = -1
                # det_size=(640,640) is recommended for CPU-only hosts;
                # (896,896) was causing OOM crashes on Hugging Face
                app.prepare(ctx_id=ctx, det_size=(640, 640), det_thresh=0.35)
                self._app = app
                self._load_error = None
                self._state = 'ready'
                logger.info(f"InsightFace '{self._model_pack}' loaded (ctx={'GPU' if ctx >= 0 else 'CPU'})")
            except Exception as e:
                logger.error(f"InsightFace load failed: {e}")
                self._load_error = str(e)
                self._state = 'failed'

    def load_in_background(self):
        """Start loading unless the model is already loaded or loading."""
        # Claim the 'loading' state before starting the thread, so a burst of requests
        # arriving while the model is down starts one loader, not one per request.
        with self._state_lock:
            if self._state in ('ready', 'loading'):
                return
            self._state = 'loading'
        threading.Thread(target=self.load, daemon=True, name='face-engine-load').start()

    def is_ready(self):
        return self._state == 'ready'

    def state(self):
        return self._state

    def get_load_error(self):
        return self._load_error

    def _faces(self, image_path):
        if not self.is_ready():
            raise EngineNotReady(self._load_error or 'Face engine is still loading')
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            raise ImageUnreadable(image_path)
        return self._app.get(img)

    def detect_and_embed(self, image_path: str):
        """
        Detect all faces in an image and return their embeddings.

        Returns:
            list of np.ndarray, one 512-dim embedding per detected face.
            Empty list only when the image really has no faces; problems raise
            EngineNotReady or ImageUnreadable so a failure is never mistaken for "no faces".
        """
        return [face.normed_embedding for face in self._faces(image_path)
                if face.normed_embedding is not None]

    def get_user_embedding(self, image_path: str):
        """
        Get a single embedding from a user selfie.
        Takes the largest (most prominent) face if multiple found.

        Returns:
            np.ndarray of shape (512,) or None if no face detected.
        """
        faces = self._faces(image_path)
        if not faces:
            return None
        # Pick largest face by bounding box area
        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return largest.normed_embedding


_engine_instance = None
_engine_lock = threading.Lock()


def get_engine() -> FaceEngine:
    """The process-wide engine. Never loads the model itself; see FaceEngine.load()."""
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = FaceEngine(model_dir=Config.INSIGHTFACE_DIR)
        return _engine_instance
