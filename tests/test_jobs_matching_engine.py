import sys
import threading
import time
import types

from backend.models.face_engine import EngineNotReady, FaceEngine
from backend.services.jobs import Job, JobRegistry
from tests.conftest import needs_numpy


# --- Jobs ---

def test_job_counts_every_outcome_and_finishes_when_batches_close():
    job = Job('event-1')
    job.add_batch(3)
    job.record('uploaded')
    job.record('duplicate')
    assert job.snapshot()['status'] == 'processing'

    job.record('failed', 'bad.jpg', 'Not a valid image file')
    job.close_batch()

    snap = job.snapshot()
    assert snap['status'] == 'completed'
    assert (snap['total'], snap['processed'], snap['uploaded'], snap['duplicates'], snap['failed']) == (3, 3, 1, 1, 1)
    assert snap['failed_files'] == [{'filename': 'bad.jpg', 'reason': 'Not a valid image file'}]


def test_job_stays_open_while_any_batch_is_running():
    job = Job('event-1')
    job.add_batch(1)
    job.add_batch(1)
    job.close_batch()
    assert not job.is_finished()
    job.close_batch()
    assert job.is_finished()


def test_job_counters_are_thread_safe():
    job = Job('event-1')
    job.add_batch(4000)
    threads = [threading.Thread(target=lambda: [job.record('uploaded') for _ in range(500)]) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert job.snapshot()['uploaded'] == 4000


def test_registry_forgets_old_finished_jobs(monkeypatch):
    registry = JobRegistry()
    old = registry.create('event-1')
    old.add_batch(1)
    old.close_batch()
    running = registry.create('event-1')
    running.add_batch(1)

    monkeypatch.setattr(time, 'time', lambda real=time.time: real() + 2 * 3600)
    registry.create('event-2')

    assert registry.get(old.id) is None
    assert registry.get(running.id) is running, 'a job that is still running must be kept'


# --- Face engine loading ---

def _fake_insightface(monkeypatch, loads, fail=False, delay=0.0):
    class FaceAnalysis:
        def __init__(self, name, allowed_modules=None, **kwargs):
            loads.append({'name': name, 'allowed_modules': allowed_modules, **kwargs})
            time.sleep(delay)
            if fail:
                raise RuntimeError('model download failed')

        def prepare(self, **kwargs):
            pass

    package = types.ModuleType('insightface')
    app_module = types.ModuleType('insightface.app')
    app_module.FaceAnalysis = FaceAnalysis
    package.app = app_module
    monkeypatch.setitem(sys.modules, 'insightface', package)
    monkeypatch.setitem(sys.modules, 'insightface.app', app_module)
    monkeypatch.setitem(sys.modules, 'torch', None)   # behave as on a CPU-only host


def test_engine_loads_only_detection_and_recognition(monkeypatch):
    loads = []
    _fake_insightface(monkeypatch, loads)
    engine = FaceEngine(model_dir='/models', model_pack='buffalo_l')
    assert engine.state() == 'not_loaded' and loads == []

    engine.load()

    assert engine.is_ready() and engine.model_version == 'buffalo_l'
    assert loads == [{'name': 'buffalo_l', 'allowed_modules': ['detection', 'recognition'], 'root': '/models'}]


def test_engine_loads_once_even_when_many_threads_ask(monkeypatch):
    loads = []
    _fake_insightface(monkeypatch, loads, delay=0.05)
    engine = FaceEngine()
    threads = [threading.Thread(target=engine.load) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(loads) == 1


def test_failed_load_is_reported_and_can_be_retried(monkeypatch):
    loads = []
    _fake_insightface(monkeypatch, loads, fail=True)
    engine = FaceEngine()
    engine.load()
    assert engine.state() == 'failed' and 'download failed' in engine.get_load_error()

    # A failure must never look like "this photo has no faces".
    try:
        engine.detect_and_embed('whatever.jpg')
        raise AssertionError('expected EngineNotReady')
    except EngineNotReady:
        pass

    _fake_insightface(monkeypatch, loads, fail=False)
    engine.load()
    assert engine.is_ready() and engine.get_load_error() is None


# --- Matching ---

@needs_numpy
def test_cosine_similarity():
    import numpy as np
    import pytest
    from backend.services.matching_service import MatchingService
    svc = MatchingService()
    assert svc._cosine_similarity(np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])) == pytest.approx(1.0)
    assert svc._cosine_similarity(np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])) == pytest.approx(0.0)
    assert svc._cosine_similarity(np.zeros(3), np.array([1.0, 0.0, 0.0])) == 0.0


@needs_numpy
def test_find_matches_uses_best_face_and_threshold(fake_repo):
    import json
    import numpy as np
    from backend.services.matching_service import MatchingService
    fake_repo.create_event('e1', 'A', 'a@b.co', 'E', 'other', 'EVT-AAAAAAAAAA', 'h', 'c')

    def add(embeddings):
        photo_id = fake_repo.add_photo('e1')
        fake_repo.photos[photo_id]['embeddings'] = json.dumps(embeddings)
        return photo_id

    exact = add([[0.0, 1.0], [1.0, 0.0]])        # second face is the guest
    close = add([[0.9, 0.436]])                  # similar enough
    stranger = add([[0.0, 1.0]])                 # someone else entirely
    fake_repo.add_photo('e1', face_count=0)      # no faces: never a match

    found = MatchingService().find_matches(np.array([1.0, 0.0], dtype=np.float32), 'e1')

    assert [m['photo_id'] for m in found] == [exact, close]
    assert found[0]['similarity'] == 1.0 and 0.89 < found[1]['similarity'] < 0.91
    assert stranger not in [m['photo_id'] for m in found]
    assert all(m['thumbnail_path'].startswith('thumbnails/') for m in found)
