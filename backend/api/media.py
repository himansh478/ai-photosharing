import logging

from flask import Blueprint, Response, jsonify, request, stream_with_context

from backend.extensions import limiter
from backend.security import storage_key, verify_media_signature
from backend.services.storage_service import ObjectNotFound, get_storage

media_bp = Blueprint('media', __name__)
logger = logging.getLogger(__name__)


@media_bp.route('/api/media/<path:key>')
@limiter.exempt  # every request already carries a signature, and one gallery loads many images
def media(key):
    """Stream one stored photo. Only links signed by this server, and not yet expired, work."""
    download = request.args.get('dl') == '1'
    if storage_key(key) != key or not verify_media_signature(
            key, request.args.get('exp'), request.args.get('sig'), download):
        return jsonify({'error': 'This link is invalid or has expired'}), 403

    try:
        chunks, content_type = get_storage().open(key)
    except ObjectNotFound:
        return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        logger.error(f"Failed to fetch {key} from storage: {e}")
        return jsonify({'error': 'Image temporarily unavailable'}), 502

    response = Response(stream_with_context(chunks), content_type=content_type)
    # The signed URL is the permission, so only the guest's own browser may cache the image.
    response.headers['Cache-Control'] = 'private, max-age=3600'
    if download:
        response.headers['Content-Disposition'] = f'attachment; filename="{key.rsplit("/", 1)[1]}"'
    return response
