# web/backend/app/tasks/celery_app.py
# Application Celery (B3) : le docker-compose lançait
# `celery -A app.tasks worker` alors qu'aucune instance Celery n'existait —
# la commande échouait. Ce module fournit l'instance attendue, le contexte
# applicatif Flask pour chaque tâche et la planification (beat).
#
# Démarrage :
#   celery -A app.tasks worker --loglevel=info   # exécution
#   celery -A app.tasks beat   --loglevel=info   # planification
#
# Sans Celery/Redis (dev), les mêmes traitements restent appelables
# directement : `python -c "from app.tasks.subscription_scheduler import
# run_subscription_reminders; print(run_subscription_reminders())"`.

import logging
import os

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# Fuseau de l'ERP (Madagascar, UTC+3). Les crontabs ci-dessous sont donc
# exprimés en heure locale ; enable_utc=True laisse Celery convertir en UTC.
TIMEZONE = os.getenv('CELERY_TIMEZONE', 'Indian/Antananarivo')


def _redis_url():
    """URL Redis du broker (et des résultats).

    REDIS_URL est fournie par docker-compose. Si elle est absente, l'URL est
    reconstruite depuis REDIS_HOST/REDIS_PORT/REDIS_PASSWORD (Redis managé).
    """
    url = os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')
    if url:
        return url
    host = os.getenv('REDIS_HOST', 'localhost')
    port = os.getenv('REDIS_PORT', '6379')
    password = os.getenv('REDIS_PASSWORD')
    credentials = f':{password}@' if password else ''
    return f'redis://{credentials}{host}:{port}/0'


celery = Celery(
    'mihaja_erp',
    broker=_redis_url(),
    backend=os.getenv('CELERY_RESULT_BACKEND') or _redis_url(),
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone=TIMEZONE,
    enable_utc=True,
    # Une tâche n'est acquittée qu'après exécution : pas de perte si le
    # worker redémarre (les traitements sont idempotents par construction :
    # rappels espacés de 3 jours, downgrade conditionné au statut courant).
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    worker_max_tasks_per_child=200,
    result_expires=3600,
)


class FlaskContextTask(celery.Task):
    """Tâche Celery s'exécutant dans un contexte applicatif Flask.

    Les traitements planifiés lisent/écrivent la base via ``db.session`` et
    sont soumis au filtre multi-tenant (app/security/tenant.py) : sans
    contexte applicatif, SQLAlchemy lève « Working outside of application
    context ». L'app Flask est créée une seule fois par process worker.
    """

    _flask_app = None

    @property
    def flask_app(self):
        app = self.__class__._flask_app
        if app is None:
            from app import create_app

            app = create_app()
            self.__class__._flask_app = app
        return app

    def __call__(self, *args, **kwargs):
        with self.flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = FlaskContextTask

# Planification quotidienne (heure locale Indian/Antananarivo).
celery.conf.beat_schedule = {
    'subscriptions-rappels': {
        'task': 'subscriptions.rappels',
        'schedule': crontab(hour=6, minute=0),
    },
    'subscriptions-expiration': {
        'task': 'subscriptions.expiration',
        'schedule': crontab(hour=6, minute=15),
    },
    'sauvegarde-base': {
        'task': 'backups.base',
        'schedule': crontab(hour=2, minute=0),
    },
}


@celery.task(name='subscriptions.rappels')
def task_subscription_reminders():
    """Rappels de fin de période de grâce (plan pro)."""
    from app.tasks.subscription_scheduler import run_subscription_reminders

    return run_subscription_reminders()


@celery.task(name='subscriptions.expiration')
def task_subscription_expiration():
    """Bascule au plan gratuit après expiration de la période de grâce."""
    from app.tasks.subscription_scheduler import run_subscription_expiration_check

    return run_subscription_expiration_check()


@celery.task(name='backups.base')
def task_database_backup():
    """Sauvegarde de la base — SQLite uniquement.

    En production PostgreSQL, la sauvegarde est assurée par ``pg_dump``
    (docs/technical/CARTE_MISE_EN_PRODUCTION.md, Phase 6) : la tâche le
    journalise explicitement plutôt que de produire une fausse sécurité.
    """
    database_url = os.getenv('DATABASE_URL', '')
    if not database_url.startswith('sqlite'):
        logger.info(
            'Sauvegarde applicative ignorée : base non SQLite '
            '(sauvegarde pg_dump externe requise).'
        )
        return {
            'status': 'skipped',
            'reason': 'postgresql: sauvegarde assuree par pg_dump (externe)',
        }

    from app.tasks.backups import backup_database

    config = {
        'DB_PATH': database_url.replace('sqlite:///', '') or os.getenv('DB_PATH', 'erp.db'),
        'BACKUP_DIR': os.getenv('BACKUP_DIR', 'backups'),
    }
    return backup_database(config)
