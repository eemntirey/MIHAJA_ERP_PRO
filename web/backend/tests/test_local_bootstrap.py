# web/backend/tests/test_local_bootstrap.py
# Bootstrap de la base locale + login hors-ligne du backend embarque.
# Commentaires et messages en francais.
import os
import subprocess
import sys

import pytest

from app.services.local_bootstrap import ensure_local_db_ready


def test_bootstrap_uses_migrations_from_pyinstaller_bundle(monkeypatch, tmp_path):
    from app.services.local_bootstrap import _migrations_directory

    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)

    assert _migrations_directory() == str(tmp_path / 'migrations')


def test_local_embedded_allows_file_renderer_preflight(tmp_path):
    env = os.environ.copy()
    env.update({
        'FLASK_ENV': 'local-embedded',
        'LOCAL_DB_PATH': str(tmp_path / 'erp-local.db'),
        'REPLICATION_URL': 'https://central.test',
        'SECRET_KEY': 'test-secret',
        'JWT_SECRET_KEY': 'test-jwt-secret',
    })
    script = """
from app import create_app
app = create_app()
response = app.test_client().options(
    '/api/v1/auth/login',
    headers={
        'Origin': 'null',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type',
    },
)
assert response.headers.get('Access-Control-Allow-Origin') == 'null'
"""

    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


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


def test_repair_missing_columns_non_nullable_python_default(local_app):
    """Colonnes tombes d'une base deja stamped head : la reparation les remet.

    Pathologie de l'incident 2026-09-22 : base creee par create_all + stamp
    head, colonnes ajoutees ensuite aux modeles absentes du schema.
    upgrade() est no-op (deja a la tete) ; seul _repair_missing_columns peut
    agir. Ici produits.stock_min (default Python 0, pas de server_default) et
    produits.published (non-nullable, default Python True, pas de
    server_default) doivent etre repares, avec un defaut serveur aligne sur
    la migration — sinon SELECT echoue avec "no such column".
    """
    from sqlalchemy import inspect, text

    from app import db
    from app.services.local_bootstrap import (
        _repair_missing_columns, ensure_local_db_ready,
    )

    # Schema complet + Alembic stamped head (1re installation).
    ensure_local_db_ready(local_app)

    with local_app.app_context():
        # Simule la base ancienne : les colonnes manquent au schema.
        db.session.execute(text('ALTER TABLE produits DROP COLUMN stock_min'))
        db.session.execute(text('ALTER TABLE produits DROP COLUMN published'))
        db.session.commit()
        avant = {
            c['name'] for c in inspect(db.engine).get_columns('produits')
        }
        assert 'stock_min' not in avant and 'published' not in avant

        # Chemin de reparation (le 2e appel du bootstrap, upgrade no-op).
        _repair_missing_columns()

        cols = {
            c['name']: c
            for c in inspect(db.engine).get_columns('produits')
        }
        assert 'stock_min' in cols, (
            'produits.stock_min non repare (default Python ignore)'
        )
        assert 'published' in cols, (
            'produits.published non repare '
            '(non-nullable sans server_default)'
        )
        # Drift en trois voies : le defaut doit etre aligne migration/modele.
        assert cols['stock_min']['default'] is not None, (
            'produits.stock_min repare sans defaut serveur (drift migration)'
        )
        assert cols['published']['default'] is not None, (
            'produits.published NOT NULL repare sans defaut serveur'
        )
        # Symptome incident : SELECT echouait "no such column".
        db.session.execute(text(
            'SELECT reference, stock_min, published FROM produits'
        ))

        # Idempotence : un second passage n'ajoute ni ne casse rien.
        _repair_missing_columns()
        apres = {
            c['name'] for c in inspect(db.engine).get_columns('produits')
        }
        assert 'stock_min' in apres and 'published' in apres


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


def _central_subscription_payload(plan='pro', statut='actif'):
    """Reponse /abonnements/mon-abonnement du central (tenant 4242)."""
    return {
        'abonnement': {
            'tenant_id': 4242,
            'montant': 15000.0,
            'devise': 'MGA',
            'date_debut': '2026-09-24T05:37:59.101546',
            'date_fin': '2099-10-24T05:37:59.101550',
            'statut': statut,
            'methode_paiement': None,
            'reference_paiement': None,
            'plan': plan,
            'notes': None,
            'max_utilisateurs': 7,
            'max_produits': 200,
            'max_clients': 1000,
            'max_admins': 1,
            'max_employees': 6,
            'max_interns': 0,
            'max_tenants': -1,
            'modules': ['dashboard', 'produits', 'ventes'],
            'id': 1,
            'created_at': '2026-09-23T14:46:43.764222',
            'updated_at': '2026-09-24T05:37:59.102323',
            'is_active': True,
        },
        'can_renew': True,
        'tenant': {
            'id': 4242,
            'nom': 'Tenant Central',
            'plan': plan,
            'statut': 'actif',
            'max_utilisateurs': 7,
            'max_employees': 6,
            'users_count': 1,
            'employees_count': 0,
        },
        'is_free_plan': plan == 'gratuit',
        'pricing': None,
    }


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
        if url.endswith('/api/v1/auth/me'):
            return _FakeResponse(central_me)
        if url.endswith('/api/v1/abonnements/mon-abonnement'):
            return _FakeResponse(_central_subscription_payload())
        raise AssertionError(f'URL inattendue : {url}')

    monkeypatch.setattr(requests, 'post', _post)
    monkeypatch.setattr(requests, 'get', _get)

    response = client.post('/api/v1/auth/login', json={
        'username': username, 'password': 'motdepasse-central',
    })
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body.get('offline') is False
    # Jeton LOCAL : le jeton central ne sert qu'a la replication.
    assert body['access_token']
    assert body['access_token'] != 'jeton-central-abc'

    with local_embedded_app.app_context():
        user = Utilisateur.query.filter_by(username=username).first()
        assert user is not None
        assert user.local_password_hash
        assert user.local_password_hash.startswith('scrypt$')
        # Le mot de passe en clair n'est jamais stocke.
        assert 'motdepasse-central' not in user.local_password_hash
        assert SyncState.get_service_token() == 'jeton-central-abc'
        assert local_embedded_app.extensions['repl_token'] == 'jeton-central-abc'

        # L'abonnement du central est miroiré (sinon le desk affiche
        # « non abonne » alors que le tenant est abonne sur le web).
        from datetime import datetime

        from app.models.abonnement import Abonnement, StatutAbonnement
        from app.models.tenant import Tenant

        tenant = Tenant.query.filter_by(slug='tenant-central').first()
        assert tenant is not None
        assert tenant.plan == 'pro'
        actifs = [
            a for a in Abonnement.query.filter_by(tenant_id=tenant.id).all()
            if a.is_active
        ]
        assert len(actifs) == 1
        assert actifs[0].statut == StatutAbonnement.ACTIF
        assert actifs[0].plan == 'pro'
        assert actifs[0].date_fin > datetime.utcnow()
        assert actifs[0].modules == 'dashboard,produits,ventes'


def _add_pending_demande(slug, plan='gratuit'):
    """Demande locale jamais reglee (creee depuis le desk, ignoree du central).

    A appeler dans un contexte applicatif.
    """
    from datetime import datetime, timedelta

    from app import db
    from app.models.abonnement import Abonnement, StatutAbonnement
    from app.models.tenant import StatutTenant, Tenant

    tenant = Tenant.query.filter_by(slug=slug).first()
    if tenant is None:
        tenant = Tenant(
            nom='Poste Local', slug=slug, domaine='local.test',
            statut=StatutTenant.ACTIF, plan=plan,
        )
        db.session.add(tenant)
        db.session.flush()
    demande = Abonnement(
        tenant_id=tenant.id,
        date_debut=datetime.utcnow() - timedelta(days=1),
        date_fin=datetime.utcnow() + timedelta(days=30),
        plan=plan,
        statut=StatutAbonnement.EN_ATTENTE,
        montant=15000,
    )
    db.session.add(demande)
    db.session.commit()
    return tenant.id, demande.id


def test_login_replaces_pending_local_subscription_with_central_one(
    local_embedded_app, client, monkeypatch
):
    """Demande locale restee en attente : le miroir central la remplace.

    Reproduit le bug « non abonne » du desk : la ligne locale EN_ATTENTE
    (prioritaire dans /mon-abonnement) masquait l'abonnement actif du web.
    """
    import requests

    from app import db
    from app.models.abonnement import Abonnement, StatutAbonnement
    from app.models.tenant import Tenant

    with local_embedded_app.app_context():
        tenant_id, demande_id = _add_pending_demande('tenant-central')
        demande = db.session.get(Abonnement, demande_id)
        assert demande.statut == StatutAbonnement.EN_ATTENTE

    central_login = {
        'access_token': 'jeton-central-abc',
        'refresh_token': 'refresh-central-abc',
        'user': {'username': 'abonne_central',
                 'email': 'abonne@central.local', 'role': 'admin'},
    }
    central_me = {
        'user': central_login['user'],
        'tenant': {'id': 4242, 'nom': 'Tenant Central', 'slug': 'tenant-central',
                   'domaine': 'central.local', 'plan': 'pro'},
    }

    def _post(url, **kwargs):
        return _FakeResponse(central_login)

    def _get(url, **kwargs):
        if url.endswith('/api/v1/auth/me'):
            return _FakeResponse(central_me)
        if url.endswith('/api/v1/abonnements/mon-abonnement'):
            return _FakeResponse(_central_subscription_payload())
        raise AssertionError(f'URL inattendue : {url}')

    monkeypatch.setattr(requests, 'post', _post)
    monkeypatch.setattr(requests, 'get', _get)

    response = client.post('/api/v1/auth/login', json={
        'username': 'abonne_central', 'password': 'motdepasse-central',
    })
    assert response.status_code == 200, response.get_json()

    with local_embedded_app.app_context():
        demande = db.session.get(Abonnement, demande_id)
        assert demande.is_active is False
        assert demande.statut == StatutAbonnement.ANNULE
        actifs = [
            a for a in Abonnement.query.filter_by(tenant_id=tenant_id).all()
            if a.is_active
        ]
        assert len(actifs) == 1
        assert actifs[0].statut == StatutAbonnement.ACTIF
        assert actifs[0].plan == 'pro'
        assert db.session.get(Tenant, tenant_id).plan == 'pro'


def _local_login(client, user):
    """Ouvre une session locale (le central est injoignable : cache scrypt)."""
    response = client.post('/api/v1/auth/login', json={
        'username': user.username,
        'password': user._raw_password,
    })
    assert response.status_code == 200, response.get_json()
    assert response.get_json().get('offline') is True
    return response.get_json()['access_token']


def test_mon_abonnement_proxies_central_when_embedded(
    local_embedded_app, cached_local_user, client, monkeypatch
):
    """Mode embarque en ligne : /mon-abonnement renvoie l'abonnement du central."""
    import requests

    from app import db
    from app.models.abonnement import Abonnement, StatutAbonnement

    with local_embedded_app.app_context():
        # Isolation : les tests partagent la base de session.
        Abonnement.query.filter_by(
            tenant_id=cached_local_user.tenant_id,
        ).delete()
        tenant_id, _ = _add_pending_demande('test-tenant-rep')

    monkeypatch.setattr(
        requests, 'get',
        lambda url, **kwargs: _FakeResponse(_central_subscription_payload()),
    )
    token = _local_login(client, cached_local_user)

    response = client.get(
        '/api/v1/abonnements/mon-abonnement',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body['abonnement']['statut'] == 'actif'
    assert body['abonnement']['plan'] == 'pro'
    assert body['tenant']['plan'] == 'pro'

    with local_embedded_app.app_context():
        rows = Abonnement.query.filter_by(tenant_id=tenant_id).all()
        assert [a.statut for a in rows if a.is_active] == [StatutAbonnement.ACTIF]
        assert [a.statut for a in rows].count(StatutAbonnement.ANNULE) == 1


def test_mon_abonnement_falls_back_to_local_when_central_unreachable(
    local_embedded_app, cached_local_user, client
):
    """Central injoignable : la copie locale sert (poste hors-ligne)."""
    from datetime import datetime, timedelta

    from app import db
    from app.models.abonnement import Abonnement, StatutAbonnement

    with local_embedded_app.app_context():
        # Isolation : les tests partagent la base de session.
        Abonnement.query.filter_by(
            tenant_id=cached_local_user.tenant_id,
        ).delete()
        abonnement = Abonnement(
            tenant_id=cached_local_user.tenant_id,
            date_debut=datetime.utcnow() - timedelta(days=1),
            date_fin=datetime.utcnow() + timedelta(days=30),
            plan='gratuit',
            statut=StatutAbonnement.ACTIF,
            montant=0,
        )
        db.session.add(abonnement)
        db.session.commit()

    token = _local_login(client, cached_local_user)
    response = client.get(
        '/api/v1/abonnements/mon-abonnement',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body['abonnement']['statut'] == 'actif'
    assert body['abonnement']['plan'] == 'gratuit'
