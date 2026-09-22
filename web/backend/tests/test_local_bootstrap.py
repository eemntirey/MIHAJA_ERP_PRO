# web/backend/tests/test_local_bootstrap.py
# Bootstrap de la base locale + login hors-ligne du backend embarque.
# Commentaires et messages en francais.
import os

import pytest

from app.services.local_bootstrap import ensure_local_db_ready


def test_bootstrap_creates_tables_and_roles(local_app):
    """Le bootstrap cree le schema complet et les tables de replication."""
    ensure_local_db_ready(local_app)
    with local_app.app_context():
        from sqlalchemy import inspect
        from app import db
        tables = inspect(db.engine).get_table_names()
        assert 'utilisateurs' in tables
        assert 'sync_outbox' in tables
        assert 'sync_cursors' in tables
        assert 'sync_local_mappings' in tables


def test_bootstrap_is_idempotent(local_app):
    """Deux appels successifs ne doivent ni echouer ni dupliquer les roles."""
    from app.models.role_permission import RoleModel

    ensure_local_db_ready(local_app)
    with local_app.app_context():
        from app import db
        before = RoleModel.query.count()
    ensure_local_db_ready(local_app)
    with local_app.app_context():
        from app import db
        assert RoleModel.query.count() == before


def test_offline_login_uses_cached_credentials(
    local_embedded_app, cached_local_user, client
):
    """Central injoignable : le login passe par le cache scrypt local."""
    response = client.post('/api/v1/auth/login', json={
        'username': cached_local_user.username,
        'password': cached_local_user._raw_password,
    })
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body.get('offline') is True
    assert body['user']['username'] == cached_local_user.username
    assert body.get('access_token')


def test_offline_login_rejects_wrong_password(
    local_embedded_app, cached_local_user, client
):
    """Mot de passe errone hors-ligne : 401 avec message explicite."""
    response = client.post('/api/v1/auth/login', json={
        'username': cached_local_user.username,
        'password': 'mauvais-mot-de-passe',
    })
    assert response.status_code == 401
    assert 'hors-ligne' in response.get_json()['message'].lower()


def test_offline_login_rejects_unknown_user(local_embedded_app, client):
    """Compte jamais connecte sur ce poste : refus hors-ligne."""
    response = client.post('/api/v1/auth/login', json={
        'username': 'utilisateur-inconnu',
        'password': 'peu-importe',
    })
    assert response.status_code == 401
    assert 'hors-ligne' in response.get_json()['message'].lower()


def test_offline_login_initialises_replication_cursors(
    local_embedded_app, cached_local_user, client
):
    """Un login reussi initialise les curseurs (sinon le pull ne demarre pas)."""
    client.post('/api/v1/auth/login', json={
        'username': cached_local_user.username,
        'password': cached_local_user._raw_password,
    })
    with local_embedded_app.app_context():
        from app.models.sync_replica import SyncCursor
        from app.services.replication.entities import REPLICATED_ENTITIES
        entities = {c.entity for c in SyncCursor.query.all()}
        assert set(REPLICATED_ENTITIES).issubset(entities)


class _FakeResponse:
    """Reponse HTTP minimale (proxy de login vers le central)."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def test_online_login_mirrors_user_and_caches_credentials(
    local_embedded_app, client, monkeypatch
):
    """Central joignable : la ligne locale est creee et le mot de passe cache."""
    import requests

    from app import db
    from app.models.sync_replica import SyncState
    from app.models.utilisateur import Utilisateur

    username = 'utilisateur_central'
    central_login = {
        'access_token': 'jeton-central-abc',
        'refresh_token': 'refresh-central-abc',
        'user': {'username': username, 'email': 'central@test.local',
                 'role': 'admin'},
    }
    central_me = {
        'user': central_login['user'],
        'tenant': {'id': 4242, 'nom': 'Tenant Central', 'slug': 'tenant-central',
                   'domaine': 'central.local', 'plan': 'pro'},
    }

    def _post(url, **kwargs):
        assert url.endswith('/api/v1/auth/login')
        return _FakeResponse(central_login)

    def _get(url, **kwargs):
        assert url.endswith('/api/v1/auth/me')
        return _FakeResponse(central_me)

    monkeypatch.setattr(requests, 'post', _post)
    monkeypatch.setattr(requests, 'get', _get)

    response = client.post('/api/v1/auth/login', json={
        'username': username, 'password': 'motdepasse-central',
    })
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body.get('offline') is False
    assert body['access_token'] == 'jeton-central-abc'

    with local_embedded_app.app_context():
        user = Utilisateur.query.filter_by(username=username).first()
        assert user is not None
        assert user.local_password_hash
        assert user.local_password_hash.startswith('scrypt$')
        # Le mot de passe en clair n'est jamais stocke.
        assert 'motdepasse-central' not in user.local_password_hash
        assert SyncState.get_service_token() == 'jeton-central-abc'
        assert local_embedded_app.extensions['repl_token'] == 'jeton-central-abc'
