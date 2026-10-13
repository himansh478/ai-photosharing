import io
import os
import sys
import types

import pytest
from PIL import Image

os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('STORAGE_BACKEND', 'local')

# Some Windows machines block the native DLLs of numpy and psycopg2 (Application Control).
# Most tests only need the app to import, so inert stand-ins are used there; the tests
# that need the real libraries are skipped through `needs_numpy`.
HAVE_NUMPY = True
try:
    import numpy  # noqa: F401
except ImportError:
    HAVE_NUMPY = False
    numpy_stub = types.ModuleType('numpy')
    numpy_stub.ndarray = type('ndarray', (), {})
    sys.modules['numpy'] = numpy_stub

try:
    import psycopg2  # noqa: F401
except ImportError:
    psycopg2_stub = types.ModuleType('psycopg2')
    psycopg2_stub.Error = type('Error', (Exception,), {})
    pool_stub = types.ModuleType('psycopg2.pool')
    pool_stub.ThreadedConnectionPool = object
    extras_stub = types.ModuleType('psycopg2.extras')
    extras_stub.RealDictCursor = object
    extras_stub.execute_values = None
    sys.modules.update({'psycopg2': psycopg2_stub, 'psycopg2.pool': pool_stub,
                        'psycopg2.extras': extras_stub})

from backend.app import app as flask_app  # noqa: E402
from backend.database import repo  # noqa: E402
from backend.extensions import limiter  # noqa: E402
from backend.models import face_engine  # noqa: E402
from backend.services import storage_service  # noqa: E402
from backend.services.jobs import registry  # noqa: E402
from tests.fakes import FakeEngine, FakeRepo, wait_for  # noqa: E402

needs_numpy = pytest.mark.skipif(not HAVE_NUMPY, reason='numpy is not importable on this machine')


@pytest.fixture
def fake_repo(monkeypatch):
    fake = FakeRepo()
    for name in dir(repo):
        if not name.startswith('_') and callable(getattr(fake, name, None)):
            monkeypatch.setattr(repo, name, getattr(fake, name))
    return fake


@pytest.fixture
def storage(monkeypatch, tmp_path):
    local = storage_service.LocalStorage(root=str(tmp_path / 'objects'))
    monkeypatch.setattr(storage_service, '_storage', local)
    monkeypatch.setattr(storage_service.Config, 'TEMP_DIR', str(tmp_path / 'temp'))
    return local


@pytest.fixture
def engine(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr(face_engine, '_engine_instance', fake)
    return fake


@pytest.fixture
def client(fake_repo, storage, engine):
    limiter.enabled = False
    yield flask_app.test_client()
    # Uploads keep running on background threads after the request returns. Let them finish
    # before the fakes are torn down, or a straggler writes into the next test's database.
    finished = wait_for(lambda: all(job.is_finished() for job in list(registry._jobs.values())))
    registry._jobs.clear()
    limiter.enabled = True
    limiter.reset()
    assert finished, 'an upload job was still running when the test ended'


def make_image(fmt='JPEG', size=(64, 48), color=(120, 30, 200)):
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, format=fmt)
    return buf.getvalue()


def register_event(client, **overrides):
    body = {'name': 'Asha', 'email': 'asha@example.com', 'event_name': 'Garba Night', 'event_type': 'garba'}
    body.update(overrides)
    response = client.post('/api/photographer/register', json=body)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


@pytest.fixture
def event(client):
    return register_event(client)
