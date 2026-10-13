"""Deleting data: a single event on request, and old events under the retention policy."""
import logging
import threading
import time

from backend.config import Config
from backend.database import repo
from backend.security import storage_key
from backend.services.storage_service import get_storage

logger = logging.getLogger(__name__)

_AUTO_PURGE_INTERVAL = 24 * 3600


def delete_event_data(event_id):
    """Delete an event's files and then its rows. Returns the number of files removed.

    Files go first: if anything fails midway the rows still exist, so the delete can simply
    be run again. The other order could leave photos in storage that nothing points to.
    """
    keys = [k for k in (storage_key(p) for p in repo.event_file_paths(event_id)) if k]
    removed = get_storage().delete_many(keys)
    repo.delete_event(event_id)
    return removed


def _compact_storage():
    try:
        get_storage().compact()
    except Exception as e:
        logger.error(f'Storage compaction failed: {e}')


def purge_expired(dry_run=True):
    """Delete events past their retention period. With dry_run nothing is deleted."""
    events = repo.expired_events(Config.RETENTION_DAYS)
    report = {
        'dry_run': dry_run,
        'events': [{'code': e['code'], 'event_name': e['event_name'],
                    'total_photos': e['total_photos'], 'created_at': str(e['created_at'])} for e in events],
        'files_removed': 0,
    }
    if dry_run or not events:
        return report
    for event in events:
        report['files_removed'] += delete_event_data(event['id'])
        logger.info(f"Retention purge removed event {event['code']}")
    _compact_storage()
    return report


def purge_legacy_selfies(dry_run=True):
    """Delete selfies that older versions of the app stored permanently."""
    rows = repo.legacy_selfies()
    keys = [k for k in (storage_key(r['selfie_path']) for r in rows) if k]
    report = {'dry_run': dry_run, 'selfies': len(rows), 'files_removed': 0}
    if dry_run or not rows:
        return report
    report['files_removed'] = get_storage().delete_many(keys)
    repo.clear_selfie_paths([r['id'] for r in rows])
    _compact_storage()
    return report


def start_auto_purge():
    """Run the retention purge once a day. Only called when RETENTION_AUTO_PURGE is on."""
    def loop():
        while True:
            try:
                report = purge_expired(dry_run=False)
                if report['events']:
                    logger.info(f"Auto purge removed {len(report['events'])} expired events")
            except Exception as e:
                logger.error(f'Auto purge failed: {e}')
            time.sleep(_AUTO_PURGE_INTERVAL)

    threading.Thread(target=loop, daemon=True, name='retention-purge').start()
