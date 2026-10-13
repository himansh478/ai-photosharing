import io
import os
from datetime import timedelta

import pytest

from backend.api import user as user_api
from tests.conftest import make_image, register_event
from tests.fakes import _now


@pytest.fixture
def matches(monkeypatch):
    """Control what the matcher returns, so these tests do not depend on numpy."""
    found = []

    def find_matches(_embedding, _event_id):
        return list(found)
    monkeypatch.setattr(user_api.matching_service, 'find_matches', find_matches)
    return found


def _search(client, code, consent='yes', image=None):
    data = {'code': code, 'photo': (io.BytesIO(image or make_image()), 'selfie.jpg')}
    if consent is not None:
        data['consent'] = consent
    return client.post('/api/user/upload-selfie', data=data, content_type='multipart/form-data')


def _add_match(fake_repo, matches, code, similarity=0.8):
    photo_id = fake_repo.add_photo(fake_repo.event_id(code))
    photo = fake_repo.photos[photo_id]
    matches.append({'photo_id': photo_id, 'thumbnail_path': photo['thumbnail_path'], 'similarity': similarity})
    return photo_id


# --- Code check ---

def test_verify_code(client, event):
    ok = client.post('/api/user/verify-code', json={'code': event['code'].lower()})
    assert ok.status_code == 200
    body = ok.get_json()
    assert body['valid'] is True and body['event_name'] == 'Garba Night'
    # Internal ids and key hashes never leave the server.
    assert set(body) == {'valid', 'event_name', 'photographer_name', 'total_photos'}

    assert client.post('/api/user/verify-code', json={'code': 'EVT-WRONGCODE1'}).status_code == 400
    assert client.post('/api/user/verify-code', json={}).status_code == 400


# --- Selfie search ---

def test_search_requires_consent(client, event, fake_repo, matches):
    for consent in (None, '', 'no'):
        response = _search(client, event['code'], consent=consent)
        assert response.status_code == 400
        assert 'agree' in response.get_json()['error']
    assert fake_repo.sessions == {}


def test_search_returns_only_signed_links(client, event, fake_repo, matches):
    photo_id = _add_match(fake_repo, matches, event['code'])
    body = _search(client, event['code']).get_json()

    assert body['matched_count'] == 1
    card = body['photos'][0]
    assert card['photo_id'] == photo_id and card['similarity'] == 0.8
    assert card['thumbnail_url'].startswith('/api/media/thumbnails/') and 'sig=' in card['thumbnail_url']
    assert card['download_url'] == f"/api/user/download/{photo_id}?session_id={body['session_id']}"
    assert fake_repo.sessions[body['session_id']]['consent_at'] is not None


def test_selfie_is_never_stored(client, event, fake_repo, matches, storage, tmp_path):
    body = _search(client, event['code']).get_json()

    assert fake_repo.sessions[body['session_id']]['selfie_path'] == ''
    stored = [f for _root, _dirs, files in os.walk(storage._root) for f in files]
    assert stored == []
    assert os.listdir(tmp_path / 'temp') == [], 'the temporary selfie must be deleted'


def test_search_rejects_bad_input(client, event, engine, matches):
    assert _search(client, 'EVT-WRONGCODE1').status_code == 401
    assert _search(client, event['code'], image=b'not an image').status_code == 400
    engine.faces = 0
    assert _search(client, event['code']).get_json()['error'] == 'No face detected in your photo.'
    engine.ready = False
    assert _search(client, event['code']).status_code == 503


# --- A session can open its own photos and nothing else ---

def test_download_is_limited_to_the_sessions_own_matches(client, event, fake_repo, matches):
    mine = _add_match(fake_repo, matches, event['code'])
    someone_elses = fake_repo.add_photo(fake_repo.event_id(event['code']))
    session_id = _search(client, event['code']).get_json()['session_id']

    ok = client.get(f'/api/user/download/{mine}?session_id={session_id}')
    assert ok.status_code == 302
    assert ok.headers['Location'].startswith('/api/media/photos/') and 'dl=1' in ok.headers['Location']
    assert fake_repo.downloads == [(session_id, mine)]

    # Same event, but a photo this guest was not matched to.
    assert client.get(f'/api/user/download/{someone_elses}?session_id={session_id}').status_code == 404
    assert client.get(f'/api/user/download/{mine}?session_id=made-up').status_code == 404
    assert client.get(f'/api/user/download/{mine}').status_code == 401


def test_session_of_another_event_cannot_download(client, event, fake_repo, matches):
    mine = _add_match(fake_repo, matches, event['code'])
    other = register_event(client, event_name='Other')
    matches.clear()
    other_session = _search(client, other['code']).get_json()['session_id']
    assert client.get(f'/api/user/download/{mine}?session_id={other_session}').status_code == 404


def test_expired_session_cannot_download(client, event, fake_repo, matches):
    mine = _add_match(fake_repo, matches, event['code'])
    session_id = _search(client, event['code']).get_json()['session_id']
    fake_repo.sessions[session_id]['expires_at'] = _now() - timedelta(minutes=1)

    assert client.get(f'/api/user/download/{mine}?session_id={session_id}').status_code == 404
    assert client.get(f'/api/user/common-photos?session_id={session_id}').status_code == 401


# --- Common album ---

def test_common_photos_are_visible_to_every_guest_of_the_event(client, event, fake_repo, matches):
    event_id = fake_repo.event_id(event['code'])
    decor = fake_repo.add_photo(event_id, face_count=0)
    fake_repo.add_photo(event_id, face_count=3)          # someone else's photo: not common
    body = _search(client, event['code']).get_json()
    assert body['common_count'] == 1 and body['matched_count'] == 0

    page = client.get(f"/api/user/common-photos?session_id={body['session_id']}").get_json()
    assert [p['photo_id'] for p in page['photos']] == [decor]
    assert page['next_offset'] is None
    assert client.get(f"/api/user/download/{decor}?session_id={body['session_id']}").status_code == 302

    assert client.get('/api/user/common-photos?session_id=made-up').status_code == 401


# --- Delete my data ---

def test_guest_can_delete_their_session(client, event, fake_repo, matches):
    mine = _add_match(fake_repo, matches, event['code'])
    session_id = _search(client, event['code']).get_json()['session_id']
    client.get(f'/api/user/download/{mine}?session_id={session_id}')

    assert client.delete(f'/api/user/session/{session_id}').get_json() == {'deleted': True}
    assert fake_repo.sessions == {} and fake_repo.downloads == [] and fake_repo.session_photos == set()
    assert client.get(f'/api/user/download/{mine}?session_id={session_id}').status_code == 404
    assert client.delete(f'/api/user/session/{session_id}').status_code == 404
