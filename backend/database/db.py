import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
import os
import logging
import threading
from contextlib import contextmanager
from config import Config
import numpy as np
import json

logger = logging.getLogger(__name__)

# --- Connection Pool Logic ---
_pool = None
_pool_lock = threading.Lock()

def init_pool(minconn=1, maxconn=20):
    global _pool
    db_url = Config.DB_URL
    if not db_url:
        logger.error("SUPABASE_DATABASE_URL is not set!")
        raise RuntimeError("Database URL missing.")

    # List of connection strings to try
    # 1. User defined (Current)
    # 2. Fallback to 6543 if was 5432
    # 3. Fallback to direct host if was pooler
    # 4. Fallback to pooler if was direct
    urls_to_try = [db_url]
    
    # Extract components
    import re
    match = re.match(r"postgresql://(?P<user>[^:]+):(?P<pass>[^@]+)@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<db>.+)", db_url)
    if match:
        d = match.groupdict()
        user, password, host, port, db = d['user'], d['pass'], d['host'], d['port'] or '5432', d['db']
        
        # If using direct host, try pooler host
        if ".supabase.co" in host and "pooler" not in host:
            # db.tvqvkunrruqjgtwgjcye.supabase.co -> tvqvkunrruqjgtwgjcye
            host_parts = host.split('.')
            if len(host_parts) >= 3:
                project_id = host_parts[-3]
                pooler_host = f"aws-0-ap-south-1.pooler.supabase.com"
                # Add pooler URL with prefixed username
                urls_to_try.append(f"postgresql://postgres.{project_id}:{password}@{pooler_host}:6543/{db}?sslmode=require")
                urls_to_try.append(f"postgresql://postgres.{project_id}:{password}@{pooler_host}:5432/{db}?sslmode=require")
        
        # If using port 5432, try 6543
        if port == '5432':
            urls_to_try.append(db_url.replace(":5432/", ":6543/"))

    working_url = None
    for url in urls_to_try:
        masked = url.split('@')[-1]
        logger.info(f"Trying database connection: {masked}")
        try:
            # Parse URL and use keywords to avoid encoding issues
            import urllib.parse as urlparse
            import socket
            result = urlparse.urlparse(url)
            username = result.username
            password = urlparse.unquote(result.password) if result.password else None
            database = result.path[1:]
            hostname = result.hostname
            port = result.port or 5432
            
            # Resolve to IPv4 to bypass Azure IPv6 issues
            hostaddr = None
            try:
                # Force IPv4 resolution
                hostaddr = socket.gethostbyname(hostname)
                logger.info(f"Resolved {hostname} to IPv4: {hostaddr}")
            except Exception as dns_err:
                logger.warning(f"DNS resolution failed for {hostname}: {dns_err}")

            conn = psycopg2.connect(
                database=database,
                user=username,
                password=password,
                host=hostname,
                hostaddr=hostaddr, # This is the magic fix for Azure IPv6 issues
                port=port,
                connect_timeout=5,
                sslmode='require' if 'sslmode=require' in url or 'pooler' in hostname else 'prefer',
                gssencmode='disable',
                target_session_attrs='read-write'
            )
            conn.close()
            logger.info("Successfully connected to database!")
            working_url = url
            break
        except Exception as e:
            logger.warning(f"Connection failed for {masked}: {e}")

    if not working_url:
        logger.error("All database connection attempts failed.")
        raise RuntimeError("Could not connect to any database endpoint.")

    try:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(minconn, maxconn, working_url)
                logger.info("Database Connection Pool Initialized.")
    except Exception as e:
        logger.error(f"Failed to create connection pool: {e}")
        raise

@contextmanager
def get_db_conn():
    """Context manager to handle DB connections safely."""
    global _pool
    if _pool is None:
        init_pool()
    
    conn = _pool.getconn()
    try:
        # Check if connection is still alive
        with conn.cursor() as tmp_cur:
            tmp_cur.execute("SELECT 1")
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        _pool.putconn(conn)

# --- Compatibility Wrappers (For older code) ---
def get_conn():
    if _pool is None: init_pool()
    return _pool.getconn()

def release_conn(conn):
    if conn and _pool:
        _pool.putconn(conn)

# --- Database Initialization ---
def init_db():
    """Create tables if they don't exist."""
    with get_db_conn() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photographers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    total_photos INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS photos (
                    id TEXT PRIMARY KEY,
                    photographer_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT NOT NULL,
                    original_filename TEXT,
                    face_count INTEGER DEFAULT 0,
                    embeddings JSONB,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (photographer_id) REFERENCES photographers(id)
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    photographer_id TEXT NOT NULL,
                    selfie_path TEXT,
                    matched_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (photographer_id) REFERENCES photographers(id)
                );

                CREATE TABLE IF NOT EXISTS download_logs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    photo_id TEXT NOT NULL,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES user_sessions(id),
                    FOREIGN KEY (photo_id) REFERENCES photos(id)
                );
            """)
            conn.commit()
            cursor.close()
            logger.info("Database tables verified.")
        except Exception as e:
            logger.error(f"init_db failed: {e}")
            raise

# --- Utility Functions ---
def embedding_to_json(embedding):
    if embedding is None: return None
    if isinstance(embedding, list):
        return json.dumps([e.tolist() if isinstance(e, np.ndarray) else e for e in embedding])
    return json.dumps(embedding.tolist() if isinstance(embedding, np.ndarray) else embedding)

def json_to_embeddings(data):
    if not data: return []
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return []
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
        return [np.array(e, dtype=np.float32) for e in data]
    return [np.array(data, dtype=np.float32)]

# import psycopg2
# from psycopg2.pool import ThreadedConnectionPool
# from psycopg2.extras import RealDictCursor
# import os
# import sys
# import logging
# import threading

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import Config
# import numpy as np
# import json

# logger = logging.getLogger(__name__)

# # --- Connection Pool ---
# _pool = None
# _pool_lock = threading.Lock()


# def init_pool(minconn=1, maxconn=15):
#     """Initialize the connection pool with automatic port fallback."""
#     global _pool
#     db_url = Config.DB_URL

#     if not db_url:
#         logger.error("SUPABASE_DATABASE_URL is not set!")
#         raise RuntimeError("SUPABASE_DATABASE_URL is not configured.")

#     # Try connection to the configured URL
#     logger.info("Connecting to Supabase...")
    
#     working_url = None
#     # If the URL is already on 6543, try it directly
#     # If on 5432, try it but prepare for fallback
#     try:
#         conn = psycopg2.connect(db_url, connect_timeout=10)
#         conn.close()
#         logger.info("Database reachable.")
#         working_url = db_url
#     except Exception as e:
#         logger.warning(f"Connection to {db_url} failed: {e}")
        
#         # Automatic fallback: If on 5432, try 6543 (Transaction Pooler)
#         if ":5432/" in db_url:
#             logger.info("Attempting fallback to Supabase Transaction Pooler (Port 6543)...")
#             fallback_url = db_url.replace(":5432/", ":6543/")
#             try:
#                 conn = psycopg2.connect(fallback_url, connect_timeout=10)
#                 conn.close()
#                 logger.info("Reachable on port 6543.")
#                 working_url = fallback_url
#             except Exception as e2:
#                 logger.error(f"Fallback also failed: {e2}")
        
#     if not working_url:
#         logger.error("FATAL: Cannot reach Supabase on any port.")
#         logger.error("TIP: Your Supabase host might be IPv6-only. Ensure you are using the POOLER URI (aws-0-[REGION].pooler.supabase.com).")
#         raise RuntimeError("Database connection failed. Please check your SUPABASE_DATABASE_URL in .env")

#     try:
#         # _pool = SimpleConnectionPool(minconn, maxconn, working_url)
#         _pool = ThreadedConnectionPool(minconn, maxconn, working_url)
#         logger.info(f"Connection pool created (min={minconn}, max={maxconn})")
#     except Exception as e:
#         logger.error(f"Failed to create connection pool: {e}")
#         raise
# @contextmanager
# def get_db_conn():
#     """Context manager for database connections."""
#     global _pool
#     if _pool is None:
#         init_pool()
    
#     conn = _pool.getconn()
#     try:
#         # Connection check karne ke liye (taki dead connection na mile)
#         with conn.cursor() as tmp_cur:
#             tmp_cur.execute("SELECT 1")
#         yield conn
#     except Exception as e:
#         logger.error(f"Database connection error: {e}")
#         raise
#     finally:
#         _pool.putconn(conn)

# def get_conn():
#     """Get a connection from the pool. Falls back to direct connect if pool not ready."""
#     global _pool
#     with _pool_lock:
#         if _pool is None:
#             try:
#                 init_pool()
#             except Exception:
#                 # Last resort: direct connection
#                 logger.warning("Pool init failed, using direct connection.")
#                 return psycopg2.connect(Config.DB_URL, connect_timeout=10)

#     try:
#         conn = _pool.getconn()
#         # Test if connection is still alive
#         try:
#             conn.cursor().execute("SELECT 1")
#         except Exception:
#             # Connection is stale, close and get a new one
#             try:
#                 _pool.putconn(conn, close=True)
#             except Exception:
#                 pass
#             conn = _pool.getconn()
#         return conn
#     except Exception as e:
#         logger.error(f"Pool getconn failed: {e}")
#         # Fallback to direct connection
#         return psycopg2.connect(Config.DB_URL, connect_timeout=10)


# def release_conn(conn):
#     """Return a connection back to the pool."""
#     global _pool
#     if conn is None:
#         return
#     try:
#         if _pool is not None:
#             _pool.putconn(conn)
#         else:
#             conn.close()
#     except Exception:
#         try:
#             conn.close()
#         except Exception:
#             pass


# def init_db():
#     """Initialize PostgreSQL tables in Supabase."""
#     conn = get_conn()
#     try:
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS photographers (
#                 id TEXT PRIMARY KEY,
#                 name TEXT NOT NULL,
#                 email TEXT NOT NULL,
#                 event_name TEXT NOT NULL,
#                 code TEXT UNIQUE NOT NULL,
#                 total_photos INTEGER DEFAULT 0,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             );

#             CREATE TABLE IF NOT EXISTS photos (
#                 id TEXT PRIMARY KEY,
#                 photographer_id TEXT NOT NULL,
#                 file_path TEXT NOT NULL,
#                 thumbnail_path TEXT NOT NULL,
#                 original_filename TEXT,
#                 face_count INTEGER DEFAULT 0,
#                 embeddings JSONB,
#                 uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (photographer_id) REFERENCES photographers(id)
#             );

#             CREATE TABLE IF NOT EXISTS user_sessions (
#                 id TEXT PRIMARY KEY,
#                 photographer_id TEXT NOT NULL,
#                 selfie_path TEXT,
#                 matched_count INTEGER DEFAULT 0,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (photographer_id) REFERENCES photographers(id)
#             );

#             CREATE TABLE IF NOT EXISTS download_logs (
#                 id TEXT PRIMARY KEY,
#                 session_id TEXT NOT NULL,
#                 photo_id TEXT NOT NULL,
#                 downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (session_id) REFERENCES user_sessions(id),
#                 FOREIGN KEY (photo_id) REFERENCES photos(id)
#             );
#         """)
#         conn.commit()
#         cursor.close()
#         logger.info("Database tables initialized successfully.")
#     except Exception as e:
#         logger.error(f"init_db failed: {e}")
#         raise
#     finally:
#         release_conn(conn)


# def embedding_to_json(embedding):
#     """Convert numpy embedding to JSON string for storage."""
#     if embedding is None:
#         return None
#     if isinstance(embedding, list):
#         return json.dumps([e.tolist() if isinstance(e, np.ndarray) else e for e in embedding])
#     return json.dumps(embedding.tolist() if isinstance(embedding, np.ndarray) else embedding)


# def json_to_embeddings(data):
#     """Convert JSON data (string or list) back to list of numpy arrays."""
#     if not data:
#         return []

#     # If data is a string (JSONB not automatically parsed), parse it
#     if isinstance(data, str):
#         try:
#             data = json.loads(data)
#         except Exception:
#             return []

#     if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
#         return [np.array(e, dtype=np.float32) for e in data]
#     return [np.array(data, dtype=np.float32)]
