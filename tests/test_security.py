import time

from backend import security
from backend.security import (hash_key, key_matches, new_guest_code, new_key, role_for_key,
                              signed_media_url, storage_key, verify_media_signature)


def _parts(url):
    path, query = url.split('?', 1)
    params = dict(p.split('=', 1) for p in query.split('&'))
    return path[len('/api/media/'):], params


def test_guest_codes_are_long_random_and_unambiguous():
    codes = {new_guest_code() for _ in range(200)}
    assert len(codes) == 200
    for code in codes:
        assert code.startswith('EVT-') and len(code) == 14
        assert not set(code[4:]) & set('01OI')


def test_keys_are_stored_as_hashes_and_compared_safely():
    key = new_key('hk_')
    assert key.startswith('hk_') and len(key) > 30
    assert hash_key(key) != key
    assert key_matches(key, hash_key(key))
    assert not key_matches(key + 'x', hash_key(key))
    assert not key_matches('', hash_key(key))
    assert not key_matches(key, None)


def test_role_for_key_distinguishes_host_contributor_and_strangers():
    host, contributor = new_key('hk_'), new_key('ck_')
    event = {'host_key_hash': hash_key(host), 'contributor_key_hash': hash_key(contributor)}
    assert role_for_key(event, host) == 'host'
    assert role_for_key(event, contributor) == 'contributor'
    assert role_for_key(event, 'EVT-ABCDEFGHJK') is None
    assert role_for_key({'host_key_hash': None, 'contributor_key_hash': None}, host) is None


def test_storage_key_accepts_only_our_own_objects():
    assert storage_key('photos/0123456789abcdef.jpg') == 'photos/0123456789abcdef.jpg'
    assert storage_key('/api/proxy/thumbnails/thumb_0123456789abcdef.jpg') == 'thumbnails/thumb_0123456789abcdef.jpg'
    for bad in ('', None, '.gitattributes', 'README.md', 'photos/../secret.jpg',
                '../photos/0123456789abcdef.jpg', 'photos/0123456789abcdef.exe',
                'other/0123456789abcdef.jpg', 'https://evil.example/photos/0123456789abcdef.jpg'):
        assert storage_key(bad) is None


def test_signed_link_verifies_and_rejects_tampering():
    key = 'photos/0123456789abcdef.jpg'
    path, params = _parts(signed_media_url(key, ttl=60))
    assert path == key
    assert verify_media_signature(key, params['exp'], params['sig'], download=False)
    # A signature is bound to the object, the expiry and the download flag.
    assert not verify_media_signature('photos/ffffffffffffffff.jpg', params['exp'], params['sig'], False)
    assert not verify_media_signature(key, str(int(params['exp']) + 1), params['sig'], False)
    assert not verify_media_signature(key, params['exp'], params['sig'], download=True)
    assert not verify_media_signature(key, params['exp'], '', False)
    assert not verify_media_signature(key, 'not-a-number', params['sig'], False)


def test_signed_link_expires():
    key = 'photos/0123456789abcdef.jpg'
    _, params = _parts(signed_media_url(key, ttl=-1))
    assert int(params['exp']) < time.time()
    assert not verify_media_signature(key, params['exp'], params['sig'], False)


def test_signature_depends_on_the_server_secret(monkeypatch):
    key = 'photos/0123456789abcdef.jpg'
    monkeypatch.setattr(security.Config, 'APP_SECRET', 'secret-one')
    _, params = _parts(signed_media_url(key, ttl=60))
    monkeypatch.setattr(security.Config, 'APP_SECRET', 'secret-two')
    assert not verify_media_signature(key, params['exp'], params['sig'], False)
