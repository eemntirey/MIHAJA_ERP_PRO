"""Tests de l'API notifications (/api/v1/notifications/).

Couvre :
- GET /notifications/ (liste, sync auto, limite 50)
- POST /notifications/ (creation, titre requis)
- GET /notifications/<id> (detail, 404)
- DELETE /notifications/<id> (soft-delete)
- PATCH /notifications/<id>/read (marquer lu)
- PATCH /notifications/read-all (marquer toutes lu)
- Isolation multi-tenant
- Auth requise
"""

import uuid
from datetime import datetime

import pytest

from app import db
from app.models.notification import Notification
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password, create_access_token_for_user


@pytest.fixture
def auth_data(app):
    """Tenant + admin + JWT headers.

    Yield puis cleanup : la connexion est rendue au pool avant que le test
    n'appelle le client HTTP, évitant les deadlocks entre connexions.
    """
    with app.app_context():
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'NotifAPI Tenant {suffix}',
            slug=f'notifapi-{suffix}',
            statut=StatutTenant.EN_ESSAI,
            plan='pro',
        )
        db.session.add(tenant)
        db.session.flush()

        user = Utilisateur(
            username=f'notifadmin-{suffix}',
            email=f'notifadmin-{suffix}@example.com',
            password_hash=hash_password('Password123!'),
            role=Role.ADMIN,
            tenant_id=tenant.id,
            statut=StatutUtilisateur.ACTIF,
            is_principal_admin=True,
        )
        db.session.add(user)
        db.session.commit()

        token = create_access_token_for_user(user, tenant)
        data = {
            'tenant_id': tenant.id,
            'user_id': user.id,
            'headers': {'Authorization': f'Bearer {token}'},
        }
        db.session.expire_all()
        db.session.remove()
        yield data


@pytest.fixture
def other_auth_data(app):
    """Deuxieme tenant pour les tests d'isolation."""
    with app.app_context():
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'OtherNotif Tenant {suffix}',
            slug=f'othernotif-{suffix}',
            statut=StatutTenant.EN_ESSAI,
            plan='pro',
        )
        db.session.add(tenant)
        db.session.flush()

        user = Utilisateur(
            username=f'othernotifadmin-{suffix}',
            email=f'othernotifadmin-{suffix}@example.com',
            password_hash=hash_password('Password123!'),
            role=Role.ADMIN,
            tenant_id=tenant.id,
            statut=StatutUtilisateur.ACTIF,
            is_principal_admin=True,
        )
        db.session.add(user)
        db.session.commit()

        token = create_access_token_for_user(user, tenant)
        data = {
            'tenant_id': tenant.id,
            'headers': {'Authorization': f'Bearer {token}'},
        }
        db.session.expire_all()
        db.session.remove()
        yield data


class TestListNotifications:

    def test_list_notifications(self, client, auth_data):
        headers = auth_data['headers']
        tenant_id = auth_data['tenant_id']

        with client.application.app_context():
            notif = Notification(
                title='Test Notif',
                message='Message test',
                type='info',
                tenant_id=tenant_id,
            )
            db.session.add(notif)
            db.session.commit()

        response = client.get('/api/v1/notifications/', headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
        assert any(n['title'] == 'Test Notif' for n in data)

    def test_list_notifications_limit_50(self, client, auth_data):
        headers = auth_data['headers']
        tenant_id = auth_data['tenant_id']

        with client.application.app_context():
            for i in range(55):
                notif = Notification(
                    title=f'Notif {i}',
                    type='info',
                    tenant_id=tenant_id,
                )
                db.session.add(notif)
            db.session.commit()

        response = client.get('/api/v1/notifications/', headers=headers)
        assert response.status_code == 200
        assert len(response.get_json()) <= 50


class TestCreateNotification:

    def test_create_notification(self, client, auth_data):
        headers = auth_data['headers']
        response = client.post(
            '/api/v1/notifications/',
            json={
                'title': 'Nouvelle notif',
                'message': 'Contenu',
                'type': 'stock_alert',
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == 'Nouvelle notif'
        assert data['type'] == 'stock_alert'

    def test_create_notification_missing_title(self, client, auth_data):
        headers = auth_data['headers']
        response = client.post(
            '/api/v1/notifications/',
            json={'message': 'Pas de titre'},
            headers=headers,
        )
        assert response.status_code in (400, 500)


class TestNotificationDetail:

    def test_get_notification_detail(self, client, auth_data):
        headers = auth_data['headers']
        tenant_id = auth_data['tenant_id']

        with client.application.app_context():
            notif = Notification(
                title='Detail Notif',
                type='info',
                tenant_id=tenant_id,
            )
            db.session.add(notif)
            db.session.commit()
            notif_id = notif.id

        response = client.get(f'/api/v1/notifications/{notif_id}', headers=headers)
        assert response.status_code == 200
        assert response.get_json()['title'] == 'Detail Notif'

    def test_get_notification_not_found(self, client, auth_data):
        headers = auth_data['headers']
        response = client.get('/api/v1/notifications/99999', headers=headers)
        assert response.status_code == 404


class TestDeleteNotification:

    def test_delete_notification(self, client, auth_data):
        headers = auth_data['headers']
        tenant_id = auth_data['tenant_id']

        with client.application.app_context():
            notif = Notification(
                title='A Supprimer',
                type='info',
                tenant_id=tenant_id,
            )
            db.session.add(notif)
            db.session.commit()
            notif_id = notif.id

        response = client.delete(f'/api/v1/notifications/{notif_id}', headers=headers)
        assert response.status_code == 200

        with client.application.app_context():
            notif_db = db.session.get(Notification, notif_id)
            assert notif_db.is_active is False


class TestMarkAsRead:

    def test_mark_as_read(self, client, auth_data):
        headers = auth_data['headers']
        tenant_id = auth_data['tenant_id']

        with client.application.app_context():
            notif = Notification(
                title='A lire',
                type='info',
                read=False,
                tenant_id=tenant_id,
            )
            db.session.add(notif)
            db.session.commit()
            notif_id = notif.id

        response = client.patch(
            f'/api/v1/notifications/{notif_id}/read',
            headers=headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['read'] is True
        assert data['read_at'] is not None

    def test_mark_all_as_read(self, client, auth_data):
        headers = auth_data['headers']
        tenant_id = auth_data['tenant_id']

        with client.application.app_context():
            for i in range(3):
                notif = Notification(
                    title=f'Non lue {i}',
                    type='info',
                    read=False,
                    tenant_id=tenant_id,
                )
                db.session.add(notif)
            db.session.commit()

        response = client.patch('/api/v1/notifications/read-all', headers=headers)
        assert response.status_code == 200

        with client.application.app_context():
            unread = Notification.query.filter_by(
                tenant_id=tenant_id,
                read=False,
                is_active=True,
            ).count()
            assert unread == 0


class TestTenantIsolation:

    def test_tenant_cannot_see_other_notifications(self, client, auth_data, other_auth_data):
        headers_a = auth_data['headers']
        headers_b = other_auth_data['headers']
        tenant_a = auth_data['tenant_id']
        tenant_b = other_auth_data['tenant_id']

        with client.application.app_context():
            notif_a = Notification(
                title='Secret A',
                type='info',
                tenant_id=tenant_a,
            )
            notif_b = Notification(
                title='Secret B',
                type='info',
                tenant_id=tenant_b,
            )
            db.session.add_all([notif_a, notif_b])
            db.session.commit()

        response_a = client.get('/api/v1/notifications/', headers=headers_a)
        titles_a = [n['title'] for n in response_a.get_json()]
        assert 'Secret A' in titles_a
        assert 'Secret B' not in titles_a

        response_b = client.get('/api/v1/notifications/', headers=headers_b)
        titles_b = [n['title'] for n in response_b.get_json()]
        assert 'Secret B' in titles_b
        assert 'Secret A' not in titles_b


class TestAuthRequired:

    def test_list_requires_auth(self, client):
        response = client.get('/api/v1/notifications/')
        assert response.status_code == 401

    def test_create_requires_auth(self, client):
        response = client.post(
            '/api/v1/notifications/',
            json={'title': 'Test', 'type': 'info'},
        )
        assert response.status_code == 401
