import logging
import uuid

from flask import Blueprint, jsonify, redirect, request

from backend.config import Config
from backend.database import repo
from backend.extensions import limiter
from backend.models.face_engine import EngineNotReady, ImageUnreadable, get_engine
from backend.security import signed_media_url, storage_key
from backend.services import storage_service
from backend.services.matching_service import MatchingService
from backend.validation import InvalidImage, validate_image

user_bp = Blueprint('user', __name__)
logger = logging.getLogger(__name__)
matching_service = MatchingService()

_COMMON_PAGE_SIZE = 60


def _photo_card(photo_id, thumbnail_path, session_id, similarity=None):
    thumb_key = storage_key(thumbnail_path)
    card = {
        'photo_id': photo_id,
        'thumbnail_url': signed_media_url(thumb_key) if thumb_key else None,
        'download_url': f'/api/user/download/{photo_id}?session_id={session_id}',
    }
    if similarity is not None:
        card['similarity'] = similarity
    return card


@user_bp.route('/api/user/verify-code', methods=['POST'])
@limiter.limit("30 per minute")
def verify_code():
    code = str((request.get_json(silent=True) or {}).get('code', '')).strip().upper()
    if not code:
        return jsonify({'valid': False, 'error': 'Code is required'}), 400

    try:
        event = repo.get_event_by_code(code)
    except Exception as e:
        logger.error(f"Event lookup failed: {e}")
        return jsonify({'valid': False, 'error': 'Service temporarily unavailable'}), 503

    if not event:
        return jsonify({'valid': False, 'error': 'Invalid event code'}), 400

    return jsonify({
        'valid': True,
        'event_name': event['event_name'],
        'photographer_name': event['name'],
        'total_photos': event['total_photos']
    })


@user_bp.route('/api/user/upload-selfie', methods=['POST'])
@limiter.limit("30 per minute; 300 per hour")
def upload_selfie():
    code = request.form.get('code', '').strip().upper()
    photo = request.files.get('photo')

    if not code or not photo:
        return jsonify({'error': 'code and photo are required'}), 400
    # Face matching uses biometric data, so the guest has to agree to it explicitly.
    if request.form.get('consent', '').strip().lower() not in ('yes', 'true', '1'):
        return jsonify({'error': 'Please agree to face matching before searching.'}), 400

    event = repo.get_event_by_code(code)
    if not event:
        return jsonify({'error': 'Invalid event code'}), 401

    engine = get_engine()
    if not engine.is_ready():
        engine.load_in_background()
        response = jsonify({'error': 'Face recognition engine not ready. Please retry shortly.'})
        response.headers['Retry-After'] = '20'
        return response, 503

    # The selfie only ever exists as a temp file: it is deleted as soon as the face
    # has been read from it, and is never uploaded or stored.
    temp_path = storage_service.save_to_temp(photo)
    try:
        validate_image(temp_path, Config.MAX_SELFIE_BYTES)
        user_embedding = engine.get_user_embedding(temp_path)
    except InvalidImage as e:
        return jsonify({'error': str(e)}), 400
    except ImageUnreadable:
        return jsonify({'error': 'Could not read your photo. Please try another one.'}), 400
    except EngineNotReady:
        return jsonify({'error': 'Face recognition engine not ready. Please retry shortly.'}), 503
    finally:
        storage_service.cleanup_temp(temp_path)

    if user_embedding is None:
        return jsonify({'error': 'No face detected in your photo.'}), 400

    matches = matching_service.find_matches(user_embedding, event['id'])

    # The session records exactly which photos this guest may open.
    session_id = str(uuid.uuid4())
    repo.create_session(session_id, event['id'],
                        [(m['photo_id'], m['similarity']) for m in matches],
                        Config.SESSION_TTL_HOURS)

    return jsonify({
        'session_id': session_id,
        'matched_count': len(matches),
        'photos': [_photo_card(m['photo_id'], m['thumbnail_path'], session_id, m['similarity'])
                   for m in matches],
        'common_count': repo.count_common_photos(event['id']),
    })


@user_bp.route('/api/user/common-photos', methods=['GET'])
@limiter.limit("120 per minute")
def common_photos():
    """Photos without faces (decor, rituals, venue), visible to every guest of the event."""
    session = repo.get_active_session(request.args.get('session_id', ''))
    if not session:
        return jsonify({'error': 'Session expired. Please search again.'}), 401
    try:
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        offset = 0

    rows = repo.common_photos(session['photographer_id'], _COMMON_PAGE_SIZE, offset)
    return jsonify({
        'photos': [_photo_card(r['id'], r['thumbnail_path'], session['id']) for r in rows],
        'next_offset': offset + len(rows) if len(rows) == _COMMON_PAGE_SIZE else None,
    })


@user_bp.route('/api/user/download/<photo_id>', methods=['GET'])
def download_photo(photo_id):
    session_id = request.args.get('session_id', '')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 401

    # Same answer whether the photo does not exist or simply is not this guest's.
    photo = repo.session_photo(session_id, photo_id)
    key = storage_key(photo['file_path']) if photo else None
    if not key:
        return jsonify({'error': 'Photo not found'}), 404

    try:
        repo.log_download(str(uuid.uuid4()), session_id, photo_id)
    except Exception as e:
        logger.warning(f"Could not log download: {e}")

    return redirect(signed_media_url(key, ttl=Config.DOWNLOAD_URL_TTL, download=True))


@user_bp.route('/api/user/session/<session_id>', methods=['DELETE'])
@limiter.limit("30 per minute")
def delete_session(session_id):
    """A guest removes their search and its history ("delete my data")."""
    if not repo.delete_session(session_id):
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({'deleted': True})
