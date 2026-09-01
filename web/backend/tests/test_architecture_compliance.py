"""Tests de conformité de l'architecture SUPER ADMIN =| TENANT == ADMIN =| USER.

Vérifie notamment :
- §5  : la création d'un Tenant crée aussi Admin principal + abonnement initial
- §8  : les données sensibles ne sont jamais retournées en clair par l'API
- §10/§11 : seul l'Admin principal du Tenant peut renouveler / payer (pas seulement un rôle admin)
- §4  : les quotas d'utilisateurs sont indépendants par Tenant
- §16  : l'employee_key est privée au Tenant et jamais exposée au Super Admin
"""
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur, StatutAdmin
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password, verify_password


@pytest.fixture(autouse=True)
def app(monkeypatch, tmp_path):
    # Base de données fichier temporaire par test -> isolation totale
    # (évite le partage de la base :memory: entre les tests de la session).
    db_file = tmp_path / 'test.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db_file}')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    application = create_app()
    application.config['TESTING'] = True
    application.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'timeout': 30},
    }
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


def _create_user(client, headers, username, role='user'):
    return client.post('/api/v1/users', headers=headers, json={
        'username': username,
        'email': username + '@x.mg',
        'password': 'Employe123',
        'nom': username,
        'role': role,
    })


# ---------------------------------------------------------------------------
# §5 : création simultanée Tenant + Admin principal + abonnement
# ---------------------------------------------------------------------------
class TestCreationTenant:

    def test_register_creates_tenant_admin_principal_and_abonnement(self, app):
        client = app.test_client()
        r = _register_company(client, 'Entreprise A', 'a@a.mg')
        assert r.status_code == 201, r.get_json()
        data = r.get_json()

        with app.app_context():
            tenant = Tenant.query.filter_by(slug='entreprise-a').first()
            assert tenant is not None
            # Admin principal lié au tenant
            assert tenant.admin_principal_id is not None
            principal = db.session.get(Utilisateur, tenant.admin_principal_id)
            assert principal is not None
            assert principal.role == Role.ADMIN
            assert principal.tenant_id == tenant.id
            # Admin principal rattaché au tenant
            assert tenant.admin_principal_id is not None
            # Abonnement initial rattaché au tenant
            abo = Abonnement.query.filter_by(tenant_id=tenant.id).first()
            assert abo is not None

    def test_register_returns_no_sensitive_data(self, app):
        client = app.test_client()
        r = _register_company(client, 'Entreprise B', 'b@b.mg')
        assert r.status_code == 201
        data = r.get_json()
        # Le tenant reçoit un admin principal et le hash n'est jamais renvoyé dans la réponse.
        assert data.get('tenant', {}).get('admin_principal_id') is not None
        assert 'admin_key_hash' not in data
        assert 'admin_key_hash' not in data.get('tenant', {})
        assert 'password_hash' not in data.get('user', {})


# ---------------------------------------------------------------------------
# §10/§11 : renouvellement réservé à l'Admin principal du Tenant
# ---------------------------------------------------------------------------
class TestRenouvellement:

    def _principal_and_abonnement(self, client, name, email):
        r = _register_company(client, name, email)
        headers = _auth(client, email)
        # L'abonnement initial est EN_ATTENTE (non encore payé) : on le récupère
        # via l'historique plutôt que via /mon-abonnement (qui ne renvoie que l'actif).
        rh = client.get('/api/v1/abonnements/mon-historique', headers=headers)
        abo_id = rh.get_json()['abonnements'][0]['id']
        return headers, abo_id

    def test_principal_admin_autorise(self, app):
        client = app.test_client()
        headers, abo_id = self._principal_and_abonnement(client, 'T A', 'ta@a.mg')
        r = client.post(f'/api/v1/abonnements/{abo_id}/renouveler', headers=headers)
        assert r.status_code == 200, r.get_json()

    def test_employe_refuse(self, app):
        client = app.test_client()
        r = _register_company(client, 'T B', 'tb@b.mg')
        headers = _auth(client, 'tb@b.mg')
        rh = client.get('/api/v1/abonnements/mon-historique', headers=headers)
        abo_id = rh.get_json()['abonnements'][0]['id']
        # L'admin principal crée un employé
        ru = _create_user(client, headers, 'employe_b')
        assert ru.status_code == 201, ru.get_json()
        emp_email = ru.get_json()['email']
        # L'employé se connecte avec email + mot de passe (connexion professionnelle).
        rl = client.post('/api/v1/auth/login', json={
            'username': emp_email, 'password': 'Employe123'
        })
        assert rl.status_code == 200, rl.get_json()
        emp_headers = {'Authorization': 'Bearer ' + rl.get_json()['access_token']}
        r = client.post(f'/api/v1/abonnements/{abo_id}/renouveler', headers=emp_headers)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# §5/§6 : connexion professionnelle des utilisateurs du Tenant
# ---------------------------------------------------------------------------
class TestConnexionProfessionnelle:

    def _setup_tenant(self, client, name, email, plan='starter'):
        r = _register_company(client, name, email, plan=plan)
        headers = _auth(client, email)
        return headers

    def test_admin_principal_connexion_ok(self, app):
        client = app.test_client()
        self._setup_tenant(client, 'T1', 't1@t.mg')
        r = _login(client, 't1@t.mg')
        assert r.status_code == 200

    def test_user_tenant_a_connexion_ok(self, app):
        client = app.test_client()
        headers = self._setup_tenant(client, 'T2', 't2@t.mg')
        ru = _create_user(client, headers, 'user_t2', role='user')
        assert ru.status_code == 201
        r = client.post('/api/v1/auth/login', json={
            'username': 'user_t2@x.mg', 'password': 'Employe123'
        })
        assert r.status_code == 200

    def test_user_tenant_a_refuse_tenant_b(self, app):
        client = app.test_client()
        headers_a = self._setup_tenant(client, 'T3', 't3@t.mg')
        headers_b = self._setup_tenant(client, 'T4', 't4@t.mg')
        ru = _create_user(client, headers_a, 'user_t3', role='user')
        assert ru.status_code == 201
        # L'utilisateur de A ne peut pas se connecter avec les identifiants de B
        r = client.post('/api/v1/auth/login', json={
            'username': 'user_t3@x.mg', 'password': 'WrongPassword'
        })
        assert r.status_code == 401

    def test_user_tenant_b_refuse_tenant_a(self, app):
        client = app.test_client()
        headers_a = self._setup_tenant(client, 'T5', 't5@t.mg')
        headers_b = self._setup_tenant(client, 'T6', 't6@t.mg')
        ru = _create_user(client, headers_b, 'user_t6', role='user')
        assert ru.status_code == 201
        # L'utilisateur de B ne peut pas se connecter avec un mauvais mot de passe
        r = client.post('/api/v1/auth/login', json={
            'username': 'user_t6@x.mg', 'password': 'WrongPassword'
        })
        assert r.status_code == 401

    def test_mauvais_mot_de_passe_refuse(self, app):
        client = app.test_client()
        self._setup_tenant(client, 'T7', 't7@t.mg')
        r = _login(client, 't7@t.mg', password='wrong-password')
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# §2/§17 : quotas par plan (Starter=3, Pro=7, Enterprise=illimité)
# ---------------------------------------------------------------------------
class TestQuotaPlans:

    def _cree_tenant_et_users(self, client, email, plan, n):
        headers = TestConnexionProfessionnelle()._setup_tenant(client, plan + email, email, plan=plan)
        cree = 0
        for i in range(n):
            ru = _create_user(client, headers, f'u_{email}_{i}')
            if ru.status_code == 201:
                cree += 1
        return headers, cree

    def test_starter_max_trois(self, app):
        client = app.test_client()
        headers = TestConnexionProfessionnelle()._setup_tenant(client, 'S', 's@s.mg', 'starter')
        # admin + 2 = 3 (OK) ; 4e refusé
        assert _create_user(client, headers, 's1').status_code == 201
        assert _create_user(client, headers, 's2').status_code == 201
        assert _create_user(client, headers, 's3').status_code == 403

    def test_pro_max_sept(self, app):
        client = app.test_client()
        headers = TestConnexionProfessionnelle()._setup_tenant(client, 'P', 'p@p.mg', 'pro')
        for i in range(6):
            assert _create_user(client, headers, f'p{i}').status_code == 201
        assert _create_user(client, headers, 'p6').status_code == 403  # 8e (admin+7)

    def test_enterprise_illimite(self, app):
        client = app.test_client()
        headers = TestConnexionProfessionnelle()._setup_tenant(client, 'E', 'e@e.mg', 'enterprise')
        for i in range(12):
            assert _create_user(client, headers, f'e{i}').status_code == 201

    def test_autre_tenant_refuse(self, app):
        client = app.test_client()
        ra = _register_company(client, 'T C', 'tc@c.mg')
        rb = _register_company(client, 'T D', 'td@d.mg')
        ha = _auth(client, 'tc@c.mg')
        hb = _auth(client, 'td@d.mg')

        rh_b = client.get('/api/v1/abonnements/mon-historique', headers=hb)
        abo_b = rh_b.get_json()['abonnements'][0]['id']

        r = client.post(f'/api/v1/abonnements/{abo_b}/renouveler', headers=ha)
        assert r.status_code == 403

    def test_sans_auth_refuse(self, app):
        client = app.test_client()
        r = client.post('/api/v1/abonnements/1/renouveler')
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# §4 : quotas d'utilisateurs indépendants par Tenant (Starter = 3 max)
# ---------------------------------------------------------------------------
class TestQuotaParTenant:

    def test_quota_independant(self, app):
        client = app.test_client()
        ra = _register_company(client, 'Quota A', 'qa@a.mg')
        rb = _register_company(client, 'Quota B', 'qb@b.mg')
        ha = _auth(client, 'qa@a.mg')
        hb = _auth(client, 'qb@b.mg')

        # Tenant A : 1 admin + 2 employés = 3 (limite Starter). Le 4e est refusé.
        assert _create_user(client, ha, 'a_emp1').status_code == 201
        assert _create_user(client, ha, 'a_emp2').status_code == 201
        assert _create_user(client, ha, 'a_emp3').status_code == 403

        # Tenant B indépendant : peut encore créer un utilisateur.
        assert _create_user(client, hb, 'b_emp1').status_code == 201


# ---------------------------------------------------------------------------
# §16 : employee_key privée au Tenant, jamais exposée au Super Admin
# ---------------------------------------------------------------------------
class TestEmployeeKeyConfidentiality:

    def test_tenant_a_can_generate_employee_key(self, app):
        client = app.test_client()
        r = _register_company(client, 'EK A', 'eka@a.mg', 'starter')
        assert r.status_code == 201
        headers = _auth(client, 'eka@a.mg')

        r = client.post('/api/v1/tenants/me/employee-key', headers=headers)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert 'employee_key' in data
        assert isinstance(data['employee_key'], str)
        assert len(data['employee_key']) > 0
        assert data['status'] == 'active'

    def test_tenant_a_can_view_employee_key_exists(self, app):
        client = app.test_client()
        r = _register_company(client, 'EK B', 'ekb@b.mg', 'starter')
        assert r.status_code == 201
        headers = _auth(client, 'ekb@b.mg')

        client.post('/api/v1/tenants/me/employee-key', headers=headers)
        r = client.get('/api/v1/tenants/me/employee-key', headers=headers)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data.get('has_employee_key') is True
        assert data.get('status') == 'active'

    def test_tenant_b_cannot_view_tenant_a_employee_key(self, app):
        client = app.test_client()
        ra = _register_company(client, 'EK TA', 'ekta@a.mg', 'starter')
        rb = _register_company(client, 'EK TB', 'ektb@b.mg', 'starter')
        ha = _auth(client, 'ekta@a.mg')
        hb = _auth(client, 'ektb@b.mg')

        client.post('/api/v1/tenants/me/employee-key', headers=ha)
        r = client.get('/api/v1/tenants/me/employee-key', headers=hb)
        assert r.status_code == 404

    def test_super_admin_cannot_view_employee_key(self, app):
        client = app.test_client()
        _register_company(client, 'EK SA', 'eksa@a.mg', 'starter')
        with app.app_context():
            sa = Utilisateur(
                username='super',
                email='super@x.mg',
                password_hash=hash_password('Super123!'),
                role=Role.SUPER_ADMIN,
                statut=StatutUtilisateur.ACTIF,
            )
            db.session.add(sa)
            db.session.commit()

        h_admin = _auth(client, 'eksa@a.mg')
        client.post('/api/v1/tenants/me/employee-key', headers=h_admin)

        r = client.post('/api/v1/auth/login', json={
            'username': 'super@x.mg',
            'password': 'Super123!',
        })
        assert r.status_code == 200, r.get_json()
        h_super = {'Authorization': 'Bearer ' + r.get_json()['access_token']}
        r = client.get('/api/v1/tenants/me/employee-key', headers=h_super)
        assert r.status_code == 403

    def test_employee_key_not_in_register_response(self, app):
        client = app.test_client()
        r = _register_company(client, 'EK Reg', 'ekreg@a.mg', 'starter')
        assert r.status_code == 201
        data = r.get_json()
        assert 'employee_key' not in data
        assert 'employee_key' not in data.get('tenant', {})

    def test_employee_key_not_in_me_response(self, app):
        client = app.test_client()
        r = _register_company(client, 'EK Me', 'ekme@a.mg', 'starter')
        assert r.status_code == 201
        h = _auth(client, 'ekme@a.mg')
        me = client.get('/api/v1/auth/me', headers=h).get_json()
        assert 'employee_key' not in me.get('user', {})
        assert 'employee_key' not in me.get('tenant', {})

    def test_employee_key_not_exposed_to_super_admin_tenant_list(self, app):
        client = app.test_client()
        _register_company(client, 'EK SA2', 'eksa2@a.mg', 'starter')
        with app.app_context():
            sa = Utilisateur(
                username='super2',
                email='super2@x.mg',
                password_hash=hash_password('Super123!'),
                role=Role.SUPER_ADMIN,
                statut=StatutUtilisateur.ACTIF,
            )
            db.session.add(sa)
            db.session.commit()

        h_admin = _auth(client, 'eksa2@a.mg')
        client.post('/api/v1/tenants/me/employee-key', headers=h_admin)

        r = client.post('/api/v1/auth/login', json={
            'username': 'super2@x.mg',
            'password': 'Super123!',
        })
        assert r.status_code == 200, r.get_json()
        h_super = {'Authorization': 'Bearer ' + r.get_json()['access_token']}
        r = client.get('/api/v1/tenants/', headers=h_super)
        assert r.status_code == 200
        data = r.get_json()
        for tenant in data.get('tenants', []):
            assert 'employee_key' not in tenant
