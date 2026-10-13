import io

from backend.extensions import limiter


def test_unknown_route_is_a_404_not_a_503(client):
    response = client.get('/this-route-does-not-exist')
    assert response.status_code == 404
    assert response.get_json() == {'error': 'Not Found'}


def test_wrong_method_is_a_405(client):
    assert client.get('/api/user/verify-code').status_code == 405


def test_unexpected_error_does_not_leak_details(client, fake_repo, monkeypatch):
    def boom(_code):
        raise RuntimeError('password=hunter2 host=db.internal')
    monkeypatch.setattr('backend.database.repo.get_event_by_code', boom)

    response = client.post('/api/user/upload-selfie', content_type='multipart/form-data',
                           data={'code': 'EVT-X', 'consent': 'yes', 'photo': (io.BytesIO(b'x'), 's.jpg')})
    assert response.status_code == 500
    assert response.get_json() == {'error': 'Internal server error'}
    assert b'hunter2' not in response.data


def test_rate_limit_answers_429(client):
    limiter.enabled = True
    limiter.reset()
    codes = [client.post('/api/user/verify-code', json={'code': 'EVT-NOPE'}).status_code
             for _ in range(32)]
    assert codes[:30] == [400] * 30
    assert codes[30:] == [429, 429]


def test_security_headers_are_set(client):
    response = client.get('/')
    csp = response.headers['Content-Security-Policy']
    assert "frame-ancestors 'self' https://cwaya.me https://www.cwaya.me" in csp
    assert "script-src 'self' blob:" in csp and "'unsafe-inline'" not in csp.split('script-src')[1].split(';')[0]
    assert "object-src 'none'" in csp
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['Referrer-Policy'] == 'no-referrer'


def test_api_responses_are_not_cached(client):
    assert client.get('/api/health').headers['Cache-Control'] == 'no-store'


def test_cors_allows_only_listed_origins(client):
    allowed = client.get('/api/health', headers={'Origin': 'https://www.cwaya.me'})
    assert allowed.headers.get('Access-Control-Allow-Origin') == 'https://www.cwaya.me'
    denied = client.get('/api/health', headers={'Origin': 'https://evil.example'})
    assert 'Access-Control-Allow-Origin' not in denied.headers


def test_health_reports_engine_state_without_loading_it(client, engine):
    assert client.get('/api/health').get_json() == {'status': 'healthy', 'face_engine': 'ready'}
    engine.ready = False
    assert client.get('/api/health').get_json()['face_engine'] == 'loading'
    assert engine.load_requested is False


def test_debug_and_open_proxy_endpoints_are_gone(client):
    assert client.get('/api/debug/db-test').status_code == 404
    assert client.get('/api/proxy/photos/0123456789abcdef.jpg').status_code == 404


def test_pages_are_served(client):
    for path in ('/', '/photographer', '/user'):
        response = client.get(path)
        assert response.status_code == 200
        assert b'<html' in response.data.lower()

