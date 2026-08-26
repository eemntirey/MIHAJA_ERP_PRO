import pytest
from decimal import Decimal
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.client import Client
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password, create_access_token_for_user
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def tenant(app):
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro',
    )
    db.session.add(tenant)
    db.session.commit()
    
    abonnement = Abonnement(
        tenant_id=tenant.id,
        montant=79.0,
        plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
        methode_paiement='especes',
        reference_paiement='SUB-TEST-001',
        is_active=True,
        max_clients=2,
    )
    db.session.add(abonnement)
    db.session.commit()
    return tenant


@pytest.fixture
def utilisateur(app, tenant):
    user = Utilisateur(
        username='testuser',
        email='test@test.com',
        password_hash=hash_password('password123'),
        role=Role.ADMIN,
        tenant_id=tenant.id
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_headers(app, utilisateur):
    with app.app_context():
        token = create_access_token_for_user(utilisateur)
    return {'Authorization': f'Bearer {token}'}


class TestClientAPI:
    def test_create_client_success(self, app, auth_headers):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI001',
                    'nom': 'Dupont',
                    'prenom': 'Jean',
                    'email': 'jean.dupont@example.com',
                    'telephone': '+261 34 123 4567',
                    'type': 'particulier'
                },
                headers=auth_headers
            )
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 'CLI001'
        assert data['nom'] == 'Dupont'
        assert data['prenom'] == 'Jean'

    def test_create_client_missing_code(self, app, auth_headers):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'nom': 'Dupont',
                    'prenom': 'Jean'
                },
                headers=auth_headers
            )
        assert response.status_code == 400
        data = response.get_json()
        assert 'code' in data['message'].lower()

    def test_create_client_no_json(self, app, auth_headers):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                headers=auth_headers
            )
        assert response.status_code in (400, 415)

    def test_create_client_duplicate_code(self, app, auth_headers, tenant):
        with app.app_context():
            client = Client(
                code='CLI002',
                nom='Client Existant',
                tenant_id=tenant.id
            )
            db.session.add(client)
            db.session.commit()
            
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI002',
                    'nom': 'Nouveau',
                    'prenom': 'Client'
                },
                headers=auth_headers
            )
        assert response.status_code == 400
        data = response.get_json()
        assert 'CLI002' in data['message']

    def test_create_client_duplicate_email(self, app, auth_headers, tenant):
        with app.app_context():
            client = Client(
                code='CLI003',
                nom='Client Existant',
                email='dupont@example.com',
                tenant_id=tenant.id
            )
            db.session.add(client)
            db.session.commit()
            
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI004',
                    'nom': 'Nouveau',
                    'prenom': 'Client',
                    'email': 'dupont@example.com'
                },
                headers=auth_headers
            )
        assert response.status_code == 400
        data = response.get_json()
        assert 'email' in data['message'].lower() or 'existe' in data['message'].lower()

    def test_create_client_unauthorized(self, app):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                json={'code': 'CLI005'}
            )
        assert response.status_code == 401

    def test_create_client_plan_limit_reached(self, app, auth_headers, tenant):
        with app.app_context():
            for i in range(tenant.max_clients):
                client = Client(
                    code=f'CLI{i:03d}',
                    nom=f'Client {i}',
                    tenant_id=tenant.id
                )
                db.session.add(client)
            db.session.commit()
            
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI_OVERFLOW',
                    'nom': 'Nouveau'
                },
                headers=auth_headers
            )
        assert response.status_code == 403
        data = response.get_json()
        assert data['message'] == 'Limite de clients atteinte pour votre abonnement actuel.'

    def test_list_clients_tenant_isolation(self, app, tenant):
        with app.app_context():
            autre_tenant = Tenant(
                nom='Autre Tenant',
                slug='autre-tenant',
                domaine='autre.local',
                statut=StatutTenant.ACTIF,
                plan='pro'
            )
            db.session.add(autre_tenant)
            db.session.commit()
            
            abonnement_autre = Abonnement(
                tenant_id=autre_tenant.id,
                montant=79.0,
                plan='pro',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=30),
                statut=StatutAbonnement.ACTIF,
                methode_paiement='especes',
                reference_paiement='SUB-AUTRE-001',
                is_active=True
            )
            db.session.add(abonnement_autre)
            db.session.commit()
            
            user1 = Utilisateur(
                username='user1',
                email='user1@test.com',
                password_hash=hash_password('password'),
                role=Role.ADMIN,
                tenant_id=tenant.id
            )
            user2 = Utilisateur(
                username='user2',
                email='user2@test.com',
                password_hash=hash_password('password'),
                role=Role.ADMIN,
                tenant_id=autre_tenant.id
            )
            db.session.add_all([user1, user2])
            db.session.commit()
            
            token1 = create_access_token_for_user(user1)
            token2 = create_access_token_for_user(user2)
            
            client1 = Client(code='T1C1', nom='Client T1', tenant_id=tenant.id)
            client2 = Client(code='T1C2', nom='Client T1B', tenant_id=tenant.id)
            client3 = Client(code='T2C1', nom='Client T2', tenant_id=autre_tenant.id)
            db.session.add_all([client1, client2, client3])
            db.session.commit()
            
            response1 = app.test_client().get(
                '/api/v1/clients/',
                headers={'Authorization': f'Bearer {token1}'}
            )
            response2 = app.test_client().get(
                '/api/v1/clients/',
                headers={'Authorization': f'Bearer {token2}'}
            )
        
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert data1['total'] == 2
        codes1 = [c['code'] for c in data1['clients']]
        assert 'T1C1' in codes1
        assert 'T1C2' in codes1
        assert 'T2C1' not in codes1
        
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['total'] == 1
        codes2 = [c['code'] for c in data2['clients']]
        assert 'T2C1' in codes2
        assert 'T1C1' not in codes2
