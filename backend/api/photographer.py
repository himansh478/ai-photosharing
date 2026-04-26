from flask import Blueprint, request, jsonify
from datetime import datetime
import os
import sys
import uuid
import threading
import logging
import queue
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from database.db import get_db_conn, embedding_to_json
from models.face_engine import get_engine
from services.upload_service import UploadService
from psycopg2.extras import RealDictCursor

photographer_bp = Blueprint('photographer', __name__)
logger = logging.getLogger(__name__)
upload_service = UploadService()

# Track async batch processing jobs
batch_jobs = {}  # job_id -> status dict

# 🛡️ PRODUCTION GUARD: Limit total threads across the whole app
# Hum 2vCPUs par ek time par 1 AI aur 5 Upload process hi allow karenge
AI_SEMAPHORE = threading.Semaphore(1) 
UPLOAD_EXECUTOR = ThreadPoolExecutor(max_workers=5)


@photographer_bp.route('/api/photographer/register', methods=['POST'])
def register():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    event_name = data.get('event_name', '').strip()

    if not all([name, email, event_name]):
        return jsonify({'error': 'name, email, event_name are required'}), 400

    pid = str(uuid.uuid4())
    code = f"EVT-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"

    try:
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO photographers (id, name, email, event_name, code) VALUES (%s,%s,%s,%s,%s)",
                (pid, name, email, event_name, code)
            )
            conn.commit()
            cursor.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'photographer_id': pid,
        'code': code,
        'event_name': event_name,
        'status': 'ready_for_upload'
    }), 201


@photographer_bp.route('/api/photographer/upload-batch', methods=['POST'])
def upload_batch():
    code = request.form.get('code', '').strip()
    files = request.files.getlist('photos')

    if not code:
        return jsonify({'error': 'code is required'}), 400
    if not files:
        return jsonify({'error': 'No photos provided'}), 400
    if len(files) > Config.MAX_PHOTOS_PER_BATCH:
        return jsonify({'error': f'Maximum {Config.MAX_PHOTOS_PER_BATCH} photos allowed per batch.'}), 400

    try:
        with get_db_conn() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM photographers WHERE code=%s", (code,))
            p = cursor.fetchone()
            cursor.close()
    except Exception as e:
        return jsonify({'error': 'Database connect error'}), 500

    if not p:
        return jsonify({'error': 'Invalid photographer code'}), 401

    photographer_id = p['id']

    # 1. Save all files to TEMP first for processing
    to_process = []
    for f in files:
        if f and f.filename:
            temp_path = upload_service.save_to_temp(f)
            to_process.append({'temp_path': temp_path, 'filename': f.filename})

    # 2. Start async processing and cloud upload
    job_id = str(uuid.uuid4())
    batch_jobs[job_id] = {
        'status': 'processing',
        'total': len(to_process),
        'processed': 0,
        'uploaded': 0,
        'skipped': 0
    }

    t = threading.Thread(target=_process_batch, args=(job_id, photographer_id, to_process))
    t.daemon = True
    t.start()

    return jsonify({
        'job_id': job_id,
        'files_received': len(to_process),
        'message': 'Batch upload and processing started.'
    }), 202


def _process_batch(job_id, photographer_id, items):
    # 🔒 ANTI-CRASH LOCK: Wait if another batch is already being AI-scanned
    with AI_SEMAPHORE:
        engine = get_engine(Config.INSIGHTFACE_DIR)
        job = batch_jobs[job_id]
        
        for item in items:
            try:
                # 1. AI Scanning (CPU heavy)
                embeddings = engine.detect_and_embed(item['temp_path'])
                
                # 2. Upload (I/O heavy - send to Executor)
                UPLOAD_EXECUTOR.submit(_finish_upload, item, embeddings, photographer_id, job)
                
            except Exception as e:
                logger.error(f"Batch error: {e}")
                job['skipped'] += 1
                job['processed'] += 1
                upload_service.cleanup_temp(item['temp_path']) # cleanup on AI error
        
        job['status'] = 'completed'


def _finish_upload(item, embeddings, photographer_id, job):
    # This runs in background UPLOAD_EXECUTOR
    temp_path = item['temp_path']
    filename = item['filename']
    face_count = len(embeddings)

    try:
        # Upload to Cloud
        cloud_url = upload_service.save_photo(temp_path, filename)
        thumb_url = upload_service.generate_thumbnail(temp_path)

        # Save to DB
        photo_id = str(uuid.uuid4())
        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO photos (id, photographer_id, file_path, thumbnail_path, original_filename, face_count, embeddings)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (photo_id, photographer_id, cloud_url, thumb_url, filename, face_count, embedding_to_json(embeddings))
            )
            cursor.execute(
                "UPDATE photographers SET total_photos = total_photos + 1 WHERE id = %s",
                (photographer_id,)
            )
            conn.commit()
            cursor.close()

        if face_count > 0:
            job['uploaded'] += 1
        else:
            job['skipped'] += 1

    except Exception as e:
        logger.error(f"Consumer error for {filename}: {e}")
        job['skipped'] += 1
    finally:
        upload_service.cleanup_temp(temp_path)
        job['processed'] += 1


@photographer_bp.route('/api/photographer/batch-status/<job_id>', methods=['GET'])
def batch_status(job_id):
    job = batch_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@photographer_bp.route('/api/photographer/stats', methods=['GET'])
def stats():
    code = request.args.get('code', '').strip()
    try:
        with get_db_conn() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM photographers WHERE code=%s", (code,))
            p = cursor.fetchone()
            if not p:
                cursor.close()
                return jsonify({'error': 'Invalid code'}), 401

            pid = p['id']

            cursor.execute("SELECT COUNT(*) FROM photos WHERE photographer_id=%s AND face_count > 0", (pid,))
            faces_detected = cursor.fetchone()['count']

            cursor.execute("""
                SELECT COUNT(*) FROM download_logs dl 
                JOIN user_sessions us ON dl.session_id=us.id 
                WHERE us.photographer_id=%s
            """, (pid,))
            total_downloads = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE photographer_id=%s", (pid,))
            total_users = cursor.fetchone()['count']

            cursor.close()
    except Exception as e:
         return jsonify({'error': 'Database error'}), 500

    return jsonify({
        'code': code,
        'event_name': p['event_name'],
        'photographer_name': p['name'],
        'total_photos': p['total_photos'],
        'faces_detected': faces_detected,
        'total_users': total_users,
        'total_downloads': total_downloads
    })



# from flask import Blueprint, request, jsonify
# from datetime import datetime
# import os
# import sys
# import uuid
# import threading
# import logging
# import queue
# from concurrent.futures import ThreadPoolExecutor

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import Config
# from database.db import get_conn, release_conn, embedding_to_json
# from models.face_engine import get_engine
# from services.upload_service import UploadService
# from psycopg2.extras import RealDictCursor

# photographer_bp = Blueprint('photographer', __name__)
# logger = logging.getLogger(__name__)
# upload_service = UploadService()

# # Track async batch processing jobs
# batch_jobs = {}  # job_id -> status dict


# @photographer_bp.route('/api/photographer/register', methods=['POST'])
# def register():
#     data = request.json or {}
#     name = data.get('name', '').strip()
#     email = data.get('email', '').strip()
#     event_name = data.get('event_name', '').strip()

#     if not all([name, email, event_name]):
#         return jsonify({'error': 'name, email, event_name are required'}), 400

#     pid = str(uuid.uuid4())
#     code = f"EVT-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"

#     conn = get_conn()
#     try:
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO photographers (id, name, email, event_name, code) VALUES (%s,%s,%s,%s,%s)",
#             (pid, name, email, event_name, code)
#         )
#         conn.commit()
#         cursor.close()
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#     finally:
#         release_conn(conn)

#     return jsonify({
#         'photographer_id': pid,
#         'code': code,
#         'event_name': event_name,
#         'status': 'ready_for_upload'
#     }), 201


# @photographer_bp.route('/api/photographer/upload-batch', methods=['POST'])
# def upload_batch():
#     code = request.form.get('code', '').strip()
#     files = request.files.getlist('photos')

#     if not code:
#         return jsonify({'error': 'code is required'}), 400
#     if not files:
#         return jsonify({'error': 'No photos provided'}), 400
#     if len(files) > Config.MAX_PHOTOS_PER_BATCH:
#         return jsonify({'error': f'Maximum {Config.MAX_PHOTOS_PER_BATCH} photos allowed per batch.'}), 400

#     conn = get_conn()
#     try:
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         cursor.execute("SELECT * FROM photographers WHERE code=%s", (code,))
#         p = cursor.fetchone()
#         cursor.close()
#     finally:
#         release_conn(conn)

#     if not p:
#         return jsonify({'error': 'Invalid photographer code'}), 401

#     photographer_id = p['id']

#     # 1. Save all files to TEMP first for processing
#     to_process = []
#     for f in files:
#         if f and f.filename:
#             temp_path = upload_service.save_to_temp(f)
#             to_process.append({'temp_path': temp_path, 'filename': f.filename})

#     # 2. Start async processing and cloud upload
#     job_id = str(uuid.uuid4())
#     batch_jobs[job_id] = {
#         'status': 'processing',
#         'total': len(to_process),
#         'processed': 0,
#         'uploaded': 0,
#         'skipped': 0
#     }

#     t = threading.Thread(target=_process_batch, args=(job_id, photographer_id, to_process))
#     t.daemon = True
#     t.start()

#     return jsonify({
#         'job_id': job_id,
#         'files_received': len(to_process),
#         'message': 'Batch upload and processing started.'
#     }), 202


# def _ai_producer(items, engine, upload_queue, job):
#     """Wait-free AI face detection: only focuses on CPU-intensive work."""
#     for item in items:
#         try:
#             temp_path = item['temp_path']
#             filename = item['filename']

#             # A. Detect faces (CPU-bound)
#             embeddings = engine.detect_and_embed(temp_path)
#             face_count = len(embeddings)

#             # Pass data forward to the uploaders
#             upload_queue.put({
#                 'temp_path': temp_path,
#                 'filename': filename,
#                 'embeddings': embeddings,
#                 'face_count': face_count
#             })
#         except Exception as e:
#             logger.error(f"Producer error for {item.get('filename')}: {e}")
#             job['skipped'] += 1
#             job['processed'] += 1

#     # Signal that AI work is done
#     upload_queue.put(None)

# def _upload_consumer(upload_queue, photographer_id, job):
#     """Network-bound upload: only focuses on I/O-intensive work."""
#     while True:
#         data = upload_queue.get()
#         if data is None:
#             upload_queue.put(None)  # Pass the signal to other workers
#             break

#         temp_path = data['temp_path']
#         filename = data['filename']
#         embeddings = data['embeddings']
#         face_count = data['face_count']
#         conn = None

#         try:
#             # B. Upload to ImgBB (I/O-bound)
#             cloud_url = upload_service.save_photo(temp_path, filename)
#             thumb_url = upload_service.generate_thumbnail(temp_path)

#             # C. Save to Supabase (Postgres)
#             photo_id = str(uuid.uuid4())
#             conn = get_conn()
#             cursor = conn.cursor()
#             cursor.execute(
#                 """INSERT INTO photos (id, photographer_id, file_path, thumbnail_path, original_filename, face_count, embeddings)
#                    VALUES (%s,%s,%s,%s,%s,%s,%s)""",
#                 (photo_id, photographer_id, cloud_url, thumb_url, filename, face_count, embedding_to_json(embeddings))
#             )
#             cursor.execute(
#                 "UPDATE photographers SET total_photos = total_photos + 1 WHERE id = %s",
#                 (photographer_id,)
#             )
#             conn.commit()
#             cursor.close()

#             if face_count > 0:
#                 job['uploaded'] += 1
#             else:
#                 job['skipped'] += 1

#         except Exception as e:
#             logger.error(f"Consumer error for {filename}: {e}")
#             job['skipped'] += 1
#         finally:
#             release_conn(conn)
#             # D. Cleanup local temp file
#             upload_service.cleanup_temp(temp_path)
#             job['processed'] += 1

#         upload_queue.task_done()

# def _process_batch(job_id, photographer_id, items):
#     engine = get_engine(Config.INSIGHTFACE_DIR)
#     job = batch_jobs[job_id]
#     upload_queue = queue.Queue(maxsize=20)  # Buffer to prevent memory bloating

#     with ThreadPoolExecutor(max_workers=11) as executor:
#         # One producer thread for AI
#         executor.submit(_ai_producer, items, engine, upload_queue, job)

#         # 10 consumer threads for simultaneous cloud uploads
#         for _ in range(10):
#             executor.submit(_upload_consumer, upload_queue, photographer_id, job)

#     job['status'] = 'completed'


# @photographer_bp.route('/api/photographer/batch-status/<job_id>', methods=['GET'])
# def batch_status(job_id):
#     job = batch_jobs.get(job_id)
#     if not job:
#         return jsonify({'error': 'Job not found'}), 404
#     return jsonify(job)


# @photographer_bp.route('/api/photographer/stats', methods=['GET'])
# def stats():
#     code = request.args.get('code', '').strip()
#     conn = get_conn()
#     try:
#         cursor = conn.cursor(cursor_factory=RealDictCursor)

#         cursor.execute("SELECT * FROM photographers WHERE code=%s", (code,))
#         p = cursor.fetchone()
#         if not p:
#             cursor.close()
#             return jsonify({'error': 'Invalid code'}), 401

#         pid = p['id']

#         cursor.execute("SELECT COUNT(*) FROM photos WHERE photographer_id=%s AND face_count > 0", (pid,))
#         faces_detected = cursor.fetchone()['count']

#         cursor.execute("""
#             SELECT COUNT(*) FROM download_logs dl 
#             JOIN user_sessions us ON dl.session_id=us.id 
#             WHERE us.photographer_id=%s
#         """, (pid,))
#         total_downloads = cursor.fetchone()['count']

#         cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE photographer_id=%s", (pid,))
#         total_users = cursor.fetchone()['count']

#         cursor.close()
#     finally:
#         release_conn(conn)

#     return jsonify({
#         'code': code,
#         'event_name': p['event_name'],
#         'photographer_name': p['name'],
#         'total_photos': p['total_photos'],
#         'faces_detected': faces_detected,
#         'total_users': total_users,
#         'total_downloads': total_downloads
#     })
