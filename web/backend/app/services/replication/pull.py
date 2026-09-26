# web/backend/app/services/replication/pull.py
# Tire les modifications du serveur central et les applique localement (LWW).
# Tous les messages et commentaires sont en français.
import requests
from datetime import datetime

from flask import current_app

from app import db
from app.models.sync_replica import (
    SyncCursor,
    SyncLocalMapping,
    SyncOutbox,
)
from app.services.replication import (
    REPLICATION_TIMEOUT,
    SUPPRESS_OUTBOX_KEY,
    auth_headers,
    device_id,
    record_online_state,
    remote_base_url,
)
from app.services.replication.entities import (
    REPLICATED_ENTITIES,
    clean_payload,
    find_existing,
    get_model,
    missing_required,
)


def resolve_local_tenant_id():
    """Tenant du poste : posé au login, sinon déduit de la dernière mutation."""
    tenant_id = current_app.config.get('LOCAL_TENANT_ID')
    if tenant_id:
        return tenant_id
    last = SyncOutbox.query.order_by(SyncOutbox.id.desc()).first()
    return last.tenant_id if last else None


def ensure_cursors(tenant_id):
    """Crée les curseurs manquants (révision 0) pour les entités répliquées.

    Sans curseur, `pull_changes` n'interroge jamais le central : un poste
    fraîchement installé ne recevrait aucun produit ni client.
    """
    created = []
    poste_id = device_id()
    for entity in REPLICATED_ENTITIES:
        exists = SyncCursor.query.filter_by(
            tenant_id=tenant_id,
            device_id=poste_id,
            entity=entity,
        ).first()
        if exists is None:
            SyncCursor.upsert(
                tenant_id=tenant_id, device_id=device_id(), entity=entity,
                last_pulled_revision=0,
            )
            created.append(entity)
    return created


def _parse_dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _local_row(entity, tenant_id, remote_pk, payload):
    """Retrouve la ligne locale correspondant à un changement distant."""
    model = get_model(entity)
    local_pk = SyncLocalMapping.local_pk_for(
        entity, remote_pk, tenant_id=tenant_id
    )
    if local_pk is not None:
        row = model.query.filter_by(id=local_pk, tenant_id=tenant_id).first()
        if row is not None:
            return row, 'mapping'
    row = find_existing(entity, tenant_id, payload)
    if row is not None:
        return row, 'natural_key'
    return None, None


def _apply_change(tenant_id, change):
    """Applique un changement du central. Retourne True si appliqué.

    - INSERT/UPDATE : dernière écriture gagnante sur `updated_at`.
    - DELETE        : suppression logique locale (is_active = False).
    L'outbox est neutralisée pendant l'écriture (sinon le changement reçu
    serait immédiatement re-poussé vers le central : boucle infinie).
    """
    entity = change.get('entity')
    op = change.get('op')
    payload = change.get('payload') or {}
    remote_pk = change.get('entity_pk')
    if get_model(entity) is None:
        return False

    row, source = _local_row(entity, tenant_id, remote_pk, payload)
    db.session.info[SUPPRESS_OUTBOX_KEY] = True
    try:
        if op == 'DELETE':
            if row is None:
                return False
            if hasattr(row, 'is_active'):
                row.is_active = False
            elif hasattr(row, 'statut'):
                row.statut = 'supprime'
            db.session.flush()
            return True

        cleaned = clean_payload(entity, payload)
        if row is None:
            # Payload incomplet : impossible de créer la ligne locale
            # (contrainte NOT NULL) — on n'applique rien plutôt que d'échouer
            # en boucle.
            if missing_required(entity, payload):
                return False
            model = get_model(entity)
            cleaned.pop('tenant_id', None)
            row = model(tenant_id=tenant_id, **cleaned)
            db.session.add(row)
            db.session.flush()
            SyncLocalMapping.upsert(
                tenant_id=tenant_id, entity=entity, local_pk=row.id,
                remote_pk=remote_pk,
            )
            db.session.flush()
            return True

        remote_updated = _parse_dt(payload.get('updated_at'))
        if remote_updated and row.updated_at and row.updated_at > remote_updated:
            return False  # version locale plus récente : on garde la locale
        for field, value in cleaned.items():
            setattr(row, field, value)
        if remote_pk is not None and source != 'mapping':
            SyncLocalMapping.upsert(
                tenant_id=tenant_id, entity=entity, local_pk=row.id,
                remote_pk=remote_pk,
            )
        db.session.flush()
        return True
    finally:
        db.session.info.pop(SUPPRESS_OUTBOX_KEY, None)


def _fetch_changes(base, cursor):
    """GET du central pour une entité. Retourne (ok, body, message)."""
    response = requests.get(
        f'{base}/api/v1/sync/replicate/pull',
        params={
            'since_revision': cursor.last_pulled_revision,
            'entities': cursor.entity,
        },
        headers=auth_headers(),
        timeout=REPLICATION_TIMEOUT,
    )
    status_code = getattr(response, 'status_code', 200)
    if status_code in (401, 403):
        if refresh_service_token():
            try:
                response = requests.get(
                    f'{base}/api/v1/sync/replicate/pull',
                    params={
                        'since_revision': cursor.last_pulled_revision,
                        'entities': cursor.entity,
                    },
                    headers=auth_headers(),
                    timeout=REPLICATION_TIMEOUT,
                )
                status_code = getattr(response, 'status_code', 200)
            except Exception as exc:
                return False, None, str(exc)[:500]
        if status_code in (401, 403):
            return False, None, (
                'Session de réplication refusée par le serveur central '
                f'({status_code}) : reconnectez-vous en ligne.'
            )
    if not getattr(response, 'ok', status_code < 400):
        return False, None, (
            f'Le serveur central a répondu {status_code} à la synchronisation.'
        )
    try:
        return True, (response.json() or {}), None
    except Exception:
        return False, None, 'Réponse illisible du serveur central.'


def pull_changes(app):
    """Applique les changements du central. Retourne {'applied', 'revision'}."""
    with app.app_context():
        base = remote_base_url()
        tenant_id = resolve_local_tenant_id()
        if not base:
            record_online_state(online=False, error=(
                "REPLICATION_URL non configurée : impossible de joindre le "
                "serveur central."
            ))
            return {'applied': 0, 'revision': 0}
        if tenant_id is None:
            record_online_state(online=False, error=(
                "Aucun utilisateur synchronisé : connectez-vous une fois en "
                "ligne pour initialiser la réplication."
            ))
            return {'applied': 0, 'revision': 0}

        if not SyncCursor.query.first():
            ensure_cursors(tenant_id)

        applied = 0
        max_revision = 0
        error = None
        my_device = device_id()

        cursors = SyncCursor.query.filter_by(
            tenant_id=tenant_id,
            device_id=my_device,
        ).order_by(SyncCursor.id.asc()).all()

        for cursor in cursors:
            try:
                ok, body, message = _fetch_changes(base, cursor)
            except Exception as exc:
                error = str(exc)[:500]
                continue
            if not ok:
                error = message
                if message and 'Session de réplication refusée' in message:
                    break
                continue

            for change in body.get('changes', []):
                # Ne jamais réappliquer nos propres mutations : elles sont
                # déjà en base locale (sinon doublon à chaque pull).
                if change.get('source_device_id') == my_device:
                    continue
                tenant_for_change = (
                    (change.get('payload') or {}).get('tenant_id') or tenant_id
                )
                try:
                    if _apply_change(tenant_for_change, change):
                        applied += 1
                except Exception as exc:
                    db.session.rollback()
                    error = (
                        f"Échec d'application du changement "
                        f"{change.get('entity')}#{change.get('entity_pk')} : "
                        f'{str(exc)[:200]}'
                    )
            revision = body.get('revision')
            if revision is not None:
                max_revision = max(max_revision, revision)
                SyncCursor.upsert(
                    tenant_id=cursor.tenant_id,
                    device_id=cursor.device_id,
                    entity=cursor.entity,
                    last_pulled_revision=revision,
                )

        db.session.commit()
        record_online_state(
            online=error is None, error=error, pull_done=True,
        )
        return {'applied': applied, 'revision': max_revision}


def apply_remote_locally(entity, remote_payload, local_pk, tenant_id=None):
    """Écrase l'enregistrement local par la version distante (remote_wins).

    Appelé par POST /sync/conflicts/<id>/resolve : l'opérateur a choisi la
    version du serveur central, on l'applique localement sans repartir en
    conflit (l'écriture n'est PAS recapturée par l'outbox).

    Retourne (ok, message).
    """
    model = get_model(entity)
    if model is None:
        return False, f'Entité non supportée par la réplication : {entity}.'

    row = None
    if local_pk is not None:
        query = model.query.filter_by(id=local_pk)
        if tenant_id is not None and hasattr(model, 'tenant_id'):
            query = query.filter_by(tenant_id=tenant_id)
        row = query.first()
    if row is None:
        return False, "Enregistrement local introuvable pour ce conflit."

    payload = remote_payload or {}
    cleaned = clean_payload(entity, payload)
    if not cleaned:
        return False, 'Version distante vide : rien à appliquer.'

    resolved_at = _parse_dt(payload.get('updated_at')) or datetime.utcnow()
    db.session.info[SUPPRESS_OUTBOX_KEY] = True
    try:
        for field, value in cleaned.items():
            setattr(row, field, value)
        # La version distante devient la référence locale : sans cette
        # datation, une prochaine mutation locale repasserait en conflit.
        row.updated_at = resolved_at
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return False, f"Échec de l'application de la version distante : {exc}"
    finally:
        db.session.info.pop(SUPPRESS_OUTBOX_KEY, None)
    return True, None
