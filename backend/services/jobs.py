"""Progress tracking for photo uploads.

One job covers a whole upload, however many requests the browser splits it into.
Jobs live in memory: they describe work in progress, not anything that must survive.
"""
import threading
import time
import uuid

_MAX_FAILED_FILES = 200
_FINISHED_TTL = 3600        # keep a finished job visible for an hour
_ABANDONED_TTL = 24 * 3600


class Job:
    OUTCOMES = ('uploaded', 'no_face', 'duplicate', 'failed')

    def __init__(self, event_id):
        self.id = str(uuid.uuid4())
        self.event_id = event_id
        self._lock = threading.Lock()
        self._total = 0
        self._open_batches = 0
        self._counts = dict.fromkeys(self.OUTCOMES, 0)
        self._failed_files = []
        self._updated = time.time()

    def add_batch(self, size):
        with self._lock:
            self._total += size
            self._open_batches += 1
            self._updated = time.time()

    def close_batch(self):
        with self._lock:
            self._open_batches -= 1
            self._updated = time.time()

    def record(self, outcome, filename=None, reason=None):
        """Count one finished file. Every file ends in exactly one outcome, so none goes missing."""
        with self._lock:
            self._counts[outcome] += 1
            if outcome == 'failed' and len(self._failed_files) < _MAX_FAILED_FILES:
                self._failed_files.append({'filename': filename or 'unknown', 'reason': reason or 'Unknown error'})
            self._updated = time.time()

    def is_finished(self):
        with self._lock:
            return self._open_batches == 0

    def idle_seconds(self):
        with self._lock:
            return time.time() - self._updated

    def snapshot(self):
        with self._lock:
            counts = dict(self._counts)
            return {
                'job_id': self.id,
                'status': 'completed' if self._open_batches == 0 else 'processing',
                'total': self._total,
                'processed': sum(counts.values()),
                'uploaded': counts['uploaded'],
                'no_face': counts['no_face'],
                'duplicates': counts['duplicate'],
                'failed': counts['failed'],
                'failed_files': list(self._failed_files),
            }


class JobRegistry:
    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()

    def create(self, event_id):
        job = Job(event_id)
        with self._lock:
            self._prune()
            self._jobs[job.id] = job
        return job

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def _prune(self):
        for job_id, job in list(self._jobs.items()):
            idle = job.idle_seconds()
            if idle > _ABANDONED_TTL or (job.is_finished() and idle > _FINISHED_TTL):
                del self._jobs[job_id]


registry = JobRegistry()
