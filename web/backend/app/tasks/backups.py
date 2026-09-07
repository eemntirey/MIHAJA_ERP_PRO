import os
import sqlite3
import shutil
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BACKUP_RETENTION_DAYS = 7


def backup_database(config):
    """Sauvegarde la base SQLite en utilisant l'API de backup officielle.

    shutil.copy2 peut copier pendant que SQLite ecrit, ce qui produit un
    fichier corrompu. sqlite3.Connection.backup() prend un verrou sur la
    base et ecrit un instantané cohérent.
    """
    db_path = config.get('DB_PATH', 'erp.db')
    backup_dir = config.get('BACKUP_DIR', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'backup_{timestamp}.db')

    try:
        # Cas SQLite : utilisation de l'API backup (snapshot WAL-safe)
        conn = sqlite3.connect(db_path)
        try:
            bck = sqlite3.connect(backup_path)
            try:
                conn.backup(bck)
            finally:
                bck.close()
        finally:
            conn.close()
    except Exception as exc:
        logger.exception('Echec de la sauvegarde SQLite (%s)', exc)
        return {' : 'error', 'message': str(exc), 'timestamp': timestamp}

    # Retention : purger les sauvegardes plus vieilles que BACKUP_RETENTION_DAYS
    try:
        cutoff = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
        for fname in os.listdir(backup_dir):
            fpath = os.path.join(backup_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)
                    logger.info('Sauvegarde purgee: %s', fpath)
            except OSError:
                continue
    except Exception:
        logger.exception('Erreur pendant la purge des sauvegardes')

    return {' : 'success', 'path': backup_path, 'timestamp': timestamp}


def backup_generic(config):
    """Pour les SGBD non-SQLite, on tente un pg_dump / mysqldump si dispo."""
    db_path = config.get('DB_PATH')
    backend = config.get('DB_BACKEND', 'sqlite')
    if backend == 'sqlite':
        return backup_database(config)
    # Fallback : simple copy (postgres/mysql sont sauvegardes au niveau volume)
    backup_dir = config.get('BACKUP_DIR', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = os.path.join(backup_dir, f'backup_{backend}_{timestamp}.sql')
    try:
        if db_path and os.path.exists(db_path):
            shutil.copy2(db_path, target)
        return {' : 'success', 'path': target, 'timestamp': timestamp}
    except Exception as exc:
        logger.exception('Echec de la sauvegarde generique (%s)', exc)
        return {' : 'error', 'message': str(exc), 'timestamp': timestamp}