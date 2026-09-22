# web/backend/tests/test_replication_maintenance.py
# Entretien de la réplication hors-ligne : enregistrement des endpoints du
# poste, purge de l'outbox (risque n°3) et contrôle de dérive d'horloge
# (risque n°2). Messages et commentaires en français.
from datetime import datetime, timedelta

from app import db
from app.models.sync_replica import SyncOutbox

# Chemins attendus par le client desktop (shared/components/SyncStatus et
# écran de conflits). Un namespace oublié dans create_app() ne casse pas les
# tests métier mais rend ces écrans inutilisables (404) : d'où ce garde-fou.
LOCAL_SYNC_RULES = (
    '/api/v1/sync/local-status',
    '/api/v1/sync/conflicts',
    '/api/v1/sync/conflicts/<int:conflict_id>/resolve',
)


def test_local_sync_endpoints_are_registered(app):
    """Les endpoints d'état et de conflits du poste doivent être routés."""
    rules = {str(rule) for rule in app.url_map.iter_rules()}
    for path in LOCAL_SYNC_RULES:
        assert path in rules, f"Route manquante : {path}"


def _make_outbox(tenant_id, suffix, status, days_ago=0):
    created = datetime.utcnow() - timedelta(days=days_ago)
    return SyncOutbox(
        tenant_id=tenant_id,
        device_id='test-device',
        entity='produit',
        op='INSERT',
        payload={'nom': f'Produit {suffix}'},
        local_uuid=f'uuid-{suffix}',
        idempotency_key=f'test-device:uuid-{suffix}',
        status=status,
        synced_at=created if status == 'sent' else None,
        created_at=created,
    )


class TestPurgeOutbox:
    """Risque n°3 : la table d'outbox ne doit pas croître sans borne."""

    def test_purge_removes_only_old_sent_entries(self, app, replication_tenant):
        from app.services.replication.maintenance import purge_sent_outbox

        with app.app_context():
            db.session.add_all([
                _make_outbox(replication_tenant, 'ancien', 'sent', 40),
                _make_outbox(replication_tenant, 'recent', 'sent', 0),
                _make_outbox(replication_tenant, 'en-attente', 'pending', 90),
            ])
            db.session.commit()

            deleted = purge_sent_outbox(app, retention_days=30)
            assert deleted == 1

            restants = {e.local_uuid for e in SyncOutbox.query.all()}
            # Une mutation non encore répliquée ne doit JAMAIS être purgée,
            # même très ancienne : la saisie du poste serait perdue.
            assert 'uuid-en-attente' in restants
            assert 'uuid-recent' in restants
            assert 'uuid-ancien' not in restants

    def test_purge_honours_retention_config(self, app, replication_tenant,
                                            monkeypatch):
        from app.services.replication.maintenance import purge_sent_outbox

        with app.app_context():
            db.session.add(_make_outbox(
                replication_tenant, 'trois-jours', 'sent', 3
            ))
            db.session.commit()

            # Rétention par défaut (30 j) : rien à purger.
            assert purge_sent_outbox(app) == 0

            # Rétention ramenée à 1 jour : l'entrée doit disparaître.
            monkeypatch.setitem(app.config, 'SYNC_OUTBOX_RETENTION_DAYS', 1)
            assert purge_sent_outbox(app) == 1

    def test_purge_never_raises_without_sent_entries(self, app,
                                                     replication_tenant):
        from app.services.replication.maintenance import purge_sent_outbox

        with app.app_context():
            db.session.add(_make_outbox(
                replication_tenant, 'seul-pending', 'pending', 0
            ))
            db.session.commit()
            assert purge_sent_outbox(app) == 0


class TestClockDrift:
    """Risque n°2 : une horloge de poste erronée tranche mal les conflits."""

    def test_returns_none_when_central_unreachable(self, app, monkeypatch):
        from app.services.replication.maintenance import check_clock_drift
        import requests

        monkeypatch.setitem(app.config, 'REPLICATION_URL', 'http://central.test')

        def _raise(*args, **kwargs):
            raise requests.ConnectionError('Serveur central injoignable')

        monkeypatch.setattr(requests, 'get', _raise)
        assert check_clock_drift(app) is None

    def test_detects_drift_beyond_tolerance(self, app, monkeypatch):
        from app.services.replication.maintenance import check_clock_drift
        import requests

        monkeypatch.setitem(app.config, 'REPLICATION_URL', 'http://central.test')
        monkeypatch.setitem(app.config, 'SYNC_CLOCK_DRIFT_TOLERANCE_S', 300)

        # Le central annonce une heure vieille de 10 minutes : le poste est
        # donc « en avance » — écart bien au-delà de la tolérance.
        server_time = (
            datetime.utcnow() - timedelta(minutes=10)
        ).strftime('%Y-%m-%dT%H:%M:%SZ')

        class FakeResponse:
            ok = True

            def json(self):
                return {'last_revision': 1, 'server_time': server_time}

        monkeypatch.setattr(
            requests, 'get', lambda *args, **kwargs: FakeResponse()
        )

        drift = check_clock_drift(app)
        assert drift is not None
        assert drift > 500
        assert app.extensions['clock_drift_seconds'] == drift

    def test_no_drift_when_clocks_agree(self, app, monkeypatch):
        from app.services.replication.maintenance import check_clock_drift
        import requests

        monkeypatch.setitem(app.config, 'REPLICATION_URL', 'http://central.test')

        class FakeResponse:
            ok = True

            def json(self):
                return {
                    'last_revision': 1,
                    'server_time': datetime.utcnow().strftime(
                        '%Y-%m-%dT%H:%M:%SZ'
                    ),
                }

        monkeypatch.setattr(
            requests, 'get', lambda *args, **kwargs: FakeResponse()
        )

        drift = check_clock_drift(app)
        assert drift is not None
        assert abs(drift) < 60

