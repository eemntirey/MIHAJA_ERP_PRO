# web/backend/tests/test_replication_engine.py
# Tests du moteur de réplication (push, pull, scheduler, conflits).
# Tous les messages et commentaires sont en français.
import uuid

# Fixtures nécessaires : local_app (FLASK_ENV=local-embedded + SQLite tmp),
# central_stub (serveur HTTP de test simulant /sync/replicate/push et pull).
# Ces fixtures sont définies dans conftest.py ou fournies par le test runner.


def test_push_marks_sent_on_success(local_app, seeded_outbox, central_stub_ok):
    from app.services.replication.push import push_pending
    report = push_pending(local_app)
    assert report['sent'] == 1
    assert seeded_outbox().status == 'sent'


def test_push_marks_failed_and_increments_attempts(local_app, seeded_outbox, central_stub_error):
    from app.services.replication.push import push_pending
    push_pending(local_app)
    e = seeded_outbox()
    assert e.status == 'failed'
    assert e.attempts == 1 and e.last_error


def test_pull_advances_cursor_and_applies_changes(local_app, central_stub_changes):
    from app.services.replication.pull import pull_changes
    report = pull_changes(local_app)
    assert report['applied'] >= 1
    from app.models.sync_replica import SyncCursor
    cur = SyncCursor.query.filter_by(entity='produit').one()
    assert cur.last_pulled_revision == central_stub_changes.revision


def test_conflict_recorded_on_conflict_response(local_app, seeded_outbox, central_stub_conflict):
    from app import db
    from app.services.replication.push import push_pending
    from app.models.sync_replica import SyncConflict
    with local_app.app_context():
        # Nettoyer les anciens conflits pour éviter la pollution inter-tests
        SyncConflict.query.delete()
        db.session.commit()
    push_pending(local_app)
    # Vérifier qu'au moins un conflit est présent (le moteur local crée SyncConflict)
    assert SyncConflict.query.count() >= 1
