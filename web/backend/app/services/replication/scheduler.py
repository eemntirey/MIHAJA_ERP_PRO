# web/backend/app/services/replication/scheduler.py
# Planificateur de réplication : thread daemon avec backoff exponentiel.
# Tous les messages et commentaires sont en français.
import logging
import threading
import time

logger = logging.getLogger(__name__)

BACKOFFS = [30, 60, 120, 300, 600, 1800]

# Entretien (purge de l'outbox) : au plus une fois par heure, quel que soit
# l'intervalle de réplication.
_MAINTENANCE_PERIOD_S = 3600


def start_replication_scheduler(app, interval_s=60):
    def _loop():
        backoff_idx = 0
        last_maintenance = 0.0
        while True:
            try:
                from app.services.replication.push import push_pending
                from app.services.replication.pull import pull_changes

                push_pending(app)
                pull_changes(app)

                # Risque n°2 : alerter si l'horloge du poste dérive, sinon les
                # conflits LWW sont tranchés avec une date fausse.
                try:
                    from app.services.replication.maintenance import (
                        check_clock_drift,
                    )
                    check_clock_drift(app)
                except Exception:
                    logger.debug(
                        "Contrôle de dérive d'horloge impossible.", exc_info=True
                    )

                # Risque n°3 : l'outbox `sent` ne doit pas croître sans borne.
                now = time.monotonic()
                if now - last_maintenance >= _MAINTENANCE_PERIOD_S:
                    last_maintenance = now
                    try:
                        from app.services.replication.maintenance import (
                            purge_sent_outbox,
                        )
                        purge_sent_outbox(app)
                    except Exception:
                        logger.debug(
                            "Purge de l'outbox impossible.", exc_info=True
                        )

                backoff_idx = 0
                wait = interval_s
            except Exception:
                wait = BACKOFFS[min(backoff_idx, len(BACKOFFS) - 1)]
                backoff_idx += 1
            time.sleep(wait)

    t = threading.Thread(target=_loop, daemon=True, name='replication-scheduler')
    t.start()
    return t
