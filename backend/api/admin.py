"""Operator endpoints. All of them need the X-Admin-Secret header (see backend.security)."""
import logging

from flask import Blueprint, jsonify, request

from backend.database import repo
from backend.extensions import limiter
from backend.security import (CONTRIBUTOR_KEY_PREFIX, HOST_KEY_PREFIX, hash_key, new_key,
                              require_admin)
from backend.services import retention_service

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)


def _wants_dry_run():
    # Deleting is opt-in: anything other than an explicit dry_run=0 only reports.
    return request.args.get('dry_run', '1') != '0'


@admin_bp.route('/api/admin/events/<code>/keys', methods=['POST'])
@limiter.limit("20 per hour")
@require_admin
def issue_keys(code):
    """Issue fresh host and contributor keys for an event; any earlier keys stop working.

    Needed for events created before upload keys existed, and when a host loses their key.
    """
    event = repo.get_event_by_code(code.strip().upper())
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    host_key = new_key(HOST_KEY_PREFIX)
    contributor_key = new_key(CONTRIBUTOR_KEY_PREFIX)
    repo.set_event_keys(event['id'], hash_key(host_key), hash_key(contributor_key))
    logger.info(f"Keys reissued for event {event['code']}")
    return jsonify({'code': event['code'], 'host_key': host_key, 'contributor_key': contributor_key})


@admin_bp.route('/api/admin/purge-expired', methods=['POST'])
@limiter.limit("20 per hour")
@require_admin
def purge_expired():
    """List (or with dry_run=0, delete) events that are past their retention period."""
    return jsonify(retention_service.purge_expired(dry_run=_wants_dry_run()))


@admin_bp.route('/api/admin/purge-selfies', methods=['POST'])
@limiter.limit("20 per hour")
@require_admin
def purge_selfies():
    """Count (or with dry_run=0, delete) selfies stored by older versions of the app."""
    return jsonify(retention_service.purge_legacy_selfies(dry_run=_wants_dry_run()))
