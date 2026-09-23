# web/backend/run_local.py
# Entrée du backend embarqué (packagé par PyInstaller pour le desktop).
import os
from app import create_app
from app.services.local_bootstrap import ensure_local_db_ready
from app.services.replication.scheduler import start_replication_scheduler

app = create_app()
ensure_local_db_ready(app)
start_replication_scheduler(app)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('LOCAL_API_PORT', '5000')))
