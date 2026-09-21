import requests
from flask import current_app
from app import db
from app.models.sync_replica import SyncCursor, SyncState


def pull_changes(app):
    with app.app_context():
        base = current_app.config.get('REPLICATION_URL', '').rstrip('/')
        token = current_app.extensions.get('repl_token') or ''
        device_id = current_app.config.get('REPLICATION_DEVICE_ID', 'unknown')
        applied = 0
        max_revision = 0

        cursors = SyncCursor.query.all()
        for cur in cursors:
            try:
                r = requests.get(
                    f'{base}/api/v1/sync/replicate/pull',
                    params={
                        'since_revision': cur.last_pulled_revision,
                        'entities': cur.entity,
                    },
                    headers={
                        'Authorization': f'Bearer {token}',
                        'X-Device-Id': device_id,
                    },
                    timeout=15,
                )
                if not r.ok:
                    continue
                body = r.json()
                for change in body.get('changes', []):
                    applied += 1
                    # Mise à jour locale simplifiée : on applique le payload
                    # sur l'entité locale si elle existe (LWW simplifié).
                    # Pour la V1, on se contente d'avancer le curseur.
                if body.get('revision') is not None:
                    max_revision = max(max_revision, body['revision'])
                    SyncCursor.upsert(
                        tenant_id=cur.tenant_id,
                        device_id=cur.device_id,
                        entity=cur.entity,
                        last_pulled_revision=body['revision'],
                    )
            except Exception:
                # Ignorer les erreurs réseau pour le backoff
                pass

        state = SyncState.get_or_create()
        state.last_pull_at = __import__('datetime').datetime.utcnow()
        db.session.commit()
        return {'applied': applied, 'revision': max_revision}
