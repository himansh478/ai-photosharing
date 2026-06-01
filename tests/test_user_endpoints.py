import pytest
from backend.app import app as flask_app


class DummyCursor:
    def __init__(self, rows):
        self._rows = rows
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def execute(self, *args, **kwargs):
        pass
    def fetchone(self):
        return self._rows[0] if self._rows else None
    def fetchall(self):
        return self._rows
    def close(self):
        pass


class DummyConn:
    def __init__(self, rows):
        self._rows = rows
    def cursor(self, cursor_factory=None):
        return DummyCursor(self._rows)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def test_verify_code_valid(monkeypatch):
    # Return a single photographer row for any query
    dummy = DummyConn([{'id': 'pid1', 'event_name': 'E', 'name': 'Photog', 'total_photos': 10}])
    monkeypatch.setattr('backend.api.user.get_db_conn', lambda: dummy)

    client = flask_app.test_client()
    resp = client.post('/api/user/verify-code', json={'code': 'EVT-TEST-123'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['valid'] is True
    assert data['photographer_id'] == 'pid1'


def test_verify_code_invalid(monkeypatch):
    # Return no rows to simulate invalid code
    dummy = DummyConn([])
    monkeypatch.setattr('backend.api.user.get_db_conn', lambda: dummy)

    client = flask_app.test_client()
    resp = client.post('/api/user/verify-code', json={'code': 'EVT-INVALID'})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['valid'] is False
