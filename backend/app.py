import os
import sys
import logging
import threading

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from config import Config
from database.db import init_db, init_pool
from api.photographer import photographer_bp
from api.user import user_bp
from models.face_engine import get_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Create Flask App ---
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')

# 🛡️ SECURITY UPGRADE 1: Strict CORS
# Ab koi aur domain postman ya apne server se API nahi chura sakta
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://www.cwaya.me",
    "https://cwaya.me",
    "https://ai.cwaya.me"
]}})
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# 🛡️ SECURITY UPGRADE 2: Anti-Hijack IFrame (Content Security Policy)
# Yeh ensure karega ki sirf aapki website hi isko Iframe bana sake!
@app.after_request
def add_security_headers(response):
    # DHYAN DEIN: Jab aap final web par deploy karein toh apni domain add kar lein
    # allowed_domains = "'self' http://localhost:5173 http://localhost:5174"
        # Yeh line paste karein
    allowed_domains = "'self' https://huggingface.co https://*.hf.space http://localhost:5173 http://localhost:5174 https://*.vercel.app https://landing-page-redesign-beta.vercel.app"

    response.headers['Content-Security-Policy'] = f"frame-ancestors {allowed_domains};"
    return response

# 🛡️ SECURITY UPGRADE 3: Global Error Guard
# Server crash hone se pehle user ko polite message dega
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Server Error [{type(e).__name__}]: {e}", exc_info=True)
    return jsonify({
        "error": f"Internal server error: {type(e).__name__}",
        "detail": str(e)[:200]
    }), 503

# --- Register Blueprints ---
app.register_blueprint(photographer_bp)
app.register_blueprint(user_bp)

# --- Secure Image Proxy ---
# Users and Frontend will request /api/proxy/photos/123.jpg
# We will silently fetch it from HF so the token is never exposed!
import requests as req
from flask import Response, stream_with_context
@app.route('/api/proxy/<path:filepath>')
def proxy_huggingface(filepath):
    if not Config.HF_TOKEN or not Config.HF_DATASET_ID:
        return jsonify({"error": "Storage not configured"}), 500
        
    url = f"https://huggingface.co/datasets/{Config.HF_DATASET_ID}/resolve/main/{filepath}"
    headers = {"Authorization": f"Bearer {Config.HF_TOKEN}"}
    
    # Stream the image back to the client directly
    try:
        r = req.get(url, headers=headers, stream=True)
        r.raise_for_status()
        
        return Response(
            stream_with_context(r.iter_content(chunk_size=4096)),
            content_type=r.headers.get('content-type', 'image/jpeg')
        )
    except Exception as e:
        logger.error(f"Failed to fetch from HF proxy: {e}")
        return jsonify({"error": "Image not found"}), 404

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

# --- Health Check ---
@app.route('/api/health')
def health():
    engine = get_engine()
    return {
        'status': 'healthy',
        'face_engine': 'ready' if engine.is_ready() else 'loading'
    }

@app.route('/api/debug/db-test')
def db_test():
    db_url = os.environ.get('SUPABASE_DATABASE_URL')
    results = []
    
    # List of hosts to try
    hosts = [
        'db.tvqvkunrruqjgtwgjcye.supabase.co',
        'aws-0-ap-south-1.pooler.supabase.com',
    ]
    
    import socket
    for host in hosts:
        res = {'host': host}
        try:
            res['ipv4'] = socket.gethostbyname(host)
        except Exception as e:
            res['ipv4_error'] = str(e)
        try:
            res['ipv6'] = socket.getaddrinfo(host, None, socket.AF_INET6)[0][4][0]
        except Exception as e:
            res['ipv6_error'] = str(e)
        results.append(res)
        
    return jsonify({
        'env_db_url_masked': db_url.split('@')[-1] if db_url else None,
        'dns_results': results
    })

# --- Initialization (Run on startup/import) ---
def startup_init():
    try:
        logger.info("Initializing connection pool...")
        init_pool()
        logger.info("Connection pool ready.")
    except Exception as e:
        logger.error(f"Connection pool init failed: {e}")

    try:
        logger.info("Initializing database tables...")
        init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    logger.info("Starting face recognition engine in background thread...")
    def _load_engine_bg():
        try:
            get_engine(Config.INSIGHTFACE_DIR)
            logger.info("Face recognition engine is ready!")
        except Exception as e:
            logger.error(f"Face engine failed to load: {e}")

    bg_thread = threading.Thread(target=_load_engine_bg, daemon=True)
    bg_thread.start()

# Execute startup
startup_init()

if __name__ == '__main__':
    logger.info(f"Starting AI Photo Sharing on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)


# import os
# import sys
# import logging
# import threading

# # Add backend dir to path
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from flask import Flask, send_from_directory
# from flask_cors import CORS
# from dotenv import load_dotenv

# # Load environment variables from .env
# load_dotenv()

# from config import Config
# from database.db import init_db, init_pool
# from api.photographer import photographer_bp
# from api.user import user_bp
# from models.face_engine import get_engine

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# # --- Create Flask App ---
# STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
# app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
# CORS(app)
# app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# # --- Register Blueprints ---
# app.register_blueprint(photographer_bp)
# app.register_blueprint(user_bp)

# # --- Serve Frontend Static Pages ---
# @app.route('/')
# def index():
#     return send_from_directory(STATIC_DIR, 'index.html')

# @app.route('/photographer')
# @app.route('/photographer/')
# def photographer_page():
#     return send_from_directory(os.path.join(STATIC_DIR, 'photographer'), 'index.html')

# @app.route('/user')
# @app.route('/user/')
# def user_page():
#     return send_from_directory(os.path.join(STATIC_DIR, 'user'), 'index.html')

# # --- Health Check ---
# @app.route('/api/health')
# def health():
#     engine = get_engine()
#     return {
#         'status': 'healthy',
#         'face_engine': 'ready' if engine.is_ready() else 'loading'
#     }

# # --- Initialization (Run on startup/import) ---
# def startup_init():
#     # Initialize connection pool first
#     try:
#         logger.info("Initializing connection pool...")
#         init_pool()
#         logger.info("Connection pool ready.")
#     except Exception as e:
#         logger.error(f"Connection pool init failed: {e}")

#     # Initialize database tables (Supabase/PostgreSQL)
#     try:
#         logger.info("Initializing database tables...")
#         init_db()
#     except Exception as e:
#         logger.error(f"Database initialization failed: {e}")

#     # Load face engine in background so server starts immediately
#     logger.info("Starting face recognition engine in background thread...")
#     def _load_engine_bg():
#         try:
#             get_engine(Config.INSIGHTFACE_DIR)
#             logger.info("Face recognition engine is ready!")
#         except Exception as e:
#             logger.error(f"Face engine failed to load: {e}")

#     bg_thread = threading.Thread(target=_load_engine_bg, daemon=True)
#     bg_thread.start()

# # Execute startup
# startup_init()

# # --- Main ---
# if __name__ == '__main__':
#     logger.info(f"Starting AI Photo Sharing on http://{Config.HOST}:{Config.PORT}")
#     app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
