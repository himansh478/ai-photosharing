import logging
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, jsonify, request

from backend.config import Config
from backend.database import repo
from backend.database.db import embedding_to_json
from backend.extensions import limiter
from backend.models.face_engine import EngineNotReady, ImageUnreadable, get_engine
from backend.security import (CONTRIBUTOR_KEY_PREFIX, HOST_KEY_PREFIX, hash_key, new_guest_code,
                              new_key, request_event_key, role_for_key)
from backend.services import storage_service
from backend.services.jobs import registry
from backend.services.retention_service import delete_event_data
from backend.validation import InvalidImage, file_sha256, strip_location, validate_image

photographer_bp = Blueprint('photographer', __name__)
logger = logging.getLogger(__name__)

# 🛡️ PRODUCTION GUARD: Limit total threads across the whole app
# Hum 2vCPUs par ek time par 1 AI aur 5 Upload process hi allow karenge
AI_SEMAPHORE = threading.Semaphore(1)
UPLOAD_EXECUTOR = ThreadPoolExecutor(max_workers=5)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_MAX_FIELD_LENGTH = 120


def _authorised_event(code, allowed_roles):
    """Look up the event for `code` and check the caller's key.

    Returns (event, role, None) on success or (None, None, error_response).
    """
    if not code:
        return None, None, (jsonify({'error': 'code is required'}), 400)
    event = repo.get_event_by_code(code)
    if not event:
        return None, None, (jsonify({'error': 'Invalid event code'}), 401)
    if not event.get('host_key_hash'):
        # Events created before upload keys existed have none until an admin issues them.
        return None, None, (jsonify({
            'error': 'This event has no upload key yet. Ask the administrator to issue one.'
        }), 403)
    role = role_for_key(event, request_event_key())
    if role not in allowed_roles:
        return None, None, (jsonify({'error': 'A valid upload key is required for this event'}), 403)
    return event, role, None


@photographer_bp.route('/api/photographer/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip()
    event_name = str(data.get('event_name', '')).strip()
    event_type = str(data.get('event_type', 'other')).strip().lower() or 'other'

    if not all([name, email, event_name]):
        return jsonify({'error': 'name, email, event_name are required'}), 400
    if max(len(name), len(email), len(event_name)) > _MAX_FIELD_LENGTH:
        return jsonify({'error': f'Fields must be at most {_MAX_FIELD_LENGTH} characters'}), 400
    if not _EMAIL_RE.match(email):
        return jsonify({'error': 'Please enter a valid email address'}), 400
    if event_type not in Config.EVENT_TYPES:
        return jsonify({'error': 'Unknown event type'}), 400

    pid = str(uuid.uuid4())
    code = new_guest_code()
    host_key = new_key(HOST_KEY_PREFIX)
    contributor_key = new_key(CONTRIBUTOR_KEY_PREFIX)

    try:
        repo.create_event(pid, name, email, event_name, event_type, code,
                          hash_key(host_key), hash_key(contributor_key))
    except Exception as e:
        logger.error(f"Event registration failed: {e}")
        return jsonify({'error': 'Could not create the event. Please try again.'}), 500

    # The keys are returned once and only their hashes are kept, so they cannot be shown again.
    return jsonify({
        'code': code,
        'event_name': event_name,
        'event_type': event_type,
        'host_key': host_key,
        'contributor_key': contributor_key,
        'status': 'ready_for_upload'
    }), 201


@photographer_bp.route('/api/photographer/access', methods=['GET'])
@limiter.limit("30 per minute")
def access():
    """Tell the caller which role their key has for an event."""
    code = request.args.get('code', '').strip().upper()
    event, role, error = _authorised_event(code, ('host', 'contributor'))
    if error:
        return error
    return jsonify({'role': role, 'code': event['code'], 'event_name': event['event_name']})


@photographer_bp.route('/api/photographer/upload-batch', methods=['POST'])
@limiter.limit("120 per minute")
def upload_batch():
    code = request.form.get('code', '').strip().upper()
    files = [f for f in request.files.getlist('photos') if f and f.filename]

    event, _role, error = _authorised_event(code, ('host', 'contributor'))
    if error:
        return error
    if not files:
        return jsonify({'error': 'No photos provided'}), 400
    if len(files) > Config.MAX_PHOTOS_PER_BATCH:
        return jsonify({'error': f'Maximum {Config.MAX_PHOTOS_PER_BATCH} photos allowed per batch.'}), 400

    # Accepting photos while the model is unavailable would process none of them.
    engine = get_engine()
    if not engine.is_ready():
        engine.load_in_background()
        response = jsonify({'error': 'The face recognition engine is starting. Please retry shortly.',
                            'face_engine': engine.state()})
        response.headers['Retry-After'] = '20'
        return response, 503

    # A large upload arrives as several requests that all report into one job.
    job_id = request.form.get('job_id', '').strip()
    if job_id:
        job = registry.get(job_id)
        if not job or job.event_id != event['id']:
            return jsonify({'error': 'Job not found'}), 404
    else:
        job = registry.create(event['id'])

    # 1. Save all files to TEMP first for processing
    to_process = [{'temp_path': storage_service.save_to_temp(f), 'filename': f.filename} for f in files]

    # 2. Start async processing and cloud upload
    job.add_batch(len(to_process))
    t = threading.Thread(target=_process_batch, args=(job, event['id'], to_process))
    t.daemon = True
    t.start()

    return jsonify({
        'job_id': job.id,
        'files_received': len(to_process),
        'message': 'Batch upload and processing started.'
    }), 202


def _process_batch(job, event_id, items):
    futures = []
    try:
        # 🔒 ANTI-CRASH LOCK: Wait if another batch is already being AI-scanned
        with AI_SEMAPHORE:
            engine = get_engine()
            for item in items:
                temp_path, filename = item['temp_path'], item['filename']
                try:
                    validate_image(temp_path, Config.MAX_PHOTO_BYTES)
                    sha256 = file_sha256(temp_path)
                    if repo.photo_hash_exists(event_id, sha256):
                        job.record('duplicate')
                        storage_service.cleanup_temp(temp_path)
                        continue
                    strip_location(temp_path)

                    # 1. AI Scanning (CPU heavy)
                    embeddings = engine.detect_and_embed(temp_path)

                    # 2. Upload (I/O heavy - send to Executor)
                    futures.append(UPLOAD_EXECUTOR.submit(
                        _finish_upload, job, event_id, item, embeddings, sha256, engine.model_version))
                    continue
                except InvalidImage as e:
                    job.record('failed', filename, str(e))
                except EngineNotReady:
                    job.record('failed', filename, 'Face recognition engine unavailable')
                except ImageUnreadable:
                    job.record('failed', filename, 'Could not read the image')
                except Exception as e:
                    logger.error(f"Batch error for {filename}: {e}", exc_info=True)
                    job.record('failed', filename, 'Processing error')
                storage_service.cleanup_temp(temp_path)

        # Wait for ALL uploads to finish before marking complete
        for f in futures:
            f.result()
    finally:
        job.close_batch()


def _finish_upload(job, event_id, item, embeddings, sha256, model_version):
    # This runs in background UPLOAD_EXECUTOR
    temp_path = item['temp_path']
    filename = item['filename']
    face_count = len(embeddings)
    stored_keys = []

    try:
        photo_key = storage_service.store_photo(temp_path, filename)
        stored_keys.append(photo_key)
        try:
            thumb_key = storage_service.store_thumbnail(temp_path)
            stored_keys.append(thumb_key)
        except Exception as e:
            logger.error(f"Thumbnail generation/upload failed for {filename}: {e}")
            thumb_key = ''

        inserted = repo.insert_photo(
            str(uuid.uuid4()), event_id, photo_key, thumb_key, filename, face_count,
            embedding_to_json(embeddings) if face_count else None, sha256, model_version)
        if not inserted:
            # The same file arrived twice at once; keep the first copy only.
            storage_service.get_storage().delete_many(stored_keys)
            job.record('duplicate')
        else:
            # Photos without faces are kept too: they go to the album every guest can see.
            job.record('uploaded' if face_count > 0 else 'no_face')
    except Exception as e:
        logger.error(f"Upload error for {filename}: {e}", exc_info=True)
        try:
            storage_service.get_storage().delete_many(stored_keys)
        except Exception as cleanup_error:
            logger.error(f"Could not remove partial upload for {filename}: {cleanup_error}")
        job.record('failed', filename, 'Could not store the photo')
    finally:
        storage_service.cleanup_temp(temp_path)


@photographer_bp.route('/api/photographer/batch-status/<job_id>', methods=['GET'])
def batch_status(job_id):
    job = registry.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.snapshot())


@photographer_bp.route('/api/photographer/stats', methods=['GET'])
@limiter.limit("60 per minute")
def stats():
    code = request.args.get('code', '').strip().upper()
    event, _role, error = _authorised_event(code, ('host',))
    if error:
        return error
    try:
        counts = repo.event_stats(event['id'])
    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        return jsonify({'error': 'Database error'}), 500

    return jsonify({
        'code': event['code'],
        'event_name': event['event_name'],
        'photographer_name': event['name'],
        'total_photos': event['total_photos'],
        'faces_detected': counts['faces_detected'],
        'common_photos': counts['common_photos'],
        'total_users': counts['total_users'],
        'total_downloads': counts['total_downloads']
    })


@photographer_bp.route('/api/photographer/event', methods=['DELETE'])
@limiter.limit("10 per hour")
def delete_event():
    """Permanently delete an event with all of its photos and guest sessions."""
    code = request.args.get('code', '').strip().upper()
    event, _role, error = _authorised_event(code, ('host',))
    if error:
        return error
    files_removed = delete_event_data(event['id'])
    logger.info(f"Event {event['code']} deleted by its host ({files_removed} files)")
    return jsonify({'deleted': True, 'files_removed': files_removed})
