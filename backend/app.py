import logging
import os

import sentry_sdk
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sentry_sdk.integrations.flask import FlaskIntegration
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from backend.api.admin import admin_bp
from backend.api.media import media_bp
from backend.api.photographer import photographer_bp
from backend.api.user import user_bp
from backend.config import ROOT_DIR, Config
from backend.database.db import get_db_conn, init_db, init_pool
from backend.extensions import limiter
from backend.models.face_engine import get_engine
from backend.services import retention_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Create Flask App ---
STATIC_DIR = os.path.join(ROOT_DIR, 'static')
PRESENTATION_FILE = 'AI_Photo_Sharing_Presentation.pptx'
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Behind a reverse proxy every request appears to come from the proxy. Rate limits are
# per client, so read the real address from the header the trusted proxy sets.
if Config.TRUSTED_PROXY_HOPS > 0:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=Config.TRUSTED_PROXY_HOPS,
                            x_proto=Config.TRUSTED_PROXY_HOPS, x_host=Config.TRUSTED_PROXY_HOPS)

# Initialize Sentry if DSN provided
if os.environ.get('SENTRY_DSN'):
    try:
        sentry_sdk.init(
            dsn=os.environ.get('SENTRY_DSN'),
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.05,
            environment=os.environ.get('ENVIRONMENT', 'production')
        )
        logger.info('Sentry initialized')
    except Exception as e:
        logger.warning(f'Failed to initialize Sentry: {e}')

limiter.init_app(app)

# 🛡️ Strict CORS: only these sites may call the API from a browser.
CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})

_CONTENT_SECURITY_POLICY = '; '.join([
    "default-src 'self'",
    # No inline scripts and no third-party hosts. blob: is for the image-compression worker.
    "script-src 'self' blob:",
    "worker-src 'self' blob:",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    # Anti-hijack: only these sites may show the app inside an iframe.
    "frame-ancestors " + ' '.join(Config.FRAME_ANCESTORS),
])


@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = _CONTENT_SECURITY_POLICY
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Session ids and signed links travel in URLs; never leak them to other sites.
    response.headers['Referrer-Policy'] = 'no-referrer'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    if request.path.startswith('/api/') and 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.errorhandler(HTTPException)
def handle_http_error(e):
    """Keep the real status code (404, 413, 429, ...) and answer in JSON."""
    if e.code == 413:
        message = 'Upload is too large'
    elif e.code == 429:
        message = 'Too many requests. Please wait a moment and try again.'
    else:
        message = e.name
    response = jsonify({'error': message})
    for name, value in (e.get_headers() or []):
        if name.lower() in ('retry-after', 'allow', 'location') or name.lower().startswith('x-ratelimit'):
            response.headers[name] = value
    return response, e.code


@app.errorhandler(Exception)
def handle_exception(e):
    """Unexpected failures are logged in full; the client is told nothing about the internals."""
    logger.error(f"Server Error [{type(e).__name__}]: {e}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500


# --- Register Blueprints ---
app.register_blueprint(photographer_bp)
app.register_blueprint(user_bp)
app.register_blueprint(media_bp)
app.register_blueprint(admin_bp)


# --- Serve Frontend Static Pages ---
@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/photographer')
@app.route('/photographer/')
def photographer_page():
    return send_from_directory(os.path.join(STATIC_DIR, 'photographer'), 'index.html')


@app.route('/user')
@app.route('/user/')
def user_page():
    return send_from_directory(os.path.join(STATIC_DIR, 'user'), 'index.html')


@app.route('/api/download-presentation')
def download_presentation():
    if not os.path.exists(os.path.join(ROOT_DIR, PRESENTATION_FILE)):
        return jsonify({'error': 'Presentation not available'}), 404
    return send_from_directory(ROOT_DIR, PRESENTATION_FILE, as_attachment=True)


@app.route('/api/health')
def health():
    """Liveness: the web server is up. Cheap, and never touches the model or the database."""
    return jsonify({'status': 'healthy', 'face_engine': get_engine().state()})


@app.route('/api/ready')
def ready():
    """Readiness: the app can actually serve uploads and searches right now."""
    engine_ready = get_engine().is_ready()
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        database_ready = True
    except Exception as e:
        logger.warning(f"Readiness check: database unavailable: {e}")
        database_ready = False
    ready_now = engine_ready and database_ready
    return jsonify({
        'ready': ready_now,
        'face_engine': get_engine().state(),
        'database': 'ok' if database_ready else 'unavailable',
    }), 200 if ready_now else 503


# --- Initialization (Run on startup/import) ---
def startup_init():
    # Skip DB and heavy engine initialization during tests to allow fast unit tests
    if Config.TESTING:
        return

    try:
        logger.info("Initializing connection pool...")
        init_pool()
        logger.info("Applying database migrations...")
        init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    logger.info("Starting face recognition engine in background thread...")
    get_engine().load_in_background()

    if Config.RETENTION_AUTO_PURGE:
        logger.info(f"Automatic retention purge is on ({Config.RETENTION_DAYS} days).")
        retention_service.start_auto_purge()


startup_init()

if __name__ == '__main__':
    logger.info(f"Starting AI Photo Sharing on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
