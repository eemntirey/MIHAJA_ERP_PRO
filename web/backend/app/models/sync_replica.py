# web/backend/app/models/sync_replica.py
# Modèles de réplication pour le mode hors-ligne desktop (backend embarqué).
#
# - SyncOutbox      : mutations locales en attente d'envoi vers le central.
# - SyncCursor      : curseur de révision par entité pour le pull central -> local.
# - SyncConflict    : conflits LWW enregistrés pour revue manuelle ultérieure.
# - SyncAppliedKey  : clés d'idempotence déjà appliquées (côté central).
# - SyncState       : état de réplication local (ligne unique id=1).
#
# Note : le listener global (app/security/tenant.py) filtre toute entité
# possédant un attribut `tenant_id`. Tous les modèles ci-dessous conservent
# `tenant_id` conformément aux conventions multi-tenant du projet.
from datetime import datetime

from app import db


class SyncOutbox(db.Model):
    """File d'attente des mutations locales vers le central."""
    __tablename__ = 'sync_outbox'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    entity = db.Column(db.String(64), nullable=False, index=True)
    entity_pk = db.Column(db.Integer, nullable=True)
    local_uuid = db.Column(db.String(36), nullable=False, unique=True)
    op = db.Column(db.String(10), nullable=False)  # INSERT | UPDATE | DELETE
    payload = db.Column(db.JSON, nullable=True)
    idempotency_key = db.Column(db.String(64), nullable=False, unique=True)
    status = db.Column(db.String(10), nullable=False, default='pending', index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    synced_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def record(cls, tenant_id, device_id, entity, op, payload, local_uuid,
               entity_pk=None):
        """Enregistre une mutation locale. Idempotent par `local_uuid`."""
        existing = cls.query.filter_by(local_uuid=local_uuid).first()
        if existing:
            return existing
        entry = cls(
            tenant_id=tenant_id,
            device_id=device_id,
            entity=entity,
            entity_pk=entity_pk,
            op=op,
            payload=payload,
            local_uuid=local_uuid,
            idempotency_key=f'{device_id}:{local_uuid}',
        )
        db.session.add(entry)
        db.session.commit()
        return entry


class SyncCursor(db.Model):
    """Curseur de révision par entité (local -> central)."""
    __tablename__ = 'sync_cursors'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    entity = db.Column(db.String(64), nullable=False, index=True)
    last_pulled_revision = db.Column(db.BigInteger, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint(
            'tenant_id', 'device_id', 'entity',
            name='uq_sync_cursor_tenant_device_entity',
        ),
    )

    @classmethod
    def upsert(cls, tenant_id, device_id, entity, last_pulled_revision):
        """Avance le curseur (jamais en arrière : max des deux valeurs)."""
        cur = cls.query.filter_by(
            tenant_id=tenant_id, device_id=device_id, entity=entity
        ).first()
        if cur is None:
            cur = cls(
                tenant_id=tenant_id,
                device_id=device_id,
                entity=entity,
                last_pulled_revision=last_pulled_revision,
            )
            db.session.add(cur)
        else:
            cur.last_pulled_revision = max(
                cur.last_pulled_revision or 0,
                last_pulled_revision or 0,
            )
        db.session.commit()
        return cur


class SyncConflict(db.Model):
    """Conflit LWW enregistré pour revue manuelle ultérieure."""
    __tablename__ = 'sync_conflicts'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    device_id = db.Column(db.String(64), nullable=False)
    entity = db.Column(db.String(64), nullable=False)
    entity_pk = db.Column(db.Integer, nullable=True)
    local_payload = db.Column(db.JSON, nullable=True)
    remote_payload = db.Column(db.JSON, nullable=True)
    resolved_as = db.Column(
        db.String(20), nullable=False, default='pending_review'
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SyncAppliedKey(db.Model):
    """Clés d'idempotence déjà appliquées (côté central)."""
    __tablename__ = 'sync_applied_keys'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    idempotency_key = db.Column(db.String(64), nullable=False, unique=True)
    entity = db.Column(db.String(64), nullable=False)
    server_pk = db.Column(db.Integer, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SyncState(db.Model):
    """État de réplication local, une ligne par tenant."""
    __tablename__ = 'sync_state'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    online = db.Column(db.Boolean, nullable=False, default=False)
    pending_count = db.Column(db.Integer, nullable=False, default=0)
    last_push_at = db.Column(db.DateTime, nullable=True)
    last_pull_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', name='uq_sync_state_tenant'),
    )

    @classmethod
    def get_or_create(cls, tenant_id):
        """Retourne ou crée la ligne d'état du tenant donné."""
        state = cls.query.filter_by(tenant_id=tenant_id).first()
        if state is None:
            state = cls(tenant_id=tenant_id)
            db.session.add(state)
            db.session.commit()
        return state
