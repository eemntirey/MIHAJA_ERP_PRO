"""Tests pour la validation JSON stricte du namespace desk."""
import json
import uuid
from datetime import datetime, timedelta

import pytest

from app import db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password


@pytest.fixture
def desk_user(app):
    with app.app_context():
        tenant = Tenant(
            nom='Desk Tenant',
            slug=f'desk-{uuid.uuid4().hex[:8]}',
            statut=StatutTenant.ACTIF,
            plan='starter',
        )
        db.session.add(tenant)
        db.session.flush()

        user = Utilisateur(
            username=f'desk-{uuid.uuid4().hex[:8]}',
            email=f'desk-{uuid.uuid4().hex[:8]}@example.com',
            password_hash=hash_password('password123'),
            role=Role.ADMIN,
            tenant_id=tenant.id,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(user)
        db.session.flush()

        abonnement = Abonnement(
            tenant_id=tenant.id,
            montant=15000.0,
            devise='MGA',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.EN_ATTENTE,
            plan='starter',
        )
        db.session.add(abonnement)
        db.session.commit()

        from flask_jwt_extended import create_access_token
        token = create_access_token(
            identity=user.id,
            additional_claims={
                'role': user.role.value,
                'tenant_id': tenant.id,
            },
        )
        return {
            'Authorization': f'Bearer {token}',
            'tenant_id': tenant.id,
        }


def test_invalid_json_returns_400(client, desk_user):
    r = client.post(
        '/api/v1/desk/favorites',
        data='{"path": ',
        content_type='application/json',
        headers=desk_user,
    )
    assert r.status_code == 400
    assert 'invalide' in r.get_json()['message'].lower()


def test_wrong_content_type_returns_415(client, desk_user):
    r = client.post(
        '/api/v1/desk/favorites',
        data='path=x',
        content_type='application/x-www-form-urlencoded',
        headers=desk_user,
    )
    assert r.status_code == 415


def test_empty_body_returns_400(client, desk_user):
    r = client.post(
        '/api/v1/desk/favorites',
        data='',
        content_type='application/json',
        headers=desk_user,
    )
    assert r.status_code == 400


def test_non_object_json_returns_400(client, desk_user):
    r = client.post(
        '/api/v1/desk/favorites',
        data=json.dumps(['not', 'an', 'object']),
        content_type='application/json',
        headers=desk_user,
    )
    assert r.status_code == 400


def test_valid_payload_still_works(client, desk_user):
    r = client.post(
        '/api/v1/desk/favorites',
        data=json.dumps({'path': '/dashboard', 'label': 'Accueil'}),
        content_type='application/json',
        headers=desk_user,
    )
    assert r.status_code == 200
    assert 'favorites' in r.get_json()


def test_filters_invalid_json_returns_400(client, desk_user):
    r = client.post(
        '/api/v1/desk/filters/ventes',
        data='not-json',
        content_type='application/json',
        headers=desk_user,
    )
    assert r.status_code == 400


def test_columns_invalid_json_returns_400(client, desk_user):
    r = client.post(
        '/api/v1/desk/columns/ventes',
        data='{',
        content_type='application/json',
        headers=desk_user,
    )
    assert r.status_code == 400


def test_sync_push_invalid_json_returns_400(client, desk_user):
    r = client.post(
        '/api/v1/desk/sync/push',
        data='{mutations: invalid}',
        content_type='application/json',
        headers=desk_user,
    )
    assert r.status_code == 400


class TestDeskRollback:
    """Garantit qu'une erreur de commit déclenche un rollback propre."""

    def test_upsert_favorite_rolls_back_on_commit_error(self, client, desk_user, monkeypatch):
        import app.api.v1.desk as desk_module
        original_commit = desk_module.db.session.commit

        def failing_commit():
            raise Exception("db down")

        monkeypatch.setattr(desk_module.db.session, 'commit', failing_commit)
        r = client.post(
            '/api/v1/desk/favorites',
            data=json.dumps({'path': '/test-rollback'}),
            content_type='application/json',
            headers=desk_user,
        )
        assert r.status_code == 500
        assert 'favori' in r.get_json()['message'].lower()
        monkeypatch.setattr(desk_module.db.session, 'commit', original_commit)

    def test_sync_push_rolls_back_on_commit_error(self, client, desk_user, monkeypatch):
        import app.api.v1.desk as desk_module
        original_commit = desk_module.db.session.commit

        def failing_commit():
            raise Exception("db down")

        monkeypatch.setattr(desk_module.db.session, 'commit', failing_commit)
        r = client.post(
            '/api/v1/desk/sync/push',
            data=json.dumps({'mutations': [{'entity': 'favorite', 'op': 'upsert', 'payload': {'path': '/sync-test'}}]}),
            content_type='application/json',
            headers=desk_user,
        )
        assert r.status_code == 500
        assert 'synchronisation' in r.get_json()['message'].lower()
        monkeypatch.setattr(desk_module.db.session, 'commit', original_commit)