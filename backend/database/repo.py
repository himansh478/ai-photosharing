"""All SQL lives here. The "photographers" table holds one row per event."""
from psycopg2.extras import RealDictCursor, execute_values

from backend.database.db import get_db_conn


# --- Events ---

def create_event(event_id, name, email, event_name, event_type, code, host_key_hash, contributor_key_hash):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO photographers
                       (id, name, email, event_name, event_type, code, host_key_hash, contributor_key_hash)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (event_id, name, email, event_name, event_type, code, host_key_hash, contributor_key_hash)
            )


def get_event_by_code(code):
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM photographers WHERE code=%s", (code,))
            return cur.fetchone()


def set_event_keys(event_id, host_key_hash, contributor_key_hash):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE photographers SET host_key_hash=%s, contributor_key_hash=%s WHERE id=%s",
                (host_key_hash, contributor_key_hash, event_id)
            )


def event_stats(event_id):
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT COUNT(*) FILTER (WHERE face_count > 0) AS faces_detected,
                          COUNT(*) FILTER (WHERE face_count = 0) AS common_photos
                   FROM photos WHERE photographer_id=%s""", (event_id,))
            stats = dict(cur.fetchone())
            cur.execute("""
                SELECT COUNT(*) AS n FROM download_logs dl
                JOIN user_sessions us ON dl.session_id=us.id
                WHERE us.photographer_id=%s
            """, (event_id,))
            stats['total_downloads'] = cur.fetchone()['n']
            cur.execute("SELECT COUNT(*) AS n FROM user_sessions WHERE photographer_id=%s", (event_id,))
            stats['total_users'] = cur.fetchone()['n']
            return stats


def event_file_paths(event_id):
    """Stored paths of every file that belongs to an event."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT file_path, thumbnail_path FROM photos WHERE photographer_id=%s", (event_id,))
            paths = [p for row in cur.fetchall() for p in row if p]
            cur.execute(
                "SELECT selfie_path FROM user_sessions WHERE photographer_id=%s AND selfie_path <> ''",
                (event_id,))
            return paths + [row[0] for row in cur.fetchall()]


def delete_event(event_id):
    """Delete an event's rows: download history, guest sessions, photos, then the event."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM download_logs
                   WHERE session_id IN (SELECT id FROM user_sessions WHERE photographer_id=%s)
                      OR photo_id IN (SELECT id FROM photos WHERE photographer_id=%s)""",
                (event_id, event_id))
            cur.execute("DELETE FROM user_sessions WHERE photographer_id=%s", (event_id,))
            cur.execute("DELETE FROM photos WHERE photographer_id=%s", (event_id,))
            cur.execute("DELETE FROM photographers WHERE id=%s", (event_id,))


def expired_events(default_retention_days):
    """Events older than their retention period."""
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, code, event_name, total_photos, created_at
                   FROM photographers
                   WHERE created_at < CURRENT_TIMESTAMP - (COALESCE(retention_days, %s) * INTERVAL '1 day')
                   ORDER BY created_at""",
                (default_retention_days,))
            return cur.fetchall()


# --- Photos ---

def photo_hash_exists(event_id, sha256):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM photos WHERE photographer_id=%s AND sha256=%s", (event_id, sha256))
            return cur.fetchone() is not None


def insert_photo(photo_id, event_id, file_key, thumbnail_key, filename, face_count,
                 embeddings_json, sha256, model_version):
    """Record a stored photo. Returns False if the same file was already in this event."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO photos (id, photographer_id, file_path, thumbnail_path, original_filename,
                                       face_count, embeddings, sha256, model_version)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (photographer_id, sha256) WHERE sha256 IS NOT NULL DO NOTHING""",
                (photo_id, event_id, file_key, thumbnail_key, filename, face_count,
                 embeddings_json, sha256, model_version)
            )
            if cur.rowcount != 1:
                return False
            cur.execute("UPDATE photographers SET total_photos = total_photos + 1 WHERE id = %s", (event_id,))
            return True


def event_face_rows(event_id):
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, thumbnail_path, embeddings FROM photos
                   WHERE photographer_id = %s AND face_count > 0 AND embeddings IS NOT NULL""",
                (event_id,)
            )
            return cur.fetchall()


def count_common_photos(event_id):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM photos WHERE photographer_id=%s AND face_count = 0", (event_id,))
            return cur.fetchone()[0]


def common_photos(event_id, limit, offset):
    """Photos without faces (decor, rituals, venue) that every guest of the event may see."""
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT id, thumbnail_path FROM photos
                   WHERE photographer_id=%s AND face_count = 0
                   ORDER BY uploaded_at, id LIMIT %s OFFSET %s""",
                (event_id, limit, offset))
            return cur.fetchall()


# --- Guest sessions ---

def create_session(session_id, event_id, matches, ttl_hours):
    """`matches` is a list of (photo_id, similarity). The selfie itself is never stored."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_sessions (id, photographer_id, selfie_path, matched_count, consent_at, expires_at)
                   VALUES (%s, %s, '', %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + (%s * INTERVAL '1 hour'))""",
                (session_id, event_id, len(matches), ttl_hours)
            )
            if matches:
                execute_values(
                    cur,
                    "INSERT INTO session_photos (session_id, photo_id, similarity) VALUES %s",
                    [(session_id, photo_id, similarity) for photo_id, similarity in matches]
                )


def get_active_session(session_id):
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM user_sessions WHERE id=%s AND expires_at > CURRENT_TIMESTAMP",
                (session_id,))
            return cur.fetchone()


def session_photo(session_id, photo_id):
    """The photo, if this session may open it: one it matched, or a common photo of its event."""
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT p.id, p.file_path, p.original_filename
                   FROM photos p
                   JOIN user_sessions s ON s.photographer_id = p.photographer_id
                   WHERE s.id = %s AND p.id = %s AND s.expires_at > CURRENT_TIMESTAMP
                     AND (p.face_count = 0
                          OR EXISTS (SELECT 1 FROM session_photos sp
                                     WHERE sp.session_id = s.id AND sp.photo_id = p.id))""",
                (session_id, photo_id))
            return cur.fetchone()


def log_download(download_id, session_id, photo_id):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO download_logs (id, session_id, photo_id) VALUES (%s,%s,%s)",
                (download_id, session_id, photo_id)
            )


def delete_session(session_id):
    """Remove a guest's session and its history. Returns True if it existed."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM download_logs WHERE session_id=%s", (session_id,))
            cur.execute("DELETE FROM user_sessions WHERE id=%s", (session_id,))
            return cur.rowcount == 1


def legacy_selfies():
    """Selfies saved by older versions of the app, which stored every one of them."""
    with get_db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, selfie_path FROM user_sessions WHERE selfie_path IS NOT NULL AND selfie_path <> ''")
            return cur.fetchall()


def clear_selfie_paths(session_ids):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE user_sessions SET selfie_path = '' WHERE id = ANY(%s)", (list(session_ids),))
