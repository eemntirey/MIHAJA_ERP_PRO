# web/backend/app/services/replication/maintenance.py
# Entretien du poste embarque : purge de l'outbox et controle d'horloge.
#
# Deux risques identifies dans le plan et non couverts par le moteur :
#  - risque n°3 : l'outbox `sent` grossit indefiniment (une semaine de ventes
#    reste confortable, mais la table ne doit pas croitre sans borne) ;
#  - risque n°2 : le LWW repose sur `occurred_at`/`updated_at`. Une horloge de
#    poste qui derive tranche les conflits a tort : on alerte des que l'ecart
#    avec l'heure du central depasse le seuil.
import logging
from datetime import datetime, timedelta, timezone

from app import db
from app.models.sync_replica import SyncOutbox

logger = logging.getLogger(__name__)

# Nombre de jours de conservation des mutations deja envoyees.
DEFAULT_OUTBOX_RETENTION_DAYS = 30
# Ecart maximal tolere entre l'horloge du poste et celle du central (secondes).
DEFAULT_CLOCK_DRIFT_TOLERANCE_S = 300


def purge_sent_outbox(app, retention_days=None):
    """Supprime les mutations deja acceptees par le central.

    Seules les entrees `status='sent'` sont purgees : une mutation `pending`,
    `failed` ou `conflict` porte encore une donnee non repliquee, la supprimer
    perdrait definitivement la saisie du poste.

    Retourne le nombre de lignes supprimees.
    """
    with app.app_context():
        if retention_days is None:
            retention_days = app.config.get(
                'SYNC_OUTBOX_RETENTION_DAYS', DEFAULT_OUTBOX_RETENTION_DAYS
            )
        try:
            retention_days = int(retention_days)
        except (TypeError, ValueError):
            retention_days = DEFAULT_OUTBOX_RETENTION_DAYS

        cutoff = datetime.utcnow() - timedelta(days=max(retention_days, 1))
        # Hors requete HTTP : le filtre tenant global ne s'applique pas, la
        # purge couvre donc bien toutes les lignes du poste.
        deleted = SyncOutbox.query.filter(
            SyncOutbox.status == 'sent',
            SyncOutbox.synced_at.isnot(None),
            SyncOutbox.synced_at < cutoff,
        ).delete(synchronize_session=False)
        db.session.commit()
        if deleted:
            logger.info(
                'Purge de l outbox de replication : %s mutation(s) envoyee(s) '
                'depuis plus de %s jour(s).', deleted, retention_days,
            )
        return deleted


def check_clock_drift(app, tolerance_s=None):
    """Compare l'heure du poste a celle du central (`/sync/replicate/status`).

    Retourne l'ecart en secondes (positif = poste en avance), ou None si le
    central est injoignable. L'ecart est expose via
    `app.extensions['clock_drift_seconds']` afin que /sync/local-status puisse
    l'afficher sans migration de schema.
    """
    from app.services.replication import auth_headers, remote_base_url

    with app.app_context():
        if tolerance_s is None:
            tolerance_s = app.config.get(
                'SYNC_CLOCK_DRIFT_TOLERANCE_S',
                DEFAULT_CLOCK_DRIFT_TOLERANCE_S,
            )
        try:
            tolerance_s = int(tolerance_s)
        except (TypeError, ValueError):
            tolerance_s = DEFAULT_CLOCK_DRIFT_TOLERANCE_S

        base = remote_base_url()
        if not base:
            return None

        import requests
        from app.services.replication import REPLICATION_TIMEOUT

        try:
            response = requests.get(
                f'{base}/api/v1/sync/replicate/status',
                headers=auth_headers(),
                timeout=REPLICATION_TIMEOUT,
            )
            if not response.ok:
                return None
            server_time = (response.json() or {}).get('server_time')
        except Exception:
            return None

        if not server_time:
            return None

        try:
            parsed = datetime.fromisoformat(str(server_time).replace('Z', '+00:00'))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

        drift = (datetime.utcnow() - parsed).total_seconds()
        app.extensions['clock_drift_seconds'] = drift

        if abs(drift) > tolerance_s:
            # Message en francais : l'operateur doit comprendre pourquoi deux
            # postes peuvent trancher un conflit differemment.
            logger.warning(
                "Derive d'horloge detectee sur ce poste : %.0f seconde(s) "
                "d'ecart avec le serveur central (tolerance %s s). Corrigez "
                "l'heure du poste : les conflits de replication sont "
                "arbitres par la date la plus recente.",
                drift, tolerance_s,
            )
        return drift
