import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.employe import Employe
from app.models.stagiaire import Stagiaire
from app.security.auth import hash_password
from app.security.plans import resolve_limits, resolve_modules, admin_limit


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


def _make_tenant_with_abonnement(plan='pro', max_admins=2, max_employees=3, max_interns=1, modules='rh,stocks,produits'):
    tenant = Tenant(
        nom='Tenant Test',
        slug='tenant-test',
        statut=StatutTenant.ACTIF,
        plan=plan,
    )
    db.session.add(tenant)
    db.session.flush()
    abonnement = Abonnement(
        tenant_id=tenant.id,
        montant=100.0,
        plan=plan,
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
        max_admins=max_admins,
        max_employees=max_employees,
        max_interns=max_interns,
        modules=modules,
    )
    db.session.add(abonnement)
    admin = Utilisateur(
        username='admin',
        email='admin@test.mg',
        password_hash=hash_password('Admin123!'),
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(admin)
    db.session.commit()
    return tenant, admin


def _login(client, username, password, tenant_slug=None):
    payload = {'username': username, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestAdminLimits:
    def test_cannot_create_more_admins_than_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_admins=1)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'admin2', 'email': 'admin2@test.mg',
                              'password': 'Pass123!', 'role': 'admin', 'statut': 'actif'})
        assert r.status_code == 403, r.get_json()
        assert 'administrateurs' in r.get_json()['message']

    def test_can_create_admin_under_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_admins=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'admin2', 'email': 'admin2@test.mg',
                              'password': 'Pass123!', 'role': 'admin', 'statut': 'actif'})
        assert r.status_code == 201, r.get_json()

    def test_super_admin_bypasses_admin_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_admins=1)
        super_admin = Utilisateur(
            username='super',
            email='super@x.mg',
            password_hash=hash_password('Super123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
        db.session.commit()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'admin2', 'email': 'admin2@test.mg',
                              'password': 'Pass123!', 'role': 'admin', 'statut': 'actif',
                              'tenant_id': tenant.id})
        assert r.status_code == 201, r.get_json()


class TestEmployeeLimits:
    def test_cannot_create_more_employees_than_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        Employe(tenant_id=tenant.id, matricule='EMP001', nom='A', prenom='B').save()
        Employe(tenant_id=tenant.id, matricule='EMP002', nom='C', prenom='D').save()

        r = client.post('/api/v1/employes', headers=headers,
                        json={'matricule': 'EMP003', 'nom': 'E', 'prenom': 'F'})
        assert r.status_code == 403, r.get_json()
        assert 'employés' in r.get_json()['message']

    def test_can_create_employee_under_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=3)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/employes', headers=headers,
                        json={'matricule': 'EMP001', 'nom': 'E', 'prenom': 'F'})
        assert r.status_code == 201, r.get_json()


class TestInternLimits:
    def test_cannot_create_more_interns_than_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_interns=1)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        Stagiaire(tenant_id=tenant.id, matricule='STG001', nom='A', prenom='B').save()

        r = client.post('/api/v1/stagiaires', headers=headers,
                        json={'matricule': 'STG002', 'nom': 'C', 'prenom': 'D'})
        assert r.status_code == 403, r.get_json()
        assert 'stagiaires' in r.get_json()['message']

    def test_can_create_intern_under_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_interns=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/stagiaires', headers=headers,
                        json={'matricule': 'STG001', 'nom': 'C', 'prenom': 'D'})
        assert r.status_code == 201, r.get_json()


class TestModuleRestrictions:
    def test_employee_routes_blocked_without_module(self, app):
        tenant, admin = _make_tenant_with_abonnement(modules='produits,clients')
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.get('/api/v1/employes', headers=headers)
        assert r.status_code == 403, r.get_json()
        assert 'rh' in r.get_json()['message']

    def test_employee_routes_allowed_with_module(self, app):
        tenant, admin = _make_tenant_with_abonnement(modules='produits,clients,rh')
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.get('/api/v1/employes', headers=headers)
        assert r.status_code == 200, r.get_json()

    def test_super_admin_bypasses_module_restriction(self, app):
        tenant, admin = _make_tenant_with_abonnement(modules='produits')
        super_admin = Utilisateur(
            username='super',
            email='super@x.mg',
            password_hash=hash_password('Super123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
        db.session.commit()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.get('/api/v1/employes', headers=headers)
        assert r.status_code == 200, r.get_json()


class TestMultiTenantIsolation:
    def test_employee_created_by_tenant_a_not_visible_by_tenant_b(self, app):
        tenant_a = Tenant(nom='Tenant A', slug='tenant-a', statut=StatutTenant.ACTIF, plan='pro')
        tenant_b = Tenant(nom='Tenant B', slug='tenant-b', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()
        for t in (tenant_a, tenant_b):
            db.session.add(Abonnement(
                tenant_id=t.id, montant=100.0, plan='pro',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=30),
                statut=StatutAbonnement.ACTIF,
                max_admins=5, max_employees=100, max_interns=20,
                modules='rh,stocks,produits',
            ))
        admin_a = Utilisateur(
            username='admin_a', email='admin_a@a.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tenant_a.id,
        )
        admin_b = Utilisateur(
            username='admin_b', email='admin_b@b.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tenant_b.id,
        )
        db.session.add_all([admin_a, admin_b])
        db.session.commit()

        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        r = client.post('/api/v1/employes', headers=headers_a,
                        json={'matricule': 'EMP001', 'nom': 'A', 'prenom': 'B'})
        assert r.status_code == 201, r.get_json()

        r_a = client.get('/api/v1/employes', headers=headers_a)
        assert r_a.status_code == 200
        assert len(r_a.get_json()['employes']) == 1

        r_b = client.get('/api/v1/employes', headers=headers_b)
        assert r_b.status_code == 200
        assert len(r_b.get_json()['employes']) == 0

    def test_user_creation_scoped_to_current_tenant(self, app):
        tenant_a = Tenant(nom='Tenant A', slug='tenant-a', statut=StatutTenant.ACTIF, plan='pro')
        tenant_b = Tenant(nom='Tenant B', slug='tenant-b', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()
        for t in (tenant_a, tenant_b):
            db.session.add(Abonnement(
                tenant_id=t.id, montant=100.0, plan='pro',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=30),
                statut=StatutAbonnement.ACTIF,
                max_admins=5, max_employees=100, max_interns=20,
                modules='rh,stocks,produits',
            ))
        admin_a = Utilisateur(
            username='admin_a', email='admin_a@a.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tenant_a.id,
        )
        db.session.add(admin_a)
        db.session.commit()

        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers_a,
                        json={'username': 'newuser', 'email': 'new@a.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == tenant_a.id


class TestEmployeeUserLimits:
    def test_cannot_create_more_employee_users_than_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp1', 'email': 'emp1@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp2', 'email': 'emp2@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp3', 'email': 'emp3@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 403, r.get_json()
        assert 'employés' in r.get_json()['message']

    def test_admin_can_still_list_users_when_employee_limit_reached(self, app):
        """La limite d'employes bloque la creation mais pas la consultation
        de la liste des utilisateurs (§34 : la limite s'affiche, la liste
        reste accessible)."""
        tenant, admin = _make_tenant_with_abonnement(max_employees=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp1', 'email': 'emp1@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp2', 'email': 'emp2@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()

        # Limite atteinte : creation refusee
        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp3', 'email': 'emp3@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 403, r.get_json()
        assert 'employés' in r.get_json()['message']

        # Mais la liste des utilisateurs reste consultable
        r = client.get('/api/v1/users', headers=headers)
        assert r.status_code == 200, r.get_json()
        emails = [u['email'] for u in r.get_json()['users']]
        assert 'emp1@test.mg' in emails
        assert 'emp2@test.mg' in emails

    def test_can_create_employee_user_under_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=3)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp1', 'email': 'emp1@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()

    def test_can_still_create_admin_when_employee_limit_reached(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=1, max_admins=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp1', 'email': 'emp1@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'admin2', 'email': 'admin2@test.mg',
                              'password': 'Pass123!', 'role': 'admin'})
        assert r.status_code == 201, r.get_json()

    def test_cannot_change_user_to_employee_when_limit_reached(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=1)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp1', 'email': 'emp1@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp2', 'email': 'emp2@test.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 403, r.get_json()

    def test_super_admin_bypasses_employee_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=1)
        super_admin = Utilisateur(
            username='super',
            email='super@x.mg',
            password_hash=hash_password('Super123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
        db.session.commit()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'emp1', 'email': 'emp1@test.mg',
                              'password': 'Pass123!', 'role': 'user',
                              'tenant_id': tenant.id})
        assert r.status_code == 201, r.get_json()
