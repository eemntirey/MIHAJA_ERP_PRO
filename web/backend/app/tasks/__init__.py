from .backups import backup_database
from .celery_app import celery
from .emails import send_email
from .reports import generate_daily_sales_report, generate_monthly_report, generate_stock_report

# `celery` est exporté pour que la CLI `celery -A app.tasks worker|beat`
# trouve l'application (Celery cherche un attribut `celery`, `app` ou
# `celery_app` dans le module cible).
__all__ = [
    'backup_database',
    'celery',
    'send_email',
    'generate_daily_sales_report',
    'generate_monthly_report',
    'generate_stock_report',
]

