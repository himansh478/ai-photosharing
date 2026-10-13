from datetime import timedelta

import pytest

from backend import security
from backend.security import hash_key, signed_media_url
from backend.services import retention_service
from backend.services.storage_service import ObjectNotFound
from tests.conftest import make_image, register_event
from tests.fakes import _now

KEY = 'photos/0123456789abcdef.jpg'


@pytest.fixture
def stored_photo(storage, tmp_path):
    src = tmp_path / 'src.jpg'
    src.write_bytes(make_image())
    storage.put(str(src), KEY)
    return src.read_bytes()


# --- Media: only links signed by this server work ---

def test_signed_link_serves_the_photo(client, stored_photo):
    response = client.get(signed_media_url(KEY, ttl=60))
    assert response.status_code == 200
    assert response.data == stored_photo
    assert response.headers['Content-Type'] == 'image/jpeg'
    assert response.headers['Cache-Control'] == 'private, max-age=3600'
    assert 'Content-Disposition' not in response.headers


def test_download_link_is_sent_as_attachment(client, stored_photo):
    response = client.get(signed_media_url(KEY, ttl=60, download=True))
    assert response.status_code == 200
    assert response.headers['Content-Disposition'] == 'attachment; filename="0123456789abcdef.jpg"'


def test_media_without_valid_signature_is_refused(client, stored_photo):
    good = signed_media_url(KEY, ttl=60)
    assert client.get(f'/api/media/{KEY}').status_code == 403
    assert client.get(good[:-3] + 'AAA').status_code == 403
    assert client.get(good + '&dl=1').status_code == 403            # flag is part of the signature
    assert client.get(signed_media_url(KEY, ttl=-5)).status_code == 403
    assert client.get(good.replace(KEY, 'photos/ffffffffffffffff.jpg')).status_code == 403


def test_media_cannot_reach_other_files(client, stored_photo, monkeypatch):
    # Even a correctly signed link is refused for anything that is not a photo or thumbnail.
    for key in ('README.md', '.gitattributes', 'photos/../../etc/passwd'):
        assert client.get(signed_media_url(key, ttl=60)).status_code in (403, 404)


def test_signed_link_for_missing_object_is_404(client):
    assert client.get(signed_media_url('photos/00000000deadbeef.jpg', ttl=60)).status_code == 404


# --- Admin ---

def test_admin_endpoints_do_not_exist_without_a_secret(client, event, monkeypatch):
    monkeypatch.setattr(security.Config, 'ADMIN_SECRET', None)
    for path in (f"/api/admin/events/{event['code']}/keys", '/api/admin/purge-expired', '/api/admin/purge-selfies'):
        assert client.post(path, headers={'X-Admin-Secret': ''}).status_code == 404


def test_admin_endpoints_reject_wrong_secret(client, event, monkeypatch):
    monkeypatch.setattr(security.Config, 'ADMIN_SECRET', 'correct-horse')
    path = f"/api/admin/events/{event['code']}/keys"
    assert client.post(path).status_code == 403
    assert client.post(path, headers={'X-Admin-Secret': 'wrong'}).status_code == 403
    assert client.post(path, headers={'X-Admin-Secret': 'correct-horse'}).status_code == 200


def test_admin_can_issue_keys_for_a_locked_event(client, fake_repo, monkeypatch):
    monkeypatch.setattr(security.Config, 'ADMIN_SECRET', 's3cret')
    fake_repo.create_event('legacy', 'Old', 'o@x.co', 'Old Wedding', 'other', 'EVT-2026-ABC123', None, None)

    keys = client.post('/api/admin/events/evt-2026-abc123/keys', headers={'X-Admin-Secret': 's3cret'}).get_json()
    stored = fake_repo.get_event_by_code('EVT-2026-ABC123')
    assert stored['host_key_hash'] == hash_key(keys['host_key'])

    access = client.get('/api/photographer/access?code=EVT-2026-ABC123', headers={'X-Event-Key': keys['host_key']})
    assert access.get_json()['role'] == 'host'
    assert client.post('/api/admin/events/EVT-NOPE/keys', headers={'X-Admin-Secret': 's3cret'}).status_code == 404


def test_reissuing_keys_revokes_the_old_ones(client, event, monkeypatch):
    monkeypatch.setattr(security.Config, 'ADMIN_SECRET', 's3cret')
    client.post(f"/api/admin/events/{event['code']}/keys", headers={'X-Admin-Secret': 's3cret'})
    old = client.get(f"/api/photographer/access?code={event['code']}", headers={'X-Event-Key': event['host_key']})
    assert old.status_code == 403


# --- Retention ---

def _old_event_with_photo(client, fake_repo, storage, tmp_path, days_old):
    event = register_event(client, event_name=f'{days_old} days old')
    event_id = fake_repo.event_id(event['code'])
    fake_repo.events[event_id]['created_at'] = _now() - timedelta(days=days_old)
    photo_id = fake_repo.add_photo(event_id)
    src = tmp_path / f'{photo_id}.jpg'
    src.write_bytes(make_image())
    storage.put(str(src), fake_repo.photos[photo_id]['file_path'])
    return event, fake_repo.photos[photo_id]['file_path']


def test_purge_is_a_dry_run_unless_asked(client, fake_repo, storage, tmp_path, monkeypatch):
    monkeypatch.setattr(security.Config, 'ADMIN_SECRET', 's3cret')
    old, old_key = _old_event_with_photo(client, fake_repo, storage, tmp_path, days_old=120)
    recent, recent_key = _old_event_with_photo(client, fake_repo, storage, tmp_path, days_old=5)
    admin = {'X-Admin-Secret': 's3cret'}

    report = client.post('/api/admin/purge-expired', headers=admin).get_json()
    assert report['dry_run'] is True
    assert [e['code'] for e in report['events']] == [old['code']]
    assert len(fake_repo.events) == 2, 'a dry run must not delete anything'
    storage.open(old_key)

    report = client.post('/api/admin/purge-expired?dry_run=0', headers=admin).get_json()
    assert report['dry_run'] is False and report['files_removed'] == 2
    assert [e['code'] for e in fake_repo.events.values()] == [recent['code']]
    with pytest.raises(ObjectNotFound):
        storage.open(old_key)
    storage.open(recent_key)


def test_event_retention_override_is_respected(client, fake_repo, storage, tmp_path):
    event, _key = _old_event_with_photo(client, fake_repo, storage, tmp_path, days_old=40)
    assert retention_service.purge_expired(dry_run=True)['events'] == []
    fake_repo.events[fake_repo.event_id(event['code'])]['retention_days'] = 30
    assert len(retention_service.purge_expired(dry_run=True)['events']) == 1


def test_legacy_selfies_can_be_purged(client, event, fake_repo, storage, tmp_path):
    selfie_key = 'photos/5e1f1e5e1f1e5e1f.jpg'
    src = tmp_path / 'selfie.jpg'
    src.write_bytes(make_image())
    storage.put(str(src), selfie_key)
    fake_repo.create_session('old-session', fake_repo.event_id(event['code']), [], 1)
    fake_repo.sessions['old-session']['selfie_path'] = f'/api/proxy/{selfie_key}'

    assert retention_service.purge_legacy_selfies(dry_run=True) == {'dry_run': True, 'selfies': 1, 'files_removed': 0}
    storage.open(selfie_key)

    assert retention_service.purge_legacy_selfies(dry_run=False)['files_removed'] == 1
    assert fake_repo.sessions['old-session']['selfie_path'] == ''
    with pytest.raises(ObjectNotFound):
        storage.open(selfie_key)
