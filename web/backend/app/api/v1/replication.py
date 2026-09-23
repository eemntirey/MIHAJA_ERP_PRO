# web/backend/app/api/v1/replication.py
# Endpoints de réplication côté serveur CENTRAL.
# Espace de noms RESTx : sync/replicate
# Messages et commentaires en français.
#
# Contrat (cf. plan Task 4) :
#   POST /sync/replicate/push  -> {results: [{local_uuid, status, server_pk,
#                                              remote_payload?, message?}]}
#        status ∈ applied | duplicate | conflict | unsupported | rejected
#   GET  /sync/replicate/pull   -> {revision, changes}
#   GET  /sync/replicate/status -> {last_revision, server_time}
#
# Idempotence : chaque mutation porte une `idempotency_key` unique
# (device:local_uuid) ; une clé déjà appliquée renvoie `duplicate` avec le
# `server_pk` d'origine sans réappliquer la mutation (pas de double effet).
from datetime import datetime

from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.sync_replica import SyncAppliedKey, SyncCentralLog
from app.services.replication.entities import (
    clean_payload,
    find_existing,
    get_model,
    is_known_entity,
    missing_required,
)

ns = Namespace('sync/replicate', description='Réplication desktop -> central')

mutation_model = ns.model('Mutation', {
    'entity': fields.String(required=True, description='Nom entité (ex: produit)'),
    'entity_pk': fields.Integer(required=False, description='PK central de l entité'),
    'local_uuid': fields.String(required=True, description='UUID local de la mutation'),
    'op': fields.String(required=True, enum=['INSERT', 'UPDATE', 'DELETE']),
    'idempotency_key': fields.String(required=True, description='Clé d idempotence'),
    'payload': fields.Raw(required=True, description='Contenu de la mutation'),
    'occurred_at': fields.String(required=True, description='Date ISO de la mutation'),
})

push_model = ns.model('PushRequest', {
    'mutations': fields.List(fields.Nested(mutation_model), required=True),
})

push_result = ns.model('PushResult', {
    'local_uuid': fields.String(required=True),
    'status': fields.String(required=True),
    'server_pk': fields.Integer(required=False),
    'remote_payload': fields.Raw(required=False),
    'message': fields.String(required=False),
})

push_response = ns.model('PushResponse', {
    'results': fields.List(fields.Nested(push_result), required=True),
})

pull_response = ns.model('PullResponse', {
    'revision': fields.Integer(required=True),
    'changes': fields.List(fields.Raw, required=True),
})


def _tenant_id_from_request():
    """Tenant courant : posé par before_request (claims JWT) ou par headers."""
    from flask import g
    from flask_jwt_extended import get_jwt
    from app.security.tenant import get_current_tenant_id

    tenant_id = get_current_tenant_id()
    if tenant_id:
        return tenant_id
    try:
        tenant_id = (get_jwt() or {}).get('tenant_id')
    except Exception:
        tenant_id = None
    if tenant_id:
        return tenant_id
    tenant = getattr(g, 'current_tenant', None)
    return getattr(tenant, 'id', None)


def _parse_occurred_at(raw):
    """Convertit une date ISO (avec Z éventuel) en datetime naïf UTC."""
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _force_win():
    """Header X-Force-Win posé lors de la résolution manuelle d'un conflit."""
    return str(request.headers.get('X-Force-Win', '')).strip().lower() in (
        '1', 'true', 'yes', 'on',
    )


def _serialize(obj):
    return obj.to_dict() if hasattr(obj, 'to_dict') else {}


def _assign_allowed(obj, cleaned):
    for field, value in cleaned.items():
        setattr(obj, field, value)


def _log_central(tenant_id, mutation, server_pk, device_id):
    """Enregistre la mutation dans le journal central (même transaction).

    La révision est un compteur monotone par tenant : les postes reprennent
    leur pull à `revision > curseur`.
    """
    max_rev = db.session.query(
        db.func.max(SyncCentralLog.revision)
    ).filter(
        SyncCentralLog.tenant_id == tenant_id
    ).scalar() or 0
    db.session.add(SyncCentralLog(
        tenant_id=tenant_id,
        entity=mutation.get('entity'),
        entity_pk=server_pk,
        op=mutation.get('op'),
        payload=mutation.get('payload'),
        revision=max_rev + 1,
        source_device_id=device_id,
    ))


def _apply_insert(tenant_id, entity, payload):
    """INSERT répliqué — bascule en UPDATE si la clé naturelle existe déjà."""
    model = get_model(entity)
    manquants = missing_required(entity, payload)
    if manquants:
        return {
            'status': 'rejected', 'server_pk': None,
            'message': (
                'Champs obligatoires manquants pour '
                f"{entity} : {', '.join(manquants)}"
            ),
        }
    cleaned = clean_payload(entity, payload)

    # Idempotence inter-postes : même clé naturelle (référence / code) créée
    # ailleurs -> on met à jour la ligne existante au lieu de dupliquer.
    existing = find_existing(entity, tenant_id, cleaned)
    if existing is not None:
        _assign_allowed(existing, cleaned)
        db.session.flush()
        return {'status': 'applied', 'server_pk': existing.id}

    obj = model(tenant_id=tenant_id, **cleaned)
    savepoint = db.session.begin_nested()
    try:
        db.session.add(obj)
        db.session.flush()
        savepoint.commit()
    except IntegrityError:
        savepoint.rollback()
        if obj in db.session:
            db.session.expunge(obj)
        existing = find_existing(entity, tenant_id, cleaned)
        if existing is None:
            return {
                'status': 'rejected', 'server_pk': None,
                'message': (
                    f"Doublon détecté pour {entity} (contrainte d'unicité)."
                ),
            }
        _assign_allowed(existing, cleaned)
        db.session.flush()
        return {'status': 'applied', 'server_pk': existing.id}
    return {'status': 'applied', 'server_pk': obj.id}


def _apply_update(tenant_id, entity, payload, entity_pk, occurred_at, force):
    """UPDATE répliqué : dernière écriture gagnante (LWW) sauf X-Force-Win."""
    model = get_model(entity)
    existing = None
    if entity_pk is not None:
        existing = model.query.filter_by(
            id=entity_pk, tenant_id=tenant_id
        ).first()
    if existing is None:
        # Le poste n'a pas (encore) la correspondance de PK : clé naturelle.
        existing = find_existing(entity, tenant_id, payload)
    if existing is None:
        return {
            'status': 'conflict', 'server_pk': None, 'remote_payload': None,
            'message': 'Entité introuvable côté central.',
        }

    cleaned = clean_payload(entity, payload)
    if not force and occurred_at is not None and existing.updated_at:
        if existing.updated_at > occurred_at:
            return {
                'status': 'conflict',
                'server_pk': existing.id,
                'remote_payload': _serialize(existing),
                'message': (
                    'Conflit : la version centrale est plus récente que la '
                    'mutation locale.'
                ),
            }
    _assign_allowed(existing, cleaned)
    db.session.flush()
    return {'status': 'applied', 'server_pk': existing.id}


def _apply_delete(tenant_id, entity, entity_pk, payload):
    """DELETE répliqué : suppression logique (is_active = False) en V1."""
    model = get_model(entity)
    existing = None
    if entity_pk is not None:
        existing = model.query.filter_by(
            id=entity_pk, tenant_id=tenant_id
        ).first()
    if existing is None:
        existing = find_existing(entity, tenant_id, payload)
    if existing is None:
        return {
            'status': 'conflict', 'server_pk': None, 'remote_payload': None,
            'message': 'Entité introuvable côté central (rien à supprimer).',
        }
    if hasattr(existing, 'is_active'):
        existing.is_active = False
    elif hasattr(existing, 'statut'):
        existing.statut = 'supprime'
    db.session.flush()
    return {'status': 'applied', 'server_pk': existing.id}


@ns.route('/push')
class ReplicationPush(Resource):
    @ns.expect(push_model, validate=False)
    @jwt_required()
    def post(self):
        """Applique des mutations locales (idempotence + conflits LWW)."""
        tenant_id = _tenant_id_from_request()
        if tenant_id is None:
            return {'message': 'Tenant introuvable pour cet utilisateur.'}, 403

        device_id = request.headers.get('X-Device-Id', 'unknown-device')
        force = _force_win()
        body = request.get_json(silent=True) or {}
        results = []

        for mutation in body.get('mutations', []):
            local_uuid = mutation.get('local_uuid')
            entity = mutation.get('entity')
            op = mutation.get('op')
            payload = mutation.get('payload') or {}
            entity_pk = mutation.get('entity_pk')
            idempotency_key = mutation.get('idempotency_key') or (
                f'{device_id}:{local_uuid}'
            )

            if not is_known_entity(entity):
                # Ne jamais répondre 'applied' pour une entité non gérée :
                # le poste perdrait la mutation en silence.
                results.append({
                    'local_uuid': local_uuid,
                    'status': 'unsupported',
                    'server_pk': None,
                    'message': (
                        'Entité non supportée par la réplication : '
                        f'{entity}.'
                    ),
                })
                continue

            applied = SyncAppliedKey.query.filter_by(
                idempotency_key=idempotency_key
            ).first()
            if applied:
                results.append({
                    'local_uuid': local_uuid,
                    'status': 'duplicate',
                    'server_pk': applied.server_pk,
                })
                continue

            if op == 'INSERT':
                outcome = _apply_insert(tenant_id, entity, payload)
            elif op == 'UPDATE':
                outcome = _apply_update(
                    tenant_id, entity, payload, entity_pk,
                    _parse_occurred_at(mutation.get('occurred_at')), force,
                )
            elif op == 'DELETE':
                outcome = _apply_delete(tenant_id, entity, entity_pk, payload)
            else:
                results.append({
                    'local_uuid': local_uuid, 'status': 'rejected',
                    'server_pk': None,
                    'message': f'Opération inconnue : {op}.',
                })
                continue

            if outcome['status'] == 'applied':
                # Journal + clé d'idempotence dans la MÊME transaction que
                # l'application de la mutation (pas de rejeu partiel).
                db.session.add(SyncAppliedKey(
                    tenant_id=tenant_id,
                    idempotency_key=idempotency_key,
                    entity=entity,
                    server_pk=outcome.get('server_pk'),
                ))
                _log_central(
                    tenant_id, mutation, outcome.get('server_pk'), device_id
                )
            results.append({'local_uuid': local_uuid, **outcome})

        db.session.commit()
        return {'results': results}, 200


@ns.route('/pull')
class ReplicationPull(Resource):
    @jwt_required()
    def get(self):
        """Renvoie les révisions du journal central postérieures au curseur."""
        tenant_id = _tenant_id_from_request()
        if tenant_id is None:
            return {'message': 'Tenant introuvable pour cet utilisateur.'}, 403

        since_revision = request.args.get('since_revision', 0, type=int) or 0
        entities_filter = request.args.get('entities', '')
        entities_list = [
            e.strip() for e in entities_filter.split(',') if e.strip()
        ]

        query = SyncCentralLog.query.filter(
            SyncCentralLog.tenant_id == tenant_id,
            SyncCentralLog.revision > since_revision,
        )
        if entities_list:
            query = query.filter(SyncCentralLog.entity.in_(entities_list))

        logs = query.order_by(SyncCentralLog.revision.asc()).all()
        max_revision = (
            max(log.revision for log in logs) if logs else since_revision
        )

        changes = [{
            'entity': log.entity,
            'entity_pk': log.entity_pk,
            'op': log.op,
            'payload': log.payload,
            'revision': log.revision,
            'source_device_id': log.source_device_id,
        } for log in logs]

        return {'revision': max_revision, 'changes': changes}, 200


@ns.route('/status')
class ReplicationStatus(Resource):
    @jwt_required()
    def get(self):
        """Dernière révision connue (tenant) et heure serveur."""
        tenant_id = _tenant_id_from_request()
        if tenant_id is None:
            return {'message': 'Tenant introuvable pour cet utilisateur.'}, 403
        max_rev = db.session.query(
            db.func.max(SyncCentralLog.revision)
        ).filter(
            SyncCentralLog.tenant_id == tenant_id
        ).scalar() or 0
        return {
            'last_revision': max_rev,
            'server_time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        }, 200
