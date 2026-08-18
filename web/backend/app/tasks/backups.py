import os
import shutil
from datetime import datetime

def backup_database(config):
    db_path = config.get('DB_PATH', 'erp.db')
    backup_dir = config.get('BACKUP_DIR', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'backup_{timestamp}.db')
    shutil.copy2(db_path, backup_path)
    return {'status': 'success', 'path': backup_path, 'timestamp': timestamp}