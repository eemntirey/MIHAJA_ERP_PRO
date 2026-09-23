# web/backend/app/services/replication/outbox.py
# Capture automatique des mutations locales dans la SyncOutbox.
# Enregistré UNIQUEMENT sur le backend embarqué (FLASK_ENV=local-embedded),
# jamais sur le serveur central.
import os
import uuid

from sqlalchemy import event

from app.models.sync_replica import SyncOutbox
from app.services.replication import SUPPRESS_OUTBOX_KEY

_REGISTERED = set()


def default_entity_map():
    """Carte {nom_de_classe_modele: nom_entite} dérivée du registre répliqué.

    Une seule source de vérité (services/replication/entities.py) : toute
    entité que le central sait appliquer est capturée localement, et
    inversement (pas d'entrée d'outbox impossible à pousser).
    """
    from app.services.replication.entities import ENTITY_REGISTRY
    return {
        definition['model'].__name__: name
        for name, definition in ENTITY_REGISTRY.items()
    }


def _bind_matches(bind, local_db_path):
    """Vrai si la session écrit bien dans la base SQLite locale embarquée."""
    if local_db_path is None or bind is None:
        return True
    url = getattr(bind, 'url', None)
    if url is None:
        return True
    if url.get_backend_name() != 'sqlite':
        return False
    database = url.database
    if not database:
        return True
    return os.path.normcase(os.path.abspath(database)) == os.path.normcase(
        os.path.abspath(local_db_path)
    )


def _configured_device_id():
    """Identifiant de poste issu de la config de l'application.

    Le listener `after_flush` s'exécute hors requête (scheduler, script) :
    `session.info['device_id']` n'est donc pas toujours posé. Sans ce repli,
    TOUTES les entrées d'outbox portaient `default-device`, alors que le push
    envoie le vrai `X-Device-Id` — la clé d'idempotence et la traçabilité du
    journal central divergeaient du poste réel.
    """
    try:
        from flask import current_app
        return current_app.config.get('REPLICATION_DEVICE_ID') or 'default-device'
    except Exception:
        return 'default-device'


def register_outbox_listeners(db, entity_map=None, local_db_path=None):
    """Enregistre le listener `after_flush` de capture des mutations.

    :param db: instance SQLAlchemy
    :param entity_map: dict {nom_classe_modele: nom_entite_outbox}
        (par défaut : registre des entités répliquées)
    :param local_db_path: chemin du fichier SQLite local. Si fourni, seules
        les sessions écrivant dans CE fichier sont capturées : indispensable
        lorsque deux applications (central de test + poste) vivent dans le
        même processus.
    """
    global _REGISTERED
    if _REGISTERED:
        return
    entity_map = entity_map if entity_map is not None else default_entity_map()
    if not entity_map:
        return

    @event.listens_for(db.session, 'after_flush')
    def _capture_after_flush(session, flush_context):
        # Le pull applique ce que le central nous envoie : ne pas le
        # recapturer, sinon chaque changement reçu repart aussitôt.
        if session.info.get(SUPPRESS_OUTBOX_KEY):
            return
        try:
            bind = session.get_bind()
        except Exception:
            bind = None
        if not _bind_matches(bind, local_db_path):
            return

        device_id = session.info.get('device_id') or _configured_device_id()
        for obj in list(session.new) + list(session.dirty) + list(session.deleted):
            entity_name = entity_map.get(type(obj).__name__)
            if entity_name is None:
                continue
            tenant_id = getattr(obj, 'tenant_id', None)
            if tenant_id is None:
                continue

            if obj in session.deleted:
                op = 'DELETE'
                # Pour un DELETE, l'objet n'a plus d'attributs fiables : on ne
                # conserve que la clé primaire (le central applique une
                # suppression logique).
                payload = {'id': getattr(obj, 'id', None)}
            elif obj in session.new:
                op = 'INSERT'
                payload = obj.to_dict() if hasattr(obj, 'to_dict') else {}
            elif session.is_modified(obj):
                op = 'UPDATE'
                payload = obj.to_dict() if hasattr(obj, 'to_dict') else {}
            else:
                continue

            local_uuid = str(uuid.uuid4())
            session.add(SyncOutbox(
                tenant_id=tenant_id,
                device_id=device_id,
                entity=entity_name,
                op=op,
                payload=payload,
                local_uuid=local_uuid,
                entity_pk=getattr(obj, 'id', None),
                idempotency_key=f'{device_id}:{local_uuid}',
            ))

    _REGISTERED = True
