import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from database.db import get_db_conn, json_to_embeddings
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)


class MatchingService:

    def find_matches(self, user_embedding: np.ndarray, photographer_id: str):
        """
        Find all event photos where the user's face appears.
        """
        with get_db_conn() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT id, thumbnail_path, file_path, embeddings FROM photos WHERE photographer_id = %s AND embeddings IS NOT NULL",
                (photographer_id,)
            )
            rows = cursor.fetchall()
            cursor.close()

        matches = []
        for row in rows:
            photo_embeddings = json_to_embeddings(row['embeddings'])
            if not photo_embeddings:
                continue

            # Check against each face in the photo
            best_sim = 0.0
            for emb in photo_embeddings:
                sim = self._cosine_similarity(user_embedding, emb)
                if sim > best_sim:
                    best_sim = sim

            if best_sim >= Config.SIMILARITY_THRESHOLD:
                # In cloud mode, paths are already full URLs
                matches.append({
                    'photo_id': row['id'],
                    'thumbnail_url': row['thumbnail_path'],
                    'download_url': f'/api/user/download/{row["id"]}',
                    'similarity': round(float(best_sim), 4)
                })

        # Sort by highest similarity first
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two normed embeddings."""
        try:
            a = np.array(a, dtype=np.float32).flatten()
            b = np.array(b, dtype=np.float32).flatten()
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))
        except Exception:
            return 0.0
