import glob
import json
import logging
import os
import re
import socket
import threading
import urllib.parse as urlparse
from contextlib import contextmanager

import numpy as np
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

from backend.config import Config

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')
# Arbitrary constant; serialises migrations when several instances start at once.
_MIGRATION_LOCK_ID = 727274001

_pool = None
_pool_lock = threading.Lock()
# psycopg2's pool raises when it is exhausted instead of waiting. This semaphore makes
# callers queue for a free connection, so a burst of work slows down rather than fails.
_pool_slots = None
_POOL_WAIT_SECONDS = 30


def _candidate_urls(db_url):
    """The configured URL first, then the Supabase pooler variants that work from IPv4-only hosts."""
    urls = [db_url]
    match = re.match(
        r"postgres(?:ql)?://(?P<user>[^:]+):(?P<pass>[^@]+)@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<db>.+)",
        db_url)
    if not match:
        return urls
    d = match.groupdict()
    password, host, port, db = d['pass'], d['host'], d['port'] or '5432', d['db']

    if '.supabase.co' in host and 'pooler' not in host:
        # db.<project>.supabase.co -> <project>
        host_parts = host.split('.')
        if len(host_parts) >= 3:
            project_id = host_parts[-3]
            pooler_host = os.environ.get('SUPABASE_POOLER_HOST', 'aws-0-ap-south-1.pooler.supabase.com')
            urls.append(f"postgresql://postgres.{project_id}:{password}@{pooler_host}:6543/{db}?sslmode=require")
            urls.append(f"postgresql://postgres.{project_id}:{password}@{pooler_host}:5432/{db}?sslmode=require")

    if port == '5432':
        urls.append(db_url.replace(':5432/', ':6543/'))
    return urls


def _connect_kwargs(url):
    """Keyword arguments for psycopg2 (avoids URL-encoding problems with passwords)."""
    parsed = urlparse.urlparse(url)
    hostname = parsed.hostname
    # An explicit ?sslmode= in the URL wins; the Supabase pooler always needs TLS.
    sslmode = urlparse.parse_qs(parsed.query).get('sslmode', [None])[0]
    kwargs = dict(
        database=parsed.path[1:],
        user=urlparse.unquote(parsed.username) if parsed.username else None,
        password=urlparse.unquote(parsed.password) if parsed.password else None,
        host=hostname,
        port=parsed.port or 5432,
        connect_timeout=5,
        sslmode=sslmode or ('require' if 'pooler' in (hostname or '') else 'prefer'),
        gssencmode='disable',
    )
    try:
        # Some hosts cannot reach IPv6-only database addresses; pin the IPv4 address when there is one.
        kwargs['hostaddr'] = socket.gethostbyname(hostname)
    except OSError as dns_err:
        logger.warning(f"DNS resolution failed for {hostname}: {dns_err}")
    return kwargs


def init_pool(minconn=1, maxconn=None):
    global _pool, _pool_slots
    maxconn = maxconn or Config.DB_POOL_MAX
    db_url = Config.DB_URL
    if not db_url:
        logger.error("SUPABASE_DATABASE_URL is not set!")
        raise RuntimeError("Database URL missing.")

    working = None
    for url in _candidate_urls(db_url):
        masked = url.split('@')[-1]
        logger.info(f"Trying database connection: {masked}")
        try:
            kwargs = _connect_kwargs(url)
            psycopg2.connect(**kwargs).close()
            working = kwargs
            logger.info("Successfully connected to database!")
            break
        except Exception as e:
            logger.warning(f"Connection failed for {masked}: {e}")

    if working is None:
        logger.error("All database connection attempts failed.")
        raise RuntimeError("Could not connect to any database endpoint.")

    with _pool_lock:
        if _pool is None:
            _pool = ThreadedConnectionPool(minconn, maxconn, **working)
            _pool_slots = threading.BoundedSemaphore(maxconn)
            logger.info(f"Database Connection Pool Initialized (max {maxconn} connections).")


def _checkout():
    """A live connection from the pool; a connection the server already closed is replaced once."""
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except psycopg2.Error:
        _pool.putconn(conn, close=True)
    conn = _pool.getconn()
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
    return conn


@contextmanager
def get_db_conn():
    """Yield a pooled connection; commits on success and rolls back on error."""
    if _pool is None:
        init_pool()

    if not _pool_slots.acquire(timeout=_POOL_WAIT_SECONDS):
        raise RuntimeError('Timed out waiting for a free database connection')
    try:
        conn = _checkout()
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except psycopg2.Error:
                pass
            raise
        finally:
            _pool.putconn(conn)
    finally:
        _pool_slots.release()


def run_migrations():
    """Apply every migration in database/migrations that this database has not seen yet."""
    files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, '*.sql')))
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in cur.fetchall()}
            for path in files:
                version = os.path.splitext(os.path.basename(path))[0]
                if version in applied:
                    continue
                with open(path, encoding='utf-8') as f:
                    cur.execute(f.read())
                cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                logger.info(f"Applied migration {version}")
    logger.info("Database schema is up to date.")


def init_db():
    run_migrations()


def embedding_to_json(embedding):
    if embedding is None:
        return None
    if isinstance(embedding, list):
        return json.dumps([e.tolist() if isinstance(e, np.ndarray) else e for e in embedding])
    return json.dumps(embedding.tolist() if isinstance(embedding, np.ndarray) else embedding)


def json_to_embeddings(data):
    if not data:
        return []
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return []
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
        return [np.array(e, dtype=np.float32) for e in data]
    return [np.array(data, dtype=np.float32)]
