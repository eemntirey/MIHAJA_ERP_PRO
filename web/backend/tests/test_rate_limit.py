"""Tests du mécanisme de rate limiting fail-closed.

Couvre:
 - Redis disponible : compteur ZSET, plafond max_requests, fenêtre glissante.
 - Redis indisponible au démarrage ET après démarrage :
   * en TESTING/DEBUG : la requête passe.
   * en production : la requête est rejetée avec 503 (fail-closed).
"""
import pytest
from unittest.mock import MagicMock, patch


def _make_app(testing=False, debug=False, redis_url='redis://localhost:6379/0'):
    from app import create_app, db as _db
    app = create_app()
    app.config['TESTING'] = testing
    app.config['DEBUG'] = debug
    app.config['REDIS_URL'] = redis_url
    return app


@pytest.fixture
def app_testing():
    return _make_app(testing=True)


@pytest.fixture
def app_production():
    return _make_app(testing=False, debug=False)


def _patch_redis_with_client():
    fake = MagicMock()
    fake.ping.return_value = True

    class _Pipe:
        def zadd(self, *a, **kw): return self
        def zremrangebyscore(self, *a, **kw): return self
        def zcard(self, *a, **kw): return self
        def expire(self, *a, **kw): return self
        def execute(self): return (1, 1, 1, 1)

    fake.pipeline.return_value = _Pipe()
    return fake


class TestRateLimitFailClosed:
    def test_redis_available_lets_request_through_in_testing(self, app_testing):
        from app.security.rate_limit import rate_limit
        client = _patch_redis_with_client()

        with app_testing.test_request_context('/'):
            from app.security import rate_limit as rl_mod
            rl_mod._redis_client = client

            @rate_limit(max_requests=5, window_seconds=60)
            def view():
                return 'ok'

            with patch.object(rl_mod, '_get_redis_client', return_value=client):
                resp = view()
            assert resp == 'ok'

    def test_redis_unavailable_at_startup_fails_closed_in_production(self, app_production):
        from app.security.rate_limit import rate_limit
        from app.security import rate_limit as rl_mod

        with app_production.test_request_context('/'):
            @rate_limit(max_requests=5, window_seconds=60)
            def view():
                return 'ok'

            with patch.object(rl_mod, '_get_redis_client', return_value=None):
                resp, status = view()
            assert status == 503
            payload = resp.get_json()
            assert 'message' in payload

    def test_redis_unavailable_at_startup_passes_in_testing(self, app_testing):
        from app.security.rate_limit import rate_limit
        from app.security import rate_limit as rl_mod

        with app_testing.test_request_context('/'):
            @rate_limit(max_requests=5, window_seconds=60)
            def view():
                return 'ok'

            with patch.object(rl_mod, '_get_redis_client', return_value=None):
                resp = view()
            assert resp == 'ok'

    def test_redis_unavailable_after_startup_fails_closed_in_production(self, app_production):
        """Scénario: Redis OK au décorateur, mais l'opération pipeline
        lève une exception en cours d'exécution (réseau coupé)."""
        from app.security.rate_limit import rate_limit
        from app.security import rate_limit as rl_mod

        fake = MagicMock()
        fake.ping.return_value = True

        class _Pipe:
            def zadd(self, *a, **kw): return self
            def zremrangebyscore(self, *a, **kw): return self
            def zcard(self, *a, **kw): return self
            def expire(self, *a, **kw): return self
            def execute(self): raise RuntimeError('redis down')

        fake.pipeline.return_value = _Pipe()

        with app_production.test_request_context('/'):
            @rate_limit(max_requests=5, window_seconds=60)
            def view():
                return 'ok'

            with patch.object(rl_mod, '_get_redis_client', return_value=fake):
                resp, status = view()
            assert status == 503
            payload = resp.get_json()
            assert 'message' in payload

    def test_redis_unavailable_after_startup_passes_in_testing(self, app_testing):
        from app.security.rate_limit import rate_limit
        from app.security import rate_limit as rl_mod

        fake = MagicMock()
        fake.ping.return_value = True

        class _Pipe:
            def zadd(self, *a, **kw): return self
            def zremrangebyscore(self, *a, **kw): return self
            def zcard(self, *a, **kw): return self
            def expire(self, *a, **kw): return self
            def execute(self): raise RuntimeError('redis down')

        fake.pipeline.return_value = _Pipe()

        with app_testing.test_request_context('/'):
            @rate_limit(max_requests=5, window_seconds=60)
            def view():
                return 'ok'

            with patch.object(rl_mod, '_get_redis_client', return_value=fake):
                resp = view()
            assert resp == 'ok'

    def test_redis_available_blocks_over_quota(self, app_testing):
        from app.security.rate_limit import rate_limit
        from app.security import rate_limit as rl_mod

        fake = MagicMock()
        fake.ping.return_value = True

        class _Pipe:
            def __init__(self, count):
                self._count = count
            def zadd(self, *a, **kw): return self
            def zremrangebyscore(self, *a, **kw): return self
            def zcard(self, *a, **kw): return self
            def expire(self, *a, **kw): return self
            def execute(self): return (1, 1, self._count, 1)

        fake.pipeline.return_value = _Pipe(count=99)

        with app_testing.test_request_context('/'):
            @rate_limit(max_requests=5, window_seconds=60)
            def view():
                return 'ok'

            with patch.object(rl_mod, '_get_redis_client', return_value=fake):
                resp, status = view()
            assert status == 429