"""The SQL in backend.database.repo and the migrations, run against a real PostgreSQL.

Skipped unless TEST_DATABASE_URL points at a *local* throwaway database, because the
tests start by wiping it, e.g.

    TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres?sslmode=disable
"""
import os
import threading
import urllib.parse
import uuid

import pytest

TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL', '')
_LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1', 'postgres'}

pytestmark = pytest.mark.skipif(
    urllib.parse.urlparse(TEST_DATABASE_URL).hostname not in _LOCAL_HOSTS,
    reason='TEST_DATABASE_URL is not set to a local throwaway database')


def _uid():
    return str(uuid.uuid4())


def _execute(sql, params=None, fetch=False):
    from backend.database.db import get_db_conn
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if fetch else None


@pytest.fixture(scope='module')
def database():
    from backend.database import db
    original_url, original_pool = db.Config.DB_URL, db._pool
    db.Config.DB_URL = TEST_DATABASE_URL
    db._pool = None
    db.init_pool(maxconn=int(os.environ.get('TEST_DB_POOL_MAX', '2')))
    _execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public;')
    yield db
    db._pool.closeall()
    db._pool, db.Config.DB_URL = original_pool, original_url


@pytest.fixture(scope='module')
def repo(database):
    """A database that looked like production before migrations existed, then migrated."""
    with open(os.path.join(database.MIGRATIONS_DIR, '001_baseline.sql'), encoding='utf-8') as f:
        _execute(f.read())
    _execute("INSERT INTO photographers (id, name, email, event_name, code, total_photos) "
             "VALUES ('legacy-event', 'Old', 'old@x.co', 'Old Wedding', 'EVT-2026-ABC123', 1)")
    _execute("INSERT INTO photos (id, photographer_id, file_path, thumbnail_path, face_count, embeddings) "
             "VALUES ('legacy-photo', 'legacy-event', '/api/proxy/photos/aaaaaaaaaaaaaaaa.jpg', "
             "'/api/proxy/thumbnails/thumb_aaaaaaaaaaaaaaaa.jpg', 1, '[[0.1, 0.2]]')")
    _execute("INSERT INTO user_sessions (id, photographer_id, selfie_path, matched_count) "
             "VALUES ('legacy-session', 'legacy-event', '/api/proxy/photos/bbbbbbbbbbbbbbbb.jpg', 1)")

    database.run_migrations()
    database.run_migrations()   # applying twice must be harmless
    from backend.database import repo as real_repo
    return real_repo


def _new_event(repo, **overrides):
    event_id = _uid()
    args = dict(name='Asha', email='a@b.co', event_name='Garba', event_type='garba',
                code='EVT-' + uuid.uuid4().hex[:10].upper(), host_key_hash='h' + _uid(),
                contributor_key_hash='c' + _uid())
    args.update(overrides)
    repo.create_event(event_id, **args)
    return event_id, args['code']


def _new_photo(repo, event_id, face_count=1, sha256=None):
    photo_id, name = _uid(), uuid.uuid4().hex
    inserted = repo.insert_photo(photo_id, event_id, f'photos/{name}.jpg', f'thumbnails/thumb_{name}.webp',
                                 'p.jpg', face_count, '[[1.0, 0.0]]' if face_count else None,
                                 sha256 or uuid.uuid4().hex, 'buffalo_l')
    return photo_id, inserted


def test_migrations_are_recorded_once(repo):
    versions = [row[0] for row in _execute('SELECT version FROM schema_migrations ORDER BY version', fetch=True)]
    assert versions == ['001_baseline', '002_roles_sessions_lifecycle', '003_lock_down_public_api']


def test_existing_data_survives_migration(repo):
    event = repo.get_event_by_code('EVT-2026-ABC123')
    assert event['event_name'] == 'Old Wedding' and event['total_photos'] == 1
    # New columns exist; a pre-existing event has no keys, so uploads to it stay locked.
    assert event['host_key_hash'] is None and event['event_type'] == 'other'
    assert [r['id'] for r in repo.event_face_rows('legacy-event')] == ['legacy-photo']
    assert repo.legacy_selfies() == [{'id': 'legacy-session', 'selfie_path': '/api/proxy/photos/bbbbbbbbbbbbbbbb.jpg'}]
    # A session from before expiry tracking is treated as expired.
    assert repo.get_active_session('legacy-session') is None


def test_row_level_security_is_enabled_on_every_table(repo):
    rows = _execute("SELECT relname, relrowsecurity FROM pg_class WHERE relname IN "
                    "('photographers','photos','user_sessions','download_logs','session_photos','schema_migrations')",
                    fetch=True)
    assert len(rows) == 6 and all(enabled for _name, enabled in rows)


def test_event_roundtrip_and_keys(repo):
    event_id, code = _new_event(repo)
    event = repo.get_event_by_code(code)
    assert event['id'] == event_id and event['event_type'] == 'garba' and event['total_photos'] == 0
    repo.set_event_keys(event_id, 'new-host', 'new-contrib')
    event = repo.get_event_by_code(code)
    assert (event['host_key_hash'], event['contributor_key_hash']) == ('new-host', 'new-contrib')
    assert repo.get_event_by_code('EVT-MISSING') is None


def test_duplicate_code_is_rejected(repo):
    _event_id, code = _new_event(repo)
    import psycopg2
    with pytest.raises(psycopg2.IntegrityError):
        _new_event(repo, code=code)


def test_photo_insert_counts_once_and_rejects_duplicates(repo):
    event_id, code = _new_event(repo)
    _photo, inserted = _new_photo(repo, event_id, sha256='same-hash')
    assert inserted is True and repo.photo_hash_exists(event_id, 'same-hash')
    _photo, inserted = _new_photo(repo, event_id, sha256='same-hash')
    assert inserted is False
    assert repo.get_event_by_code(code)['total_photos'] == 1

    # The same file in a different event is a different photo.
    other_id, _ = _new_event(repo)
    assert not repo.photo_hash_exists(other_id, 'same-hash')
    assert _new_photo(repo, other_id, sha256='same-hash')[1] is True


def test_common_photos_are_paged_and_exclude_photos_with_faces(repo):
    event_id, _ = _new_event(repo)
    _new_photo(repo, event_id, face_count=2)
    common = [_new_photo(repo, event_id, face_count=0)[0] for _ in range(3)]
    assert repo.count_common_photos(event_id) == 3
    first = repo.common_photos(event_id, 2, 0)
    rest = repo.common_photos(event_id, 2, 2)
    assert len(first) == 2 and len(rest) == 1
    assert {r['id'] for r in first + rest} == set(common)
    assert [r['id'] for r in repo.event_face_rows(event_id)] != []


def test_session_access_rules(repo):
    event_id, _ = _new_event(repo)
    mine, _ = _new_photo(repo, event_id)
    not_mine, _ = _new_photo(repo, event_id)
    decor, _ = _new_photo(repo, event_id, face_count=0)
    other_event, _ = _new_event(repo)
    elsewhere, _ = _new_photo(repo, other_event, face_count=0)

    session_id = _uid()
    repo.create_session(session_id, event_id, [(mine, 0.8123)], ttl_hours=1)
    session = repo.get_active_session(session_id)
    assert session['matched_count'] == 1 and session['selfie_path'] == '' and session['consent_at'] is not None

    assert repo.session_photo(session_id, mine)['file_path'].startswith('photos/')
    assert repo.session_photo(session_id, decor) is not None       # common photo of the same event
    assert repo.session_photo(session_id, not_mine) is None        # someone else's photo
    assert repo.session_photo(session_id, elsewhere) is None       # another event entirely
    assert repo.session_photo('no-such-session', mine) is None

    # Expiry closes everything.
    _execute("UPDATE user_sessions SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 minute' WHERE id=%s",
             (session_id,))
    assert repo.get_active_session(session_id) is None
    assert repo.session_photo(session_id, mine) is None


def test_stats_and_delete_session(repo):
    event_id, _ = _new_event(repo)
    mine, _ = _new_photo(repo, event_id)
    _new_photo(repo, event_id, face_count=0)
    session_id = _uid()
    repo.create_session(session_id, event_id, [(mine, 0.9)], ttl_hours=1)
    repo.log_download(_uid(), session_id, mine)
    repo.log_download(_uid(), session_id, mine)

    assert repo.event_stats(event_id) == {'faces_detected': 1, 'common_photos': 1,
                                          'total_downloads': 2, 'total_users': 1}

    assert repo.delete_session(session_id) is True
    assert repo.delete_session(session_id) is False
    assert repo.event_stats(event_id)['total_downloads'] == 0
    assert _execute('SELECT COUNT(*) FROM session_photos WHERE session_id=%s', (session_id,), fetch=True)[0][0] == 0


def test_delete_event_removes_everything_and_nothing_else(repo):
    keep_id, keep_code = _new_event(repo)
    keep_photo, _ = _new_photo(repo, keep_id)
    event_id, code = _new_event(repo)
    photo, _ = _new_photo(repo, event_id)
    session_id = _uid()
    repo.create_session(session_id, event_id, [(photo, 0.9)], ttl_hours=1)
    repo.log_download(_uid(), session_id, photo)

    paths = repo.event_file_paths(event_id)
    assert len(paths) == 2 and all(p.startswith(('photos/', 'thumbnails/')) for p in paths)

    repo.delete_event(event_id)

    assert repo.get_event_by_code(code) is None
    assert repo.event_file_paths(event_id) == []
    for table, column in (('photos', 'photographer_id'), ('user_sessions', 'photographer_id')):
        assert _execute(f'SELECT COUNT(*) FROM {table} WHERE {column}=%s', (event_id,), fetch=True)[0][0] == 0
    assert repo.get_event_by_code(keep_code)['total_photos'] == 1
    assert [r['id'] for r in repo.event_face_rows(keep_id)] == [keep_photo]


def test_expired_events_use_per_event_retention(repo):
    old_id, old_code = _new_event(repo)
    custom_id, custom_code = _new_event(repo)
    _fresh_id, fresh_code = _new_event(repo)
    _execute("UPDATE photographers SET created_at = CURRENT_TIMESTAMP - INTERVAL '120 days' WHERE id=%s", (old_id,))
    _execute("UPDATE photographers SET created_at = CURRENT_TIMESTAMP - INTERVAL '40 days', retention_days = 30 "
             "WHERE id=%s", (custom_id,))

    expired = {e['code'] for e in repo.expired_events(90)}
    assert {old_code, custom_code} <= expired
    assert fresh_code not in expired


def test_legacy_selfie_paths_can_be_cleared(repo):
    repo.clear_selfie_paths(['legacy-session'])
    assert repo.legacy_selfies() == []


def test_busy_pool_makes_callers_wait_instead_of_failing(repo):
    event_id, _ = _new_event(repo)
    errors = []

    def work():
        try:
            for _ in range(5):
                repo.photo_hash_exists(event_id, 'no-such-hash')
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
