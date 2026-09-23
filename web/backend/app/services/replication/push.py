# web/backend/app/services/replication/push.py
# Pousse les mutations locales en attente vers le serveur central.
# Tous les messages et commentaires sont en français.
import requests
from datetime import datetime

from app import db
from app.models.sync_replica import (
    SyncConflict,
    SyncLocalMapping,
    SyncOutbox,
)
from app.services.replication import (
    REPLICATION_TIMEOUT,
    auth_headers,
    device_id,
    record_online_state,
    remote_base_url,
)

MAX_BATCH = 100

# Statuts renvoyés par le central (cf. app/api/v1/replication.py).
_SENT_STATUSES = ('applied', 'duplicate')
_FAILED_STATUSES = ('unsupported', 'rejected')


def _mutation_for(entry):
    """Construit la mutation à envoyer pour une entrée d'outbox."""
    entity_pk = entry.entity_pk
    if entity_pk is not None:
        # Risque n°6 : la PK locale n'est pas la PK centrale. On envoie la
        # correspondance si elle existe (mutation déjà poussée une fois).
        remote_pk = SyncLocalMapping.remote_pk_for(entry.entity, entity_pk)
        if remote_pk is not None:
            entity_pk = remote_pk
    return {
        'entity': entry.entity,
        'entity_pk': entity_pk,
        'local_uuid': entry.local_uuid,
        'op': entry.op,
        'idempotency_key': entry.idempotency_key,
        'payload': entry.payload,
        'occurred_at': (
            entry.created_at.isoformat() if entry.created_at else None
        ),
    }


def _remember_mapping(entry, server_pk):
    """Mémorise la correspondance PK locale <-> PK centrale."""
    if server_pk is None or entry.entity_pk is None:
        return
    SyncLocalMapping.upsert(
        tenant_id=entry.tenant_id,
        entity=entry.entity,
        local_pk=entry.entity_pk,
        remote_pk=server_pk,
        local_uuid=entry.local_uuid,
    )


def _send(base, entry):
    """POST d'une mutation. Leve une exception réseau si le central est absent."""
    return requests.post(
        f'{base}/api/v1/sync/replicate/push',
        json={'mutations': [_mutation_for(entry)]},
        headers=auth_headers(),
        timeout=REPLICATION_TIMEOUT,
    )


def push_pending(app):
    """Envoie les mutations en attente. Retourne {'sent', 'remaining'}."""
    with app.app_context():
        base = remote_base_url()
        if not base:
            record_online_state(online=False, error=(
                "REPLICATION_URL non configurée : impossible de joindre le "
                "serveur central."
            ))
            return {'sent': 0, 'remaining': 0}

        entries = SyncOutbox.query.filter(
            SyncOutbox.status.in_(['pending', 'failed'])
        ).order_by(SyncOutbox.id.asc()).limit(MAX_BATCH).all()

        sent = 0
        network_error = None
        auth_error = None
        server_error = None

        for entry in entries:
            try:
                response = _send(base, entry)
            except Exception as exc:
                network_error = str(exc)[:500]
                entry.status = 'failed'
                entry.attempts = (entry.attempts or 0) + 1
                entry.last_error = network_error
                db.session.commit()
                continue

            status_code = getattr(response, 'status_code', 200)

            if status_code in (401, 403):
                # Jeton absent/expiré : inutile d'insister sur les autres
                # entrées, le poste doit se reconnecter en ligne.
                auth_error = (
                    'Session de réplication refusée par le serveur central '
                    f'({status_code}) : reconnectez-vous en ligne.'
                )
                entry.last_error = auth_error
                db.session.commit()
                break

            if not getattr(response, 'ok', status_code < 400):
                server_error = (
                    f'Le serveur central a répondu {status_code} '
                    'à la synchronisation.'
                )
                entry.status = 'failed'
                entry.attempts = (entry.attempts or 0) + 1
                entry.last_error = server_error
                db.session.commit()
                continue

            result = {}
            try:
                body = response.json() or {}
                if body.get('results'):
                    result = body['results'][0]
            except Exception:
                result = {}

            status = result.get('status')
            if status in _SENT_STATUSES:
                entry.status = 'sent'
                entry.synced_at = datetime.utcnow()
                entry.last_error = None
                _remember_mapping(entry, result.get('server_pk'))
                sent += 1
            elif status == 'conflict':
                entry.status = 'conflict'
                entry.last_error = result.get('message')
                db.session.add(SyncConflict(
                    tenant_id=entry.tenant_id,
                    device_id=entry.device_id or device_id(),
                    entity=entry.entity,
                    entity_pk=entry.entity_pk,
                    local_payload=entry.payload,
                    remote_payload=result.get('remote_payload'),
                    # Aucune version n'est écrasée automatiquement : la
                    # résolution est explicite (cf. /sync/conflicts).
                    resolved_as='pending_review',
                ))
            elif status in _FAILED_STATUSES:
                # 'unsupported' (entité hors périmètre V1) ou 'rejected' :
                # la mutation n'a PAS été appliquée — on le dit explicitement.
                entry.status = 'failed'
                entry.attempts = (entry.attempts or 0) + 1
                entry.last_error = (
                    result.get('message') or
                    f'Mutation refusée par le serveur central ({status}).'
                )
            else:
                entry.status = 'failed'
                entry.attempts = (entry.attempts or 0) + 1
                entry.last_error = (
                    'Réponse inattendue du serveur central pour la mutation.'
                )
            db.session.commit()

        error = auth_error or network_error or server_error
        state = record_online_state(
            online=error is None, error=error, push_done=True,
        )
        return {'sent': sent, 'remaining': state.pending_count}


def force_push_conflict(conflict):
    """Re-pousse la version locale d'un conflit avec priorité forcée.

    Utilisée par POST /sync/conflicts/<id>/resolve (resolution=local_wins) :
    le central reçoit `X-Force-Win: true` et applique la version locale sans
    arbitrage LWW (l'opérateur a tranché explicitement).

    Retourne (ok, message).
    """
    import uuid as _uuid

    base = remote_base_url()
    if not base:
        return False, "REPLICATION_URL non configurée : push impossible."

    entity_pk = conflict.entity_pk
    if entity_pk is not None:
        entity_pk = SyncLocalMapping.remote_pk_for(
            conflict.entity, entity_pk
        ) or entity_pk

    mutation = {
        'entity': conflict.entity,
        'entity_pk': entity_pk,
        'local_uuid': str(_uuid.uuid4()),
        'op': 'UPDATE' if entity_pk is not None else 'INSERT',
        'idempotency_key': (
            f'{device_id()}:force:{conflict.id}:{_uuid.uuid4()}'
        ),
        'payload': conflict.local_payload or {},
        'occurred_at': datetime.utcnow().isoformat(),
    }

    try:
        response = requests.post(
            f'{base}/api/v1/sync/replicate/push',
            json={'mutations': [mutation]},
            headers={**auth_headers(), 'X-Force-Win': 'true'},
            timeout=REPLICATION_TIMEOUT,
        )
    except Exception as exc:
        return False, f'Serveur central injoignable : {str(exc)[:200]}'

    if not getattr(response, 'ok', False):
        return False, (
            f'Le serveur central a refusé la résolution '
            f'({getattr(response, "status_code", "?")}).'
        )

    try:
        result = (response.json() or {}).get('results', [{}])[0]
    except Exception:
        result = {}

    if result.get('status') in _SENT_STATUSES:
        # L'entrée d'outbox en conflit est désormais appliquée côté central.
        for entry in SyncOutbox.query.filter_by(
            entity=conflict.entity, status='conflict'
        ).all():
            if entry.entity_pk == conflict.entity_pk:
                entry.status = 'sent'
                entry.synced_at = datetime.utcnow()
                entry.last_error = None
        db.session.commit()
        return True, None

    return False, (
        result.get('message') or
        'Le serveur central n\'a pas appliqué la version locale.'
    )

