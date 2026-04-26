import cv2
import numpy as np
import os
import sys
import logging

logger = logging.getLogger(__name__)


class FaceEngine:
    """
    InsightFace-based face detection + embedding extraction.
    Falls back to a dummy mode if insightface is not installed.
    """

    def __init__(self, model_dir=None):
        self._app = None
        self._ready = False
        self._model_dir = model_dir
        self._load()

    def _load(self):
        try:
            import insightface
            from insightface.app import FaceAnalysis
            kwargs = {}
            if self._model_dir:
                kwargs['root'] = self._model_dir
            self._app = FaceAnalysis(name='buffalo_l', **kwargs)
            # ctx_id=0 → GPU, ctx_id=-1 → CPU
            try:
                import torch
                ctx = 0 if torch.cuda.is_available() else -1
            except ImportError:
                ctx = -1
            self._app.prepare(ctx_id=ctx, det_size=(896, 896), det_thresh=0.35)
            self._ready = True
            logger.info(f"InsightFace loaded (ctx={'GPU' if ctx >= 0 else 'CPU'})")
        except Exception as e:
            logger.error(f"InsightFace load failed: {e}")
            self._ready = False

    def is_ready(self):
        return self._ready

    def detect_and_embed(self, image_path: str):
        """
        Detect all faces in an image and return their embeddings.

        Returns:
            list of np.ndarray, one 512-dim embedding per detected face.
            Empty list if no faces found or engine not ready.
        """
        if not self._ready:
            return []

        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Could not read image: {image_path}")
            return []

        try:
            faces = self._app.get(img)
            embeddings = [face.normed_embedding for face in faces if face.normed_embedding is not None]
            return embeddings
        except Exception as e:
            logger.error(f"Embedding extraction failed for {image_path}: {e}")
            return []

    def get_user_embedding(self, image_path: str):
        """
        Get a single embedding from a user selfie.
        Takes the largest (most prominent) face if multiple found.

        Returns:
            np.ndarray of shape (512,) or None if no face detected.
        """
        if not self._ready:
            return None

        img = cv2.imread(image_path)
        if img is None:
            return None

        try:
            faces = self._app.get(img)
            if not faces:
                return None
            # Pick largest face by bounding box area
            largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            return largest.normed_embedding
        except Exception as e:
            logger.error(f"User embedding failed: {e}")
            return None


# Singleton instance (loaded once)
_engine_instance = None

def get_engine(model_dir=None) -> FaceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = FaceEngine(model_dir=model_dir)
    return _engine_instance
