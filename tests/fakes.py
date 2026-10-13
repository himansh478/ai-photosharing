"""In-memory stand-ins for the database and the face model, used by the unit tests."""
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone


def _now():
    return datetime.now(timezone.utc)


class FakeRepo:
    """Implements the functions of backend.database.repo on plain dictionaries."""

    def __init__(self):
        self.events = {}
        self.photos = {}
        self.sessions = {}
        self.session_photos = set()
        self.downloads = []
        # The real database makes "insert unless this file is already there" atomic
        # (unique index + ON CONFLICT); the fake needs a lock to behave the same way.
        self._insert_lock = threading.Lock()

    # --- Events ---
    def create_event(self, event_id, name, email, event_name, event_type, code,
                     host_key_hash, contributor_key_hash):
        self.events[event_id] = dict(
            id=event_id, name=name, email=email, event_name=event_name, event_type=event_type,
            code=code, host_key_hash=host_key_hash, contributor_key_hash=contributor_key_hash,
            total_photos=0, retention_days=None, created_at=_now())

    def get_event_by_code(self, code):
        return next((dict(e) for e in self.events.values() if e['code'] == code), None)

    def set_event_keys(self, event_id, host_key_hash, contributor_key_hash):
        self.events[event_id].update(host_key_hash=host_key_hash, contributor_key_hash=contributor_key_hash)

    def event_stats(self, event_id):
        photos = [p for p in self.photos.values() if p['photographer_id'] == event_id]
        sessions = {s['id'] for s in self.sessions.values() if s['photographer_id'] == event_id}
        return {
            'faces_detected': sum(1 for p in photos if p['face_count'] > 0),
            'common_photos': sum(1 for p in photos if p['face_count'] == 0),
            'total_downloads': sum(1 for d in self.downloads if d[0] in sessions),
            'total_users': len(sessions),
        }

    def event_file_paths(self, event_id):
        paths = []
        for p in self.photos.values():
            if p['photographer_id'] == event_id:
                paths += [x for x in (p['file_path'], p['thumbnail_path']) if x]
        paths += [s['selfie_path'] for s in self.sessions.values()
                  if s['photographer_id'] == event_id and s['selfie_path']]
        return paths

    def delete_event(self, event_id):
        session_ids = {s for s, v in self.sessions.items() if v['photographer_id'] == event_id}
        photo_ids = {p for p, v in self.photos.items() if v['photographer_id'] == event_id}
        self.downloads = [d for d in self.downloads if d[0] not in session_ids and d[1] not in photo_ids]
        self.session_photos = {sp for sp in self.session_photos
                               if sp[0] not in session_ids and sp[1] not in photo_ids}
        for s in session_ids:
            del self.sessions[s]
        for p in photo_ids:
            del self.photos[p]
        self.events.pop(event_id, None)

    def expired_events(self, default_retention_days):
        now = _now()
        return [dict(e) for e in self.events.values()
                if e['created_at'] < now - timedelta(days=e['retention_days'] or default_retention_days)]

    # --- Photos ---
    def photo_hash_exists(self, event_id, sha256):
        return any(p['photographer_id'] == event_id and p['sha256'] == sha256 for p in self.photos.values())

    def insert_photo(self, photo_id, event_id, file_key, thumbnail_key, filename, face_count,
                     embeddings_json, sha256, model_version):
        with self._insert_lock:
            if sha256 and self.photo_hash_exists(event_id, sha256):
                return False
            self.photos[photo_id] = dict(
                id=photo_id, photographer_id=event_id, file_path=file_key, thumbnail_path=thumbnail_key,
                original_filename=filename, face_count=face_count, embeddings=embeddings_json,
                sha256=sha256, model_version=model_version, uploaded_at=time.time())
            self.events[event_id]['total_photos'] += 1
            return True

    def event_face_rows(self, event_id):
        return [dict(id=p['id'], thumbnail_path=p['thumbnail_path'], embeddings=p['embeddings'])
                for p in self.photos.values()
                if p['photographer_id'] == event_id and p['face_count'] > 0 and p['embeddings']]

    def count_common_photos(self, event_id):
        return sum(1 for p in self.photos.values()
                   if p['photographer_id'] == event_id and p['face_count'] == 0)

    def common_photos(self, event_id, limit, offset):
        rows = sorted((p for p in self.photos.values()
                       if p['photographer_id'] == event_id and p['face_count'] == 0),
                      key=lambda p: (p['uploaded_at'], p['id']))
        return [dict(id=p['id'], thumbnail_path=p['thumbnail_path']) for p in rows[offset:offset + limit]]

    # --- Guest sessions ---
    def create_session(self, session_id, event_id, matches, ttl_hours):
        self.sessions[session_id] = dict(
            id=session_id, photographer_id=event_id, selfie_path='', matched_count=len(matches),
            consent_at=_now(), expires_at=_now() + timedelta(hours=ttl_hours))
        for photo_id, _similarity in matches:
            self.session_photos.add((session_id, photo_id))

    def get_active_session(self, session_id):
        session = self.sessions.get(session_id)
        if session and session['expires_at'] and session['expires_at'] > _now():
            return dict(session)
        return None

    def session_photo(self, session_id, photo_id):
        session = self.get_active_session(session_id)
        photo = self.photos.get(photo_id)
        if not session or not photo or photo['photographer_id'] != session['photographer_id']:
            return None
        if photo['face_count'] == 0 or (session_id, photo_id) in self.session_photos:
            return dict(id=photo['id'], file_path=photo['file_path'],
                        original_filename=photo['original_filename'])
        return None

    def log_download(self, download_id, session_id, photo_id):
        self.downloads.append((session_id, photo_id))

    def delete_session(self, session_id):
        if session_id not in self.sessions:
            return False
        del self.sessions[session_id]
        self.downloads = [d for d in self.downloads if d[0] != session_id]
        self.session_photos = {sp for sp in self.session_photos if sp[0] != session_id}
        return True

    def legacy_selfies(self):
        return [dict(id=s['id'], selfie_path=s['selfie_path'])
                for s in self.sessions.values() if s['selfie_path']]

    def clear_selfie_paths(self, session_ids):
        for session_id in session_ids:
            self.sessions[session_id]['selfie_path'] = ''

    # --- Helpers for tests ---
    def add_photo(self, event_id, face_count=1):
        photo_id = str(uuid.uuid4())
        name = uuid.uuid4().hex
        self.insert_photo(photo_id, event_id, f'photos/{name}.jpg', f'thumbnails/thumb_{name}.webp',
                          'p.jpg', face_count, '[[1.0, 0.0]]' if face_count else None,
                          uuid.uuid4().hex, 'fake')
        return photo_id

    def event_id(self, code):
        return self.get_event_by_code(code)['id']


class FakeEngine:
    """Stands in for the InsightFace engine: every image has the configured number of faces."""

    model_version = 'fake'

    def __init__(self, ready=True, faces=1):
        self.ready = ready
        self.faces = faces
        self.load_requested = False

    def is_ready(self):
        return self.ready

    def state(self):
        return 'ready' if self.ready else 'loading'

    def load_in_background(self):
        self.load_requested = True

    def get_load_error(self):
        return None

    def _require_ready(self):
        from backend.models.face_engine import EngineNotReady
        if not self.ready:
            raise EngineNotReady('loading')

    def detect_and_embed(self, image_path):
        self._require_ready()
        return [[1.0, 0.0] for _ in range(self.faces)]

    def get_user_embedding(self, image_path):
        self._require_ready()
        return [1.0, 0.0] if self.faces else None


def wait_for(predicate, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False
