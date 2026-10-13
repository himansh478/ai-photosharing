"""Codes, keys and signed media links.

Three kinds of secrets exist per event:
  * guest code       - shared with every attendee; only lets them search for their own photos
  * contributor key  - lets someone upload photos, nothing else
  * host key         - full control of the event (upload, stats, delete)
Keys are random and only their SHA-256 hash is stored.
"""
import base64
import hashlib
import hmac
import logging
import re
import secrets
import time
from functools import wraps

from flask import jsonify, request

from backend.config import Config

logger = logging.getLogger(__name__)

# No 0/O or 1/I, so a code read aloud or typed from a poster is unambiguous.
_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
_CODE_LENGTH = 10

HOST_KEY_PREFIX = 'hk_'
CONTRIBUTOR_KEY_PREFIX = 'ck_'

# Only objects the app itself wrote may be served; this also blocks path traversal.
_STORAGE_KEY_RE = re.compile(r'^(photos|thumbnails)/[A-Za-z0-9_]{8,80}\.(jpg|jpeg|png|webp|bmp)$')
_LEGACY_PROXY_PREFIX = '/api/proxy/'

_process_secret = None


def new_guest_code():
    return 'EVT-' + ''.join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


def new_key(prefix):
    return prefix + secrets.token_urlsafe(24)


def hash_key(key):
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def key_matches(provided, stored_hash):
    if not provided or not stored_hash:
        return False
    return hmac.compare_digest(hash_key(provided), stored_hash)


def role_for_key(event, provided_key):
    """Return 'host', 'contributor' or None for the key presented with a request."""
    if key_matches(provided_key, event.get('host_key_hash')):
        return 'host'
    if key_matches(provided_key, event.get('contributor_key_hash')):
        return 'contributor'
    return None


def request_event_key():
    """The event key travels in a header so it never lands in URLs or access logs."""
    return (request.headers.get('X-Event-Key') or '').strip()


def storage_key(value):
    """Normalise a stored path to a storage key, or None if it is not one of ours.

    Older rows hold '/api/proxy/photos/x.jpg'; newer rows hold 'photos/x.jpg'.
    """
    if not value:
        return None
    if value.startswith(_LEGACY_PROXY_PREFIX):
        value = value[len(_LEGACY_PROXY_PREFIX):]
    return value if _STORAGE_KEY_RE.match(value) else None


def _secret():
    global _process_secret
    if Config.APP_SECRET:
        return Config.APP_SECRET.encode('utf-8')
    if _process_secret is None:
        _process_secret = secrets.token_bytes(32)
        if not Config.TESTING:
            logger.warning('APP_SECRET is not set; media links will stop working after a restart.')
    return _process_secret


def _media_signature(key, expires, download):
    message = f'{key}\n{expires}\n{int(bool(download))}'.encode('utf-8')
    digest = hmac.new(_secret(), message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')


def signed_media_url(key, ttl=None, download=False):
    """A link to one stored object that expires after `ttl` seconds."""
    expires = int(time.time()) + (ttl if ttl is not None else Config.MEDIA_URL_TTL)
    url = f'/api/media/{key}?exp={expires}&sig={_media_signature(key, expires, download)}'
    return url + '&dl=1' if download else url


def verify_media_signature(key, expires, signature, download):
    try:
        expires = int(expires)
    except (TypeError, ValueError):
        return False
    if expires < time.time() or not signature:
        return False
    return hmac.compare_digest(_media_signature(key, expires, download), signature)


def require_admin(view):
    """Admin endpoints need the X-Admin-Secret header and do not exist until ADMIN_SECRET is set."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not Config.ADMIN_SECRET:
            return jsonify({'error': 'Not found'}), 404
        provided = request.headers.get('X-Admin-Secret', '')
        if not hmac.compare_digest(provided.encode('utf-8'), Config.ADMIN_SECRET.encode('utf-8')):
            logger.warning('Rejected admin request to %s from %s', request.path, request.remote_addr)
            return jsonify({'error': 'Forbidden'}), 403
        return view(*args, **kwargs)
    return wrapper
