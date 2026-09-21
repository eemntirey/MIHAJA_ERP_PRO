import requests
from datetime import datetime
from flask import current_app
from app import db
from app.models.sync_replica import SyncOutbox, SyncConflict, SyncState

MAX_BATCH = 100


def push_pending(app):
    with app.app_context():
        base = current_app.config.get('REPLICATION_URL', '').rstrip('/')
        token = current_app.extensions.get('repl_token') or ''
        device_id = current_app.config.get('REPLICATION_DEVICE_ID', 'unknown')
        entries = SyncOutbox.query.filter(
            SyncOutbox.status.in_(['pending', 'failed'])
        ).limit(MAX_BATCH).all()
        sent = 0
        for e in entries:
            try:
                r = requests.post(
                    f'{base}/api/v1/sync/replicate/push',
                    json={
                        'mutations': [{
                            'entity': e.entity,
                            'entity_pk': e.entity_pk,
                            'local_uuid': e.local_uuid,
                            'op': e.op,
                            'idempotency_key': e.idempotency_key,
                            'payload': e.payload,
                            'occurred_at': e.created_at.isoformat() if e.created_at else None,
                        }]
                    },
                    headers={
                        'Authorization': f'Bearer {token}',
                        'X-Device-Id': device_id,
                    },
                    timeout=15,
                )
                res = r.json()['results'][0] if r.ok and r.json().get('results') else {}
                if res.get('status') in ('applied', 'duplicate'):
                    e.status = 'sent'
                    e.synced_at = datetime.utcnow()
                    sent += 1
                elif res.get('status') == 'conflict':
                    e.status = 'conflict'
                    db.session.add(SyncConflict(
                        tenant_id=e.tenant_id,
                        device_id=e.device_id,
                        entity=e.entity,
                        entity_pk=e.entity_pk,
                        local_payload=e.payload,
                        remote_payload=res.get('remote_payload'),
                        resolved_as='remote_wins',
                    ))
            except Exception as exc:
                e.status = 'failed'
                e.attempts = (e.attempts or 0) + 1
                e.last_error = str(exc)[:500]
            db.session.commit()
        state = SyncState.get_or_create()
        state.pending_count = (
            SyncOutbox.query.filter_by(status='pending').count()
            + SyncOutbox.query.filter_by(status='failed').count()
        )
        state.last_push_at = datetime.utcnow()
        db.session.commit()
        return {'sent': sent, 'remaining': state.pending_count}
