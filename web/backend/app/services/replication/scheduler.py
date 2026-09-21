import threading
import time

BACKOFFS = [30, 60, 120, 300, 600, 1800]


def start_replication_scheduler(app, interval_s=60):
    def _loop():
        backoff_idx = 0
        while True:
            try:
                from app.services.replication.push import push_pending
                from app.services.replication.pull import pull_changes
                push_pending(app)
                pull_changes(app)
                backoff_idx = 0
                wait = interval_s
            except Exception:
                wait = BACKOFFS[min(backoff_idx, len(BACKOFFS) - 1)]
                backoff_idx += 1
            time.sleep(wait)

    t = threading.Thread(target=_loop, daemon=True, name='replication-scheduler')
    t.start()
    return t
