# web/backend/app/services/replication/__init__.py
# Module de réplication pour le backend embarqué (mode hors-ligne).
#
# Helpers partagés par le push (local -> central), le pull (central -> local)
# et le planificateur.
from datetime import datetime

from flask import current_app

from app import db
from app.models.sync_replica import SyncState

# Délai maximal d'un appel HTTP vers le serveur central (secondes).
REPLICATION_TIMEOUT = 15
# Marqueur posé dans `session.info` pendant l'application d'un changement
# distant : l'outbox ne doit PAS recapturer ce que le central nous envoie.
SUPPRESS_OUTBOX_KEY = 'suppress_outbox'


def remote_base_url():
    """URL du serveur central (sans slash final)."""
    return (current_app.config.get('REPLICATION_URL') or '').rstrip('/')


def device_id():
    """Identifiant du poste de travail."""
    return current_app.config.get('REPLICATION_DEVICE_ID') or 'unknown-device'


def service_token():
    """Jeton JWT du central : mémoire vive d'abord, puis jeton persisté.

    Le jeton est mémorisé au login en ligne (cf. app/services/local_auth.py).
    Sans jeton, le central refuse la requête : le moteur marque alors l'état
    hors-ligne avec un message explicite plutôt que de boucler en silence.
    """
    token = current_app.extensions.get('repl_token')
    if token:
        return token
    try:
        token = SyncState.get_service_token()
    except Exception:
        token = None
    if token:
        current_app.extensions['repl_token'] = token
    return token


def auth_headers():
    """En-têtes d'authentification + identification du poste."""
    headers = {'X-Device-Id': device_id()}
    token = service_token()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def record_online_state(online=None, error=None, push_done=False,
                        pull_done=False):
    """Met à jour l'état de réplication exposé par /sync/local-status."""
    state = SyncState.get_or_create()
    if online is not None:
        state.online = bool(online)
    state.last_error = error
    if push_done:
        state.last_push_at = datetime.utcnow()
    if pull_done:
        state.last_pull_at = datetime.utcnow()
    from app.models.sync_replica import SyncOutbox
    state.pending_count = (
        SyncOutbox.query.filter(
            SyncOutbox.status.in_(['pending', 'failed'])
        ).count()
    )
    db.session.commit()
    return state

