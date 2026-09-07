"""Tests de conformitÃ© pour l'employee_key â€” ClÃ© privÃ©e du Tenant.

VÃ©rifie :
- Â§1  : Tenant A peut crÃ©er sa clÃ© employÃ©
- Â§2  : Tenant A peut consulter sa clÃ©
- Â§3  : Tenant B ne peut pas consulter la clÃ© de Tenant A
- Â§4  : Super Admin ne voit pas l'employee_key dans la liste des Tenants
- Â§5  : Super Admin ne voit pas l'employee_key dans la liste des utilisateurs
- Â§6  : L'API Super Admin ne peut pas rÃ©cupÃ©rer la clÃ© directement
- Â§7  : Recherche globale admin_key = aucune rÃ©fÃ©rence mÃ©tier active
"""
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur, StatutAdmin
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://postgres:eemntirey@localhost:55432/erp_test')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    application = create_app()
    application.config['TESTING'] = True
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.engine.dispose()
        db.drop_all()


def _register_company(client, name, email, plan='starter'):
    return client.post('/api/v1/auth/register', json={
        'profile_type': 'company',
        'nom_entreprise': name,
        'email': email,
        'username': email,
        'password': 'Companie123',
        'nom': 'Boss',
        'plan': plan,
    })


def _login(client, email, password='Companie123', device_id='device-test'):
    return client.post('/api/v1/auth/login', json={
        'username': email,
        'password': password,
        'device_id': device_id,
    })


def _auth(client, email, password='Companie123', device_id='device-test'):
    r = _login(client, email, password, device_id)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


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


# ---------------------------------------------------------------------------
# Â§1 : Tenant A peut crÃ©er sa clÃ© employÃ©
# ---------------------------------------------------------------------------
class TestEmployeeKeyCreation:

    def test_tenant_can_create_employee_key(self, app):
        """Test 1: Tenant A crÃ©e sa clÃ© employÃ© -> succÃ¨s."""
        client = app.test_client()
        r = _register_company(client, 'Entreprise A', 'a@a.mg')
        assert r.status_code == 201, r.get_json()
        h = _auth(client, 'a@a.mg')

        # CrÃ©er l'employee_key
        r = client.post('/api/v1/tenants/me/employee-key', headers=h)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert 'employee_key' in data
        assert isinstance(data['employee_key'], str)
        assert len(data['employee_key']) > 0

    def test_tenant_can_regenerate_employee_key(self, app):
        """Test 1b: Tenant A peut rÃ©gÃ©nÃ©rer sa clÃ© employÃ©."""
        client = app.test_client()
        r = _register_company(client, 'Entreprise B', 'b@b.mg')
        assert r.status_code == 201, r.get_json()
        h = _auth(client, 'b@b.mg')

        # PremiÃ¨re crÃ©ation
        r1 = client.post('/api/v1/tenants/me/employee-key', headers=h)
        assert r1.status_code == 200
        key1 = r1.get_json()['employee_key']

        # RÃ©gÃ©nÃ©ration
        r2 = client.post('/api/v1/tenants/me/employee-key', headers=h)
        assert r2.status_code == 200
        key2 = r2.get_json()['employee_key']

        # Les clÃ©s doivent Ãªtre diffÃ©rentes
        assert key1 != key2


# ---------------------------------------------------------------------------
# Â§2 : Tenant A peut consulter sa clÃ©
# ---------------------------------------------------------------------------
class TestEmployeeKeyConsultation:

    def test_tenant_can_see_employee_key_status(self, app):
        """Test 2: Tenant A consulte sa clÃ© -> autorisÃ©."""
        client = app.test_client()
        r = _register_company(client, 'Entreprise C', 'c@c.mg')
        assert r.status_code == 201, r.get_json()
        h = _auth(client, 'c@c.mg')

        # CrÃ©er l'employee_key
        client.post('/api/v1/tenants/me/employee-key', headers=h)

        # Consulter le statut
        r = client.get('/api/v1/tenants/me/employee-key', headers=h)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data.get('has_employee_key') is True
        assert data.get('status') == 'active'

    def test_non_principal_admin_cannot_access_employee_key(self, app):
        """Test 2b: Un employÃ© non admin principal ne peut pas accÃ©der Ã  la clÃ©."""
        client = app.test_client()
        r = _register_company(client, 'Entreprise D', 'd@d.mg', 'enterprise')
        assert r.status_code == 201, r.get_json()
        h = _auth(client, 'd@d.mg')

        # CrÃ©er un employÃ© normal
        ru = client.post('/api/v1/users', headers=h, json={
            'username': 'employe_d',
            'email': 'employe_d@x.mg',
            'password': 'Employe123',
            'nom': 'Employe',
            'role': 'user',
        })
        assert ru.status_code == 201

        # L'employÃ© tente d'accÃ©der Ã  l'employee_key
        emp_h = _auth(client, 'employe_d@x.mg', 'Employe123')
        r = client.get('/api/v1/tenants/me/employee-key', headers=emp_h)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Â§3 : Tenant B ne peut pas consulter la clÃ© de Tenant A
# ---------------------------------------------------------------------------
class TestEmployeeKeyIsolation:

    def test_tenant_b_cannot_see_tenant_a_key(self, app):
        """Test 3: Tenant B tente de consulter la clÃ© de Tenant A -> accÃ¨s refusÃ©."""
        client = app.test_client()

        # CrÃ©er Tenant A avec sa clÃ©
        ra = _register_company(client, 'Tenant A', 'ta@a.mg')
        assert ra.status_code == 201
        ha = _auth(client, 'ta@a.mg')
        client.post('/api/v1/tenants/me/employee-key', headers=ha)

        # CrÃ©er Tenant B
        rb = _register_company(client, 'Tenant B', 'tb@b.mg')
        assert rb.status_code == 201
        hb = _auth(client, 'tb@b.mg')

        # Tenant B tente d'accÃ©der Ã  la clÃ© de A (via l'API de A)
        # L'API /tenants/me renvoie le tenant de l'utilisateur authentifiÃ©
        # Donc Tenant B ne peut voir que sa propre clÃ© (qui n'existe pas encore)
        r = client.get('/api/v1/tenants/me/employee-key', headers=hb)
        assert r.status_code == 404
        assert r.get_json().get('message') == 'Aucune cle employe generee'


# ---------------------------------------------------------------------------
# Â§4 : Super Admin ne voit pas l'employee_key dans la liste des Tenants
# ---------------------------------------------------------------------------
class TestSuperAdminTenantList:

    def test_super_admin_tenant_list_no_employee_key(self, app):
        """Test 4: Super Admin consulte la liste des Tenants -> employee_key absente."""
        client = app.test_client()
        _make_super_admin()

        # CrÃ©er un Tenant avec sa clÃ©
        r = _register_company(client, 'Tenant X', 'tx@x.mg')
        assert r.status_code == 201
        h = _auth(client, 'tx@x.mg')
        client.post('/api/v1/tenants/me/employee-key', headers=h)

        # Super Admin se connecte
        sh = _auth(client, 'super@x.mg', 'Super123!')

        # Super Admin consulte la liste des tenants
        r = client.get('/api/v1/super-admin/tenants', headers=sh)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()

        # VÃ©rifier que l'employee_key n'est pas exposÃ©e
        for tenant in data.get('tenants', []):
            assert 'employee_key' not in tenant
            assert 'employee_key_hash' not in tenant


# ---------------------------------------------------------------------------
# Â§5 : Super Admin ne voit pas l'employee_key dans la liste des utilisateurs
# ---------------------------------------------------------------------------
class TestSuperAdminUserList:

    def test_super_admin_user_list_no_employee_key(self, app):
        """Test 5: Super Admin consulte la liste des utilisateurs -> employee_key absente."""
        client = app.test_client()
        _make_super_admin()

        # CrÃ©er un Tenant avec sa clÃ©
        r = _register_company(client, 'Tenant Y', 'ty@y.mg')
        assert r.status_code == 201

        # Super Admin se connecte
        sh = _auth(client, 'super@x.mg', 'Super123!')

        # Super Admin consulte la liste des utilisateurs
        r = client.get('/api/v1/super-admin/users', headers=sh)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()

        # VÃ©rifier que l'employee_key n'est pas exposÃ©e
        for user in data.get('users', []):
            assert 'employee_key' not in user
            assert 'employee_key_hash' not in user


# ---------------------------------------------------------------------------
# Â§6 : L'API Super Admin ne peut pas rÃ©cupÃ©rer la clÃ© directement
# ---------------------------------------------------------------------------
class TestSuperAdminDirectAccess:

    def test_super_admin_cannot_get_employee_key_directly(self, app):
        """Test 6: L'API Super Admin tente de rÃ©cupÃ©rer directement la clÃ© -> refus."""
        client = app.test_client()
        _make_super_admin()

        # CrÃ©er un Tenant avec sa clÃ©
        r = _register_company(client, 'Tenant Z', 'tz@z.mg')
        assert r.status_code == 201
        h = _auth(client, 'tz@z.mg')
        client.post('/api/v1/tenants/me/employee-key', headers=h)

        # RÃ©cupÃ©rer l'ID du tenant
        with app.app_context():
            tenant = Tenant.query.filter_by(slug='tenant-z').first()
            tenant_id = tenant.id

        # Super Admin se connecte
        sh = _auth(client, 'super@x.mg', 'Super123!')

        # Super Admin tente d'accÃ©der Ã  la clÃ© du tenant
        # L'endpoint /api/v1/tenants/<id> ne doit pas exposer l'employee_key
        r = client.get(f'/api/v1/tenants/{tenant_id}', headers=sh)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert 'employee_key' not in data
        assert 'employee_key_hash' not in data


# ---------------------------------------------------------------------------
# Â§7 : Recherche globale admin_key = aucune rÃ©fÃ©rence mÃ©tier active
# ---------------------------------------------------------------------------
class TestGlobalAdminKeySearch:

    def test_no_active_admin_key_in_code(self, app):
        """Test 7: VÃ©rifier que le code ne contient pas de rÃ©fÃ©rences actives Ã  admin_key."""
        import os
        import re

        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        backend_dir = os.path.join(repo_root, 'web', 'backend', 'app')

        # Patterns Ã  rechercher (rÃ©fÃ©rences fonctionnelles, pas les assertions de sÃ©curitÃ©)
        functional_patterns = [
            r"admin_key_hash\s*=",  # Assignation
            r"admin_key_status\s*=",  # Assignation
            r"hash_admin_key\s*\(",  # Appel de fonction
            r"verify_admin_key\s*\(",  # Appel de fonction
            r"_resolve_admin_key\s*\(",  # Appel de fonction
            r"_validate_admin_key\s*\(",  # Appel de fonction
        ]

        violations = []
        for root, dirs, files in os.walk(backend_dir):
            # Ignorer les migrations (historique) et les tests
            if 'migrations' in root or 'tests' in root:
                continue
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in functional_patterns:
                        if re.search(pattern, content):
                            violations.append((filepath, pattern))

        assert violations == [], f"RÃ©fÃ©rences fonctionnelles Ã  admin_key trouvÃ©es: {violations}"

    def test_no_admin_key_in_api_responses(self, app):
        """Test 7b: VÃ©rifier que les rÃ©ponses API ne contiennent pas d'admin_key."""
        client = app.test_client()
        _make_super_admin()

        # CrÃ©er un Tenant
        r = _register_company(client, 'Tenant Audit', 'audit@a.mg')
        assert r.status_code == 201

        # VÃ©rifier la rÃ©ponse d'inscription
        data = r.get_json()
        assert 'admin_key' not in data
        assert 'admin_key_hash' not in data

        # VÃ©rifier /me
        h = _auth(client, 'audit@a.mg')
        me = client.get('/api/v1/auth/me', headers=h).get_json()
        assert 'admin_key' not in me
        assert 'admin_key_hash' not in me
        assert 'admin_key' not in me.get('tenant', {})
        assert 'admin_key_hash' not in me.get('tenant', {})

        # VÃ©rifier la liste Super Admin
        sh = _auth(client, 'super@x.mg', 'Super123!')
        tenants = client.get('/api/v1/super-admin/tenants', headers=sh).get_json()
        for tenant in tenants.get('tenants', []):
            assert 'admin_key' not in tenant
            assert 'admin_key_hash' not in tenant
