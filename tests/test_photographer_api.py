import io

from backend.extensions import limiter
from backend.security import hash_key
from backend.services.jobs import registry
from tests.conftest import make_image, register_event
from tests.fakes import wait_for


def _upload(client, code, key, images, job_id=None):
    data = {'code': code, 'photos': [(io.BytesIO(content), name) for name, content in images]}
    if job_id:
        data['job_id'] = job_id
    return client.post('/api/photographer/upload-batch', data=data,
                       headers={'X-Event-Key': key} if key else {},
                       content_type='multipart/form-data')


def _finish(job_id):
    job = registry.get(job_id)
    assert wait_for(job.is_finished), 'upload job did not finish'
    return job.snapshot()


# --- Registration ---

def test_register_returns_code_and_keys_and_stores_only_hashes(client, fake_repo):
    data = register_event(client)
    assert data['code'].startswith('EVT-') and len(data['code']) == 14
    assert data['host_key'].startswith('hk_') and data['contributor_key'].startswith('ck_')
    assert data['event_type'] == 'garba'

    stored = fake_repo.get_event_by_code(data['code'])
    assert stored['host_key_hash'] == hash_key(data['host_key'])
    assert stored['contributor_key_hash'] == hash_key(data['contributor_key'])
    assert data['host_key'] not in str(stored) and data['contributor_key'] not in str(stored)


def test_register_validates_input(client):
    post = lambda body: client.post('/api/photographer/register', json=body)
    good = {'name': 'A', 'email': 'a@b.co', 'event_name': 'E'}
    assert post({**good, 'email': ''}).status_code == 400
    assert post({**good, 'email': 'not-an-email'}).status_code == 400
    assert post({**good, 'name': 'x' * 500}).status_code == 400
    assert post({**good, 'event_type': 'rave'}).status_code == 400
    assert post(good).status_code == 201


def test_register_is_rate_limited(client):
    limiter.enabled = True
    limiter.reset()
    body = {'name': 'A', 'email': 'a@b.co', 'event_name': 'E'}
    codes = [client.post('/api/photographer/register', json=body).status_code for _ in range(11)]
    assert codes == [201] * 10 + [429]


# --- Who may upload ---

def test_guest_code_alone_cannot_upload(client, event, fake_repo):
    response = _upload(client, event['code'], None, [('a.jpg', make_image())])
    assert response.status_code == 403
    # Presenting the guest code as if it were the key does not work either.
    assert _upload(client, event['code'], event['code'], [('a.jpg', make_image())]).status_code == 403
    assert fake_repo.photos == {}


def test_key_of_another_event_cannot_upload(client, event):
    other = register_event(client, event_name='Other')
    assert _upload(client, event['code'], other['host_key'], [('a.jpg', make_image())]).status_code == 403


def test_unknown_code_is_rejected(client):
    assert _upload(client, 'EVT-DOESNOTEXIST', 'hk_x', [('a.jpg', make_image())]).status_code == 401


def test_event_without_keys_is_locked_until_admin_issues_them(client, fake_repo):
    fake_repo.create_event('legacy', 'Old', 'o@x.co', 'Old Wedding', 'other', 'EVT-2026-ABC123', None, None)
    response = _upload(client, 'EVT-2026-ABC123', '', [('a.jpg', make_image())])
    assert response.status_code == 403
    assert 'no upload key' in response.get_json()['error']


def test_access_reports_the_role_of_a_key(client, event):
    get = lambda key: client.get(f"/api/photographer/access?code={event['code']}", headers={'X-Event-Key': key})
    assert get(event['host_key']).get_json()['role'] == 'host'
    assert get(event['contributor_key']).get_json()['role'] == 'contributor'
    assert get('ck_wrong').status_code == 403


# --- Upload processing ---

def test_host_and_contributor_can_upload(client, event, fake_repo, storage):
    for key, color in ((event['host_key'], (1, 2, 3)), (event['contributor_key'], (4, 5, 6))):
        response = _upload(client, event['code'], key, [('a.jpg', make_image(color=color))])
        assert response.status_code == 202
        status = _finish(response.get_json()['job_id'])
        assert (status['status'], status['uploaded'], status['failed']) == ('completed', 1, 0)

    assert len(fake_repo.photos) == 2
    photo = next(iter(fake_repo.photos.values()))
    assert photo['file_path'].startswith('photos/') and photo['thumbnail_path'].startswith('thumbnails/')
    assert photo['model_version'] == 'fake' and len(photo['sha256']) == 64
    # Both the photo and its thumbnail really are in storage.
    assert sum(1 for _ in storage.open(photo['file_path'])[0]) >= 1
    assert storage.open(photo['thumbnail_path'])[1] == 'image/webp'


def test_every_file_is_accounted_for(client, event, fake_repo):
    same = make_image(color=(7, 7, 7))
    response = _upload(client, event['code'], event['host_key'], [
        ('good.jpg', make_image(color=(1, 1, 1))),
        ('same-1.jpg', same),
        ('same-2.jpg', same),
        ('fake.jpg', b'this is not an image'),
        ('anim.gif', make_image('GIF')),
    ])
    status = _finish(response.get_json()['job_id'])

    assert status['total'] == status['processed'] == 5
    assert (status['uploaded'], status['duplicates'], status['failed']) == (2, 1, 2)
    assert {f['filename'] for f in status['failed_files']} == {'fake.jpg', 'anim.gif'}
    assert len(fake_repo.photos) == 2


def test_photos_without_faces_are_kept_for_the_common_album(client, event, fake_repo, engine):
    engine.faces = 0
    response = _upload(client, event['code'], event['host_key'], [('decor.jpg', make_image())])
    status = _finish(response.get_json()['job_id'])

    assert (status['no_face'], status['uploaded'], status['failed']) == (1, 0, 0)
    photo = next(iter(fake_repo.photos.values()))
    assert photo['face_count'] == 0 and photo['embeddings'] is None


def test_upload_is_refused_while_engine_is_loading(client, event, fake_repo, engine):
    engine.ready = False
    response = _upload(client, event['code'], event['host_key'], [('a.jpg', make_image())])

    assert response.status_code == 503
    assert response.headers['Retry-After'] == '20'
    assert engine.load_requested is True
    assert fake_repo.photos == {}, 'no photo may be accepted and then silently dropped'


def test_several_requests_report_into_one_job(client, event):
    first = _upload(client, event['code'], event['host_key'], [('1.jpg', make_image(color=(1, 0, 0)))])
    job_id = first.get_json()['job_id']
    second = _upload(client, event['code'], event['host_key'],
                     [('2.jpg', make_image(color=(2, 0, 0))), ('3.jpg', make_image(color=(3, 0, 0)))],
                     job_id=job_id)
    assert second.get_json()['job_id'] == job_id

    status = _finish(job_id)
    assert (status['total'], status['processed'], status['uploaded']) == (3, 3, 3)
    assert client.get(f'/api/photographer/batch-status/{job_id}').get_json()['total'] == 3


def test_job_of_another_event_cannot_be_reused(client, event):
    other = register_event(client, event_name='Other')
    job_id = _upload(client, other['code'], other['host_key'], [('a.jpg', make_image())]).get_json()['job_id']
    response = _upload(client, event['code'], event['host_key'], [('b.jpg', make_image())], job_id=job_id)
    assert response.status_code == 404


def test_failed_storage_leaves_nothing_behind(client, event, fake_repo, storage, monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError('database is down')
    monkeypatch.setattr('backend.database.repo.insert_photo', broken)

    response = _upload(client, event['code'], event['host_key'], [('a.jpg', make_image())])
    status = _finish(response.get_json()['job_id'])

    assert status['failed'] == 1 and status['failed_files'][0]['reason'] == 'Could not store the photo'
    assert fake_repo.photos == {}
    import os
    leftovers = [f for _root, _dirs, files in os.walk(storage._root) for f in files]
    assert leftovers == [], 'files of a failed upload must be removed from storage'


# --- Stats and deletion are for the host only ---

def test_stats_require_the_host_key(client, event, fake_repo):
    fake_repo.add_photo(fake_repo.event_id(event['code']), face_count=2)
    fake_repo.add_photo(fake_repo.event_id(event['code']), face_count=0)
    url = f"/api/photographer/stats?code={event['code']}"

    assert client.get(url).status_code == 403
    assert client.get(url, headers={'X-Event-Key': event['contributor_key']}).status_code == 403
    data = client.get(url, headers={'X-Event-Key': event['host_key']}).get_json()
    assert (data['total_photos'], data['faces_detected'], data['common_photos']) == (2, 1, 1)


def test_only_the_host_can_delete_an_event(client, event, fake_repo, storage):
    response = _upload(client, event['code'], event['host_key'], [('a.jpg', make_image())])
    _finish(response.get_json()['job_id'])
    photo = next(iter(fake_repo.photos.values()))
    url = f"/api/photographer/event?code={event['code']}"

    assert client.delete(url, headers={'X-Event-Key': event['contributor_key']}).status_code == 403
    assert len(fake_repo.photos) == 1

    result = client.delete(url, headers={'X-Event-Key': event['host_key']})
    assert result.get_json() == {'deleted': True, 'files_removed': 2}
    assert fake_repo.events == {} and fake_repo.photos == {}
    import pytest
    from backend.services.storage_service import ObjectNotFound
    with pytest.raises(ObjectNotFound):
        storage.open(photo['file_path'])
