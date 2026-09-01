import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from app.security.plans import check_tenant_limit, get_tenant_limit, count_active_tenants_for_plan


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


def _login(client, username, password):
    r = client.post('/api/v1/auth/login', json={'username': username, 'password': password})
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestTenantLimitGratuit:
    def test_create_first_gratuit_tenant_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        r = client.post('/api/v1/tenants/', headers=headers,
                        json={'nom': 'Gratuit A', 'slug': 'gratuit-a', 'plan': 'gratuit',
                              'admin_email': 'admin@gratuit-a.mg', 'admin_password': 'Admin123!'})
        assert r.status_code == 201, r.get_json()

    def test_create_second_gratuit_tenant_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        r1 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Gratuit A', 'slug': 'gratuit-a', 'plan': 'gratuit',
                               'admin_email': 'admin@gratuit-a.mg', 'admin_password': 'Admin123!'})
        assert r1.status_code == 201

        r2 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Gratuit B', 'slug': 'gratuit-b', 'plan': 'gratuit',
                               'admin_email': 'admin@gratuit-b.mg', 'admin_password': 'Admin123!'})
        assert r2.status_code == 201, r2.get_json()


class TestTenantLimitStarter:
    def test_create_first_starter_tenant_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        r = client.post('/api/v1/tenants/', headers=headers,
                        json={'nom': 'Starter A', 'slug': 'starter-a', 'plan': 'starter',
                              'admin_email': 'admin@starter-a.mg', 'admin_password': 'Admin123!'})
        assert r.status_code == 201, r.get_json()

    def test_create_second_starter_tenant_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        r1 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Starter A', 'slug': 'starter-a', 'plan': 'starter',
                               'admin_email': 'admin@starter-a.mg', 'admin_password': 'Admin123!'})
        assert r1.status_code == 201

        r2 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Starter B', 'slug': 'starter-b', 'plan': 'starter',
                               'admin_email': 'admin@starter-b.mg', 'admin_password': 'Admin123!'})
        assert r2.status_code == 201, r2.get_json()


class TestTenantLimitPro:
    def test_create_up_to_two_pro_tenants_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        r1 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Pro A', 'slug': 'pro-a', 'plan': 'pro',
                               'admin_email': 'admin@pro-a.mg', 'admin_password': 'Admin123!'})
        assert r1.status_code == 201, r1.get_json()

        r2 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Pro B', 'slug': 'pro-b', 'plan': 'pro',
                               'admin_email': 'admin@pro-b.mg', 'admin_password': 'Admin123!'})
        assert r2.status_code == 201, r2.get_json()

    def test_create_third_pro_tenant_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        client.post('/api/v1/tenants/', headers=headers,
                    json={'nom': 'Pro A', 'slug': 'pro-a', 'plan': 'pro',
                          'admin_email': 'admin@pro-a.mg', 'admin_password': 'Admin123!'})
        client.post('/api/v1/tenants/', headers=headers,
                    json={'nom': 'Pro B', 'slug': 'pro-b', 'plan': 'pro',
                          'admin_email': 'admin@pro-b.mg', 'admin_password': 'Admin123!'})

        r3 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Pro C', 'slug': 'pro-c', 'plan': 'pro',
                               'admin_email': 'admin@pro-c.mg', 'admin_password': 'Admin123!'})
        assert r3.status_code == 201, r3.get_json()


class TestTenantLimitEnterprise:
    def test_create_up_to_five_enterprise_tenants_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        for i in range(5):
            r = client.post('/api/v1/tenants/', headers=headers,
                            json={'nom': f'Ent {i}', 'slug': f'ent-{i}', 'plan': 'enterprise',
                                  'admin_email': f'admin@ent-{i}.mg', 'admin_password': 'Admin123!'})
            assert r.status_code == 201, r.get_json()

    def test_create_sixth_enterprise_tenant_allowed(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        for i in range(5):
            client.post('/api/v1/tenants/', headers=headers,
                        json={'nom': f'Ent {i}', 'slug': f'ent-{i}', 'plan': 'enterprise',
                              'admin_email': f'admin@ent-{i}.mg', 'admin_password': 'Admin123!'})

        r6 = client.post('/api/v1/tenants/', headers=headers,
                         json={'nom': 'Ent 5', 'slug': 'ent-5', 'plan': 'enterprise',
                               'admin_email': 'admin@ent-5.mg', 'admin_password': 'Admin123!'})
        assert r6.status_code == 201, r6.get_json()


class TestTenantLimitPlanIsolation:
    def test_gratuit_limit_does_not_block_starter(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        r_gratuit = client.post('/api/v1/tenants/', headers=headers,
                                json={'nom': 'Gratuit A', 'slug': 'gratuit-a', 'plan': 'gratuit',
                                      'admin_email': 'admin@gratuit-a.mg', 'admin_password': 'Admin123!'})
        assert r_gratuit.status_code == 201

        r_starter = client.post('/api/v1/tenants/', headers=headers,
                                json={'nom': 'Starter A', 'slug': 'starter-a', 'plan': 'starter',
                                      'admin_email': 'admin@starter-a.mg', 'admin_password': 'Admin123!'})
        assert r_starter.status_code == 201, r_starter.get_json()

    def test_pro_limit_does_not_block_enterprise(self, app):
        client = app.test_client()
        _make_super_admin()
        headers = _login(client, 'super', 'Super123!')

        for i in range(2):
            client.post('/api/v1/tenants/', headers=headers,
                        json={'nom': f'Pro {i}', 'slug': f'pro-{i}', 'plan': 'pro',
                              'admin_email': f'admin@pro-{i}.mg', 'admin_password': 'Admin123!'})

        r_ent = client.post('/api/v1/tenants/', headers=headers,
                            json={'nom': 'Ent 0', 'slug': 'ent-0', 'plan': 'enterprise',
                                  'admin_email': 'admin@ent-0.mg', 'admin_password': 'Admin123!'})
        assert r_ent.status_code == 201, r_ent.get_json()


class TestCompanyRegistrationTenantLimit:
    def test_company_registration_allows_multiple_gratuit_tenants(self, app):
        client = app.test_client()

        r1 = client.post('/api/v1/auth/register', json={
            'profile_type': 'company',
            'nom_entreprise': 'Gratuit A',
            'slug': 'gratuit-a',
            'plan': 'gratuit',
            'email': 'a@test.mg',
            'username': 'usera',
            'password': 'Pass123!',
            'nom': 'A',
            'prenom': 'User',
        })
        assert r1.status_code == 201, r1.get_json()

        r2 = client.post('/api/v1/auth/register', json={
            'profile_type': 'company',
            'nom_entreprise': 'Gratuit B',
            'slug': 'gratuit-b',
            'plan': 'gratuit',
            'email': 'b@test.mg',
            'username': 'userb',
            'password': 'Pass123!',
            'nom': 'B',
            'prenom': 'User',
        })
        assert r2.status_code == 201, r2.get_json()

    def test_company_registration_rejects_duplicate_domaine(self, app):
        client = app.test_client()

        r1 = client.post('/api/v1/auth/register', json={
            'profile_type': 'company',
            'nom_entreprise': 'Gratuit A',
            'slug': 'gratuit-a',
            'domaine': 'example.com',
            'plan': 'gratuit',
            'email': 'a@test.mg',
            'username': 'usera',
            'password': 'Pass123!',
            'nom': 'A',
            'prenom': 'User',
        })
        assert r1.status_code == 201, r1.get_json()

        r2 = client.post('/api/v1/auth/register', json={
            'profile_type': 'company',
            'nom_entreprise': 'Gratuit B',
            'slug': 'gratuit-b',
            'domaine': 'example.com',
            'plan': 'gratuit',
            'email': 'b@test.mg',
            'username': 'userb',
            'password': 'Pass123!',
            'nom': 'B',
            'prenom': 'User',
        })
        assert r2.status_code == 409, r2.get_json()
        assert 'existe deja' in r2.get_json()['message']


class TestTenantLimitHelpers:
    def test_get_tenant_limit(self):
        from app.security.plans import get_tenant_limit
        # max_tenants est illimité (-1) : un SaaS multi-locataire doit pouvoir
        # heberger autant de tenants que necessaire par plan.
        assert get_tenant_limit('gratuit') == -1
        assert get_tenant_limit('starter') == -1
        assert get_tenant_limit('pro') == -1
        assert get_tenant_limit('enterprise') == -1
        assert get_tenant_limit('unknown') == -1

    def test_count_active_tenants_for_plan(self, app):
        tenant = Tenant(nom='T', slug='t', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(tenant)
        db.session.commit()

        assert count_active_tenants_for_plan('pro') == 1
        assert count_active_tenants_for_plan('gratuit') == 0

    def test_check_tenant_limit(self):
        allowed, msg = check_tenant_limit('gratuit')
        assert allowed is True
        assert msg is None
