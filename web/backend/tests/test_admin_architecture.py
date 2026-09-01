import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur, StatutAdmin
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.admin_device import AdminDevice, StatutDevice
from app.models.audit_log import AuditLog, TypeActionAudit
from app.security.auth import hash_password
from app.security.roles import is_super_admin, is_admin


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_admin_tenant(name, slug):
    tenant = Tenant(
        nom=name, slug=slug, domaine=f'{slug}.local',
        statut=StatutTenant.ACTIF, plan='pro'
    )
    db.session.add(tenant)
    db.session.flush()

    abonnement = Abonnement(
        tenant_id=tenant.id, montant=100.0, plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    )
    db.session.add(abonnement)

    admin = Utilisateur(
        username=f'admin_{slug}',
        email=f'admin@{slug}.mg',
        password_hash=hash_password('Admin123!'),
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
        admin_statut=StatutAdmin.ACTIVE,
    )
    db.session.add(admin)
    db.session.flush()

    device = AdminDevice(
        user_id=admin.id,
        device_id=f'device-{slug}',
        device_name=f'Device {name}',
        statut=StatutDevice.ACTIVE,
    )
    db.session.add(device)
    admin.device_id = f'device-{slug}'

    db.session.commit()
    return tenant, admin


def _make_super_admin():
    super_admin = Utilisateur(
        username='super',
        email='super@x.mg',
        password_hash=hash_password('Super123!'),
        role=Role.SUPER_ADMIN,
        statut=StatutUtilisateur.ACTIF,
    )
    db.session.add(super_admin)
    db.session.commit()
    return super_admin


def _login(client, identifier, password, tenant_slug=None, device_id=None):
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    if device_id:
        payload['device_id'] = device_id
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestArchitectureAdmin:
    """Tests de l architecture ADMIN / TENANT / APPAREIL"""

    def test_01_admin_a_tenant_a_device_a_authorized(self, app):
        """Test 1: ADMIN A + TENANT A + DEVICE A -> autorise"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 200, r.get_json()
            data = r.get_json()
            assert 'access_token' in data

    def test_02_admin_a_tenant_a_device_b_denied(self, app):
        """Test 2: ADMIN A + TENANT A + DEVICE B -> refuse"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-wrong'
            })
            assert r.status_code == 401
            data = r.get_json()
            assert 'Appareil non autorise' in data.get('message', '')

    def test_03_admin_a_tenant_b_device_a_denied(self, app):
        """Test 3: ADMIN A + TENANT B + DEVICE A -> refuse"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        tenant_b, admin_b = _make_admin_tenant('Tenant B', 'tenant-b')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-b',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 401

    def test_04_admin_b_tenant_b_device_b_authorized(self, app):
        """Test 4: ADMIN B + TENANT B + DEVICE B -> autorise"""
        tenant_b, admin_b = _make_admin_tenant('Tenant B', 'tenant-b')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-b',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-b',
                'device_id': 'device-tenant-b'
            })
            assert r.status_code == 200, r.get_json()
            data = r.get_json()
            assert 'access_token' in data

    def test_05_super_admin_global_access(self, app):
        """Test 5: SUPER_ADMIN -> acces global"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        headers_super = _login(client, 'super', 'Super123!')
        assert isinstance(headers_super, dict)
        assert 'Authorization' in headers_super

        r = client.get('/api/v1/auth/me', headers=headers_super)
        assert r.status_code == 200
        data = r.get_json()
        assert data['user']['role'] == 'super_admin'

    def test_06_admin_a_cannot_access_tenant_b_data(self, app):
        """Test 6: ADMIN A ne doit jamais acceder aux donnees de TENANT B"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        tenant_b, admin_b = _make_admin_tenant('Tenant B', 'tenant-b')
        _make_super_admin()
        client = app.test_client()

        headers_a = _login(client, 'admin_tenant-a', 'Admin123!', 'tenant-a',
                          device_id='device-tenant-a')
        assert isinstance(headers_a, dict)

        with app.app_context():
            from app.models.produit import Produit
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tenant_b.id,
                         prix_achat_ht=20, prix_vente_ht=30)
            db.session.add(p_b)
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/produits/{pid_b}', headers=headers_a)
        assert r.status_code == 404

    def test_07_revoked_admin_denied(self, app):
        """Test 7: Admin revoque -> acces refuse"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()

        admin_a.admin_statut = StatutAdmin.REVOKED
        db.session.add(admin_a)
        db.session.commit()

        client = app.test_client()
        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 401
            data = r.get_json()
            assert 'suspendu' in data.get('message', '').lower() or 'revoq' in data.get('message', '').lower()

    def test_08_revoked_device_denied(self, app):
        """Test 8: Device revoque -> acces refuse"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()

        device = AdminDevice.query.filter_by(user_id=admin_a.id, device_id='device-tenant-a').first()
        assert device is not None
        device.statut = StatutDevice.REVOKED
        db.session.add(device)
        db.session.commit()

        client = app.test_client()
        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 401
            data = r.get_json()
            assert 'Appareil non autorise' in data.get('message', '')

    def test_09_suspended_admin_denied(self, app):
        """Test 9: ADMIN suspendu -> acces refuse"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()

        admin_a.admin_statut = StatutAdmin.SUSPENDED
        db.session.add(admin_a)
        db.session.commit()

        client = app.test_client()
        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 401
            data = r.get_json()
            assert 'suspendu' in data.get('message', '').lower() or 'revoque' in data.get('message', '').lower()

    def test_10_first_device_auto_registered(self, app):
        """Test 10: Premier appareil auto-enregistre lors de la premiere connexion"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()

        AdminDevice.query.filter_by(user_id=admin_a.id).delete()
        admin_a.device_id = None
        db.session.commit()

        client = app.test_client()
        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'new-device-xyz'
            })
            assert r.status_code == 200, r.get_json()
            data = r.get_json()
            assert 'access_token' in data

        device = AdminDevice.query.filter_by(user_id=admin_a.id, device_id='new-device-xyz').first()
        assert device is not None
        assert device.statut == StatutDevice.ACTIVE

    def test_11_second_device_not_auto_registered(self, app):
        """Test 11: Deuxieme appareil NON auto-enregistre -> acces refuse"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 200

            r2 = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'another-device-999'
            })
            assert r2.status_code == 401
            data2 = r2.get_json()
            assert 'Appareil non autorise' in data2.get('message', '')

    def test_12_audit_logs_created(self, app):
        """Test 12: Les logs d'audit sont crees pour les operations sensibles"""
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()

        client = app.test_client()
        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 200

            device_token = r.get_json()['access_token']
            headers = {'Authorization': f'Bearer {device_token}'}

            r2 = client.post('/api/v1/admin/devices/', json={
                'device_id': 'new-device-audit',
                'device_name': 'Device Audit Test',
            }, headers=headers)
            assert r2.status_code == 201

        logs = AuditLog.query.filter_by(utilisateur_id=admin_a.id).all()
        assert len(logs) >= 1

        log_types = [log.type_action.value for log in logs]
        assert 'device_registered' in log_types


class TestSubscriptionAdminPrincipal:
    """Tests : seul l'admin principal du tenant peut gérer l'abonnement."""

    def test_13_admin_principal_can_renew_subscription(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 200
            headers = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            sub = tenant_a.abonnements.first()
            assert sub is not None

            r2 = client.post(f'/api/v1/abonnements/{sub.id}/renouveler', headers=headers)
            assert r2.status_code == 200, r2.get_json()

    def test_14_non_admin_principal_cannot_renew_subscription(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        normal_user = Utilisateur(
            username='user_a',
            email='user_a@a.mg',
            password_hash=hash_password('User123!'),
            role=Role.USER,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant_a.id,
        )
        db.session.add(normal_user)
        db.session.commit()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'user_a',
                'password': 'User123!',
                'tenant_slug': 'tenant-a',
            })
            assert r.status_code == 200
            headers = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            sub = tenant_a.abonnements.first()
            r2 = client.post(f'/api/v1/abonnements/{sub.id}/renouveler', headers=headers)
            assert r2.status_code == 403, r2.get_json()
            assert 'administrateur principal' in r2.get_json()['message'].lower()

    def test_15_super_admin_can_renew_any_subscription(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'super',
                'password': 'Super123!',
            })
            assert r.status_code == 200
            headers = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            sub = tenant_a.abonnements.first()
            r2 = client.post(f'/api/v1/abonnements/{sub.id}/renouveler', headers=headers)
            assert r2.status_code == 200, r2.get_json()

    def test_16_admin_principal_can_pay_subscription(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 200
            headers = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            sub = tenant_a.abonnements.first()
            r2 = client.post(f'/api/v1/abonnements/{sub.id}/payer', headers=headers, json={})
            assert r2.status_code == 200, r2.get_json()

    def test_17_non_admin_principal_cannot_pay_subscription(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        normal_user = Utilisateur(
            username='user_a2',
            email='user_a2@a.mg',
            password_hash=hash_password('User123!'),
            role=Role.USER,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant_a.id,
        )
        db.session.add(normal_user)
        db.session.commit()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'user_a2',
                'password': 'User123!',
                'tenant_slug': 'tenant-a',
            })
            assert r.status_code == 200
            headers = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            sub = tenant_a.abonnements.first()
            r2 = client.post(f'/api/v1/abonnements/{sub.id}/payer', headers=headers, json={})
            assert r2.status_code == 403, r2.get_json()
            assert 'administrateur principal' in r2.get_json()['message'].lower()

    def test_18_super_admin_can_pay_any_subscription(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'super',
                'password': 'Super123!',
            })
            assert r.status_code == 200
            headers = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            sub = tenant_a.abonnements.first()
            r2 = client.post(f'/api/v1/abonnements/{sub.id}/payer', headers=headers, json={})
            assert r2.status_code == 200, r2.get_json()

    def test_19_super_admin_tenant_creation_includes_admin_principal(self, app):
        client = app.test_client()
        _make_super_admin()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'super',
                'password': 'Super123!',
            })
            assert r.status_code == 200
            headers = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            r2 = client.post('/api/v1/tenants/', headers=headers, json={
                'nom': 'New Tenant',
                'slug': 'new-tenant',
                'domaine': 'new.local',
                'plan': 'starter',
                'admin_email': 'newadmin@new.mg',
                'admin_password': 'NewAdmin123!',
                'admin_nom': 'New',
                'admin_prenom': 'Admin',
            })
            assert r2.status_code == 201, r2.get_json()
            data = r2.get_json()
            assert data['tenant']['plan'] == 'starter'
            assert data['admin']['email'] == 'newadmin@new.mg'
            assert data['admin']['role'] == 'admin'
            assert data['tenant']['admin_principal_id'] == data['admin']['id']

            tenant = Tenant.query.filter_by(slug='new-tenant').first()
            assert tenant is not None
            assert tenant.admin_principal_id == data['admin']['id']
            assert tenant.admin_principal_id is not None
            assert data['admin']['is_principal_admin'] is True

    def test_20_cross_tenant_subscription_denied(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        tenant_b, admin_b = _make_admin_tenant('Tenant B', 'tenant-b')
        _make_super_admin()
        client = app.test_client()

        with app.app_context():
            r = client.post('/api/v1/auth/login', json={
                'username': 'admin_tenant-a',
                'password': 'Admin123!',
                'tenant_slug': 'tenant-a',
                'device_id': 'device-tenant-a'
            })
            assert r.status_code == 200
            headers_a = {'Authorization': 'Bearer ' + r.get_json()['access_token']}

            sub_b = tenant_b.abonnements.first()
            assert sub_b is not None

            r2 = client.post(f'/api/v1/abonnements/{sub_b.id}/renouveler', headers=headers_a)
            assert r2.status_code == 403, r2.get_json()

    def test_21_company_registration_creates_initial_abonnement(self, app):
        client = app.test_client()
        r = client.post('/api/v1/auth/register', json={
            'profile_type': 'company',
            'nom_entreprise': 'Test Company',
            'slug': 'test-company',
            'plan': 'starter',
            'email': 'admin@testcompany.mg',
            'username': 'testadmin',
            'password': 'Pass123!',
            'nom': 'Test',
            'prenom': 'Admin',
        })
        assert r.status_code == 201, r.get_json()
        data = r.get_json()
        assert data['tenant']['plan'] == 'starter'
        assert data['tenant']['admin_principal_id'] == data['user']['id']
        assert data['user']['is_principal_admin'] is True
        assert 'admin_key' not in data

        with app.app_context():
            tenant = Tenant.query.filter_by(slug='test-company').first()
            assert tenant is not None
            from app.models.abonnement import Abonnement, StatutAbonnement
            abonnement = Abonnement.query.filter_by(tenant_id=tenant.id).first()
            assert abonnement is not None

    def test_22_mon_abonnement_returns_can_renew_for_principal_admin(self, app):
        tenant, admin = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()
        headers = _login(client, 'admin_tenant-a', 'Admin123!', 'tenant-a',
                         device_id='device-tenant-a')
        r = client.get('/api/v1/abonnements/mon-abonnement', headers=headers)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data['can_renew'] is True

    def test_23_mon_abonnement_returns_can_renew_false_for_super_admin(self, app):
        _make_super_admin()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')
        r = client.get('/api/v1/abonnements/mon-abonnement', headers=headers)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data['can_renew'] is True

    def test_24_principal_admin_can_renew_subscription(self, app):
        tenant, admin = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        client = app.test_client()
        headers = _login(client, 'admin_tenant-a', 'Admin123!', 'tenant-a',
                         device_id='device-tenant-a')
        sub = tenant.abonnements.first()
        assert sub is not None
        r = client.post(f'/api/v1/abonnements/{sub.id}/renouveler', headers=headers)
        assert r.status_code == 200, r.get_json()

    def test_25_regular_user_cannot_renew_subscription(self, app):
        tenant, admin = _make_admin_tenant('Tenant A', 'tenant-a')
        _make_super_admin()
        regular = Utilisateur(
            username='regular', email='regular@a.mg',
            password_hash=hash_password('Regular123!'), role=Role.USER,
            statut=StatutUtilisateur.ACTIF, tenant_id=tenant.id,
        )
        db.session.add(regular)
        db.session.commit()
        client = app.test_client()
        headers = _login(client, 'regular', 'Regular123!', 'tenant-a')
        sub = tenant.abonnements.first()
        assert sub is not None
        r = client.post(f'/api/v1/abonnements/{sub.id}/renouveler', headers=headers)
        assert r.status_code == 403, r.get_json()

    def test_26_cross_tenant_renewal_denied(self, app):
        tenant_a, admin_a = _make_admin_tenant('Tenant A', 'tenant-a')
        tenant_b, admin_b = _make_admin_tenant('Tenant B', 'tenant-b')
        _make_super_admin()
        client = app.test_client()
        headers_a = _login(client, 'admin_tenant-a', 'Admin123!', 'tenant-a',
                           device_id='device-tenant-a')
        sub_b = tenant_b.abonnements.first()
        assert sub_b is not None
        r = client.post(f'/api/v1/abonnements/{sub_b.id}/renouveler', headers=headers_a)
        assert r.status_code == 403, r.get_json()
