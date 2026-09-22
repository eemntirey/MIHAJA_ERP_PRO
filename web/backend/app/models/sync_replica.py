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


class SyncCentralLog(db.Model):
    """Journal central des révisions (pull côté serveur)."""
    __tablename__ = 'sync_central_log'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    entity = db.Column(db.String(64), nullable=False, index=True)
    entity_pk = db.Column(db.Integer, nullable=False)
    op = db.Column(db.String(10), nullable=False)  # INSERT | UPDATE | DELETE
    payload = db.Column(db.JSON, nullable=True)
    revision = db.Column(db.BigInteger, nullable=False, index=True, default=0)
    # Poste d'origine de la mutation : le pull local ignore ses propres
    # mutations (sinon la ligne déjà présente localement serait recréée).
    source_device_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SyncLocalMapping(db.Model):
    """Correspondance clé primaire locale (SQLite) <-> PK du serveur central.

    Risque n°6 du plan : les ids locaux diffèrent des ids centraux. Toute
    référence croisée (UPDATE/DELETE d'un enregistrement déjà poussé) doit
    passer par cette table, alimentée par le push (server_pk renvoyé) et par
    le pull (change appliqué localement).
    """
    __tablename__ = 'sync_local_mappings'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)
    entity = db.Column(db.String(64), nullable=False, index=True)
    local_pk = db.Column(db.Integer, nullable=False, index=True)
    remote_pk = db.Column(db.Integer, nullable=False, index=True)
    local_uuid = db.Column(db.String(36), nullable=True)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'entity', 'local_pk',
                            name='uq_sync_mapping_tenant_entity_local'),
        db.UniqueConstraint('tenant_id', 'entity', 'remote_pk',
                            name='uq_sync_mapping_tenant_entity_remote'),
    )

    @classmethod
    def upsert(cls, tenant_id, entity, local_pk, remote_pk, local_uuid=None):
        """Enregistre (ou met à jour) la correspondance pour une entité."""
        row = cls.query.filter_by(
            tenant_id=tenant_id, entity=entity, local_pk=local_pk
        ).first()
        if row is None:
            row = cls(
                tenant_id=tenant_id, entity=entity, local_pk=local_pk,
                remote_pk=remote_pk, local_uuid=local_uuid,
            )
            db.session.add(row)
        else:
            row.remote_pk = remote_pk
            if local_uuid:
                row.local_uuid = local_uuid
        return row

    @classmethod
    def remote_pk_for(cls, entity, local_pk):
        """PK central correspondant à un PK local (None si jamais poussé)."""
        row = cls.query.filter_by(entity=entity, local_pk=local_pk).first()
        return row.remote_pk if row else None

    @classmethod
    def local_pk_for(cls, entity, remote_pk):
        """PK local correspondant à un PK central (None si inconnu)."""
        row = cls.query.filter_by(entity=entity, remote_pk=remote_pk).first()
        return row.local_pk if row else None


class SyncState(db.Model):
    """État de réplication local (ligne unique id=1)."""
    __tablename__ = 'sync_state'

    id = db.Column(db.Integer, primary_key=True, default=1)
    online = db.Column(db.Boolean, nullable=False, default=False)
    pending_count = db.Column(db.Integer, nullable=False, default=0)
    last_push_at = db.Column(db.DateTime, nullable=True)
    last_pull_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    # Jeton JWT du central servant à authentifier le push/pull. Renseigné au
    # login en ligne (proxy vers le central) ; vide = poste jamais connecté
    # ou session expirée (il faut se reconnecter en ligne).
    service_token = db.Column(db.Text, nullable=True)

    @classmethod
    def get_or_create(cls):
        state = db.session.get(cls, 1)
        if state is None:
            state = cls(id=1)
            db.session.add(state)
            db.session.commit()
        return state

    @classmethod
    def set_service_token(cls, token):
        state = cls.get_or_create()
        state.service_token = token
        db.session.commit()
        return state

    @classmethod
    def get_service_token(cls):
        state = cls.get_or_create()
        return state.service_token

