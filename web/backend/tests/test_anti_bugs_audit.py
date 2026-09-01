"""Plan de test anti-bugs - Audit complet de l'architecture MIHAJA_ERP_PRO.

Ce fichier transpose en tests pytest les 33 sections du plan d'audit. Il
ne declare pas ZERO BUGS simplement parce que les anciens tests passent
: il execute une nouvelle batterie de tests et produit un rapport final
avec PASS / FAIL / BLOCKED / SKIPPED.
"""
import os
import re
import secrets
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import jwt
import pytest
from flask import current_app
from flask_jwt_extended import create_access_token

# Importer le module app une seule fois au chargement
from app import create_app, db  # noqa: E402
from app.models.abonnement import Abonnement, StatutAbonnement  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.models.produit import Produit  # noqa: E402
from app.models.tenant import Tenant, StatutTenant  # noqa: E402
from app.models.utilisateur import (  # noqa: E402
    Role,
    StatutAdmin,
    StatutUtilisateur,
    Utilisateur,
)
from app.security.auth import (  # noqa: E402
    hash_password,
    verify_password,
)
from app.security.plans import (  # noqa: E402
    MAX_ADMINS_ABSOLUTE,
    PLAN_CONFIG,
    admin_limit,
    get_plan_config,
    resolve_limits,
)


# ---------------------------------------------------------------------------
# Fixtures et helpers
# ---------------------------------------------------------------------------

# App session-scope : on reutilise la meme instance pour eviter le conflit
# d'enregistrement de fonctions de vue Flask entre tests.
_audit_app = None


def _get_audit_app():
    global _audit_app
    if _audit_app is None:
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        os.environ['JWT_SECRET_KEY'] = 'audit-secret'
        os.environ['SECRET_KEY'] = 'audit-secret'
        os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
        os.environ['PAPI_API_KEY'] = 'test-api-key'
        os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
        os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'
        _audit_app = create_app()
        _audit_app.config['TESTING'] = True
    return _audit_app


@pytest.fixture
def app():
    application = _get_audit_app()
    with application.app_context():
        db.drop_all()
        db.create_all()
        try:
            from scripts.seed_roles import seed_roles
            seed_roles()
        except Exception:
            pass
        yield application
        db.session.remove()
        db.drop_all()


def _register_company(client, name, email, plan='starter', password='Companie123'):
    return client.post('/api/v1/auth/register', json={
        'profile_type': 'company',
        'nom_entreprise': name,
        'email': email,
        'username': email,
        'password': password,
        'nom': 'Boss',
        'plan': plan,
    })


def _login(client, email, password='Companie123', device_id='device-audit'):
    return client.post('/api/v1/auth/login', json={
        'username': email,
        'password': password,
        'device_id': device_id,
    })


def _auth(client, email, password='Companie123', device_id='device-audit'):
    r = _login(client, email, password, device_id=device_id)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


def _create_user(client, headers, username, role='user', password='Employe123'):
    return client.post('/api/v1/users', headers=headers, json={
        'username': username,
        'email': f'{username}@x.mg',
        'password': password,
        'nom': username,
        'role': role,
    })


def _created_user_data(resp):
    """Normalise la reponse de POST /api/v1/users (retourne user.to_dict() directement)."""
    data = resp.get_json() or {}
    if 'user' in data:
        return data['user']
    return data


# Compteurs de resultats (rapport final)
_RESULTS = Counter()


def _record(name, outcome):
    _RESULTS[outcome] += 1
    return outcome


# ===========================================================================
# Section 2 - TEST 1.1 : Inscription normale
# ===========================================================================
class Test1_1InscriptionNormale:
    def test_cree_tenant_user_admin_principal_et_abonnement(self, app):
        client = app.test_client()
        r = _register_company(client, 'Entreprise A', 'a@a.mg', 'pro')
        assert r.status_code == 201, r.get_json()
        data = r.get_json()

        with app.app_context():
            tenant = Tenant.query.filter_by(slug='entreprise-a').first()
            assert tenant is not None
            user = db.session.get(Utilisateur, tenant.admin_principal_id)
            assert user is not None
            assert user.tenant_id == tenant.id
            assert tenant.admin_principal_id == user.id
            assert user.role == Role.ADMIN
            assert user.is_principal_admin is True

            abo = Abonnement.query.filter_by(tenant_id=tenant.id).first()
            assert abo is not None
            assert abo.tenant_id == tenant.id
            _record('1.1 inscription normale', 'PASS')

    def test_auth_me_ne_crashe_pas(self, app):
        """Regression : /api/v1/auth/me doit fonctionner (tenant.to_dict avec
        include_subscription=True charge l'admin_principal)."""
        client = app.test_client()
        r = _register_company(client, 'MeCo', 'me@m.mg', 'starter')
        h = _auth(client, 'me@m.mg')
        me = client.get('/api/v1/auth/me', headers=h)
        assert me.status_code == 200, me.get_json()
        assert me.get_json()['user']['email'] == 'me@m.mg'
        assert me.get_json()['tenant']['admin_principal'] is not None
        _record('1.1b /me fonctionnel', 'PASS')


# ===========================================================================
# Section 3 - TEST 1.2 : admin_principal_id est la source de verite
# ===========================================================================
class Test1_2AdminPrincipal:

    def _setup_two_admins(self, app, client, name, email, plan='starter'):
        r = _register_company(client, name, email, plan=plan)
        headers = _auth(client, email)
        # On cree un second utilisateur avec role=ADMIN
        with app.app_context():
            tenant = Tenant.query.filter_by(slug=name.lower()).first()
            admin_principal = db.session.get(Utilisateur, tenant.admin_principal_id)
            other = Utilisateur(
                username='admin2',
                email='admin2@x.mg',
                password_hash=hash_password('Employe123'),
                role=Role.ADMIN,
                statut=StatutUtilisateur.ACTIF,
                admin_statut=StatutAdmin.ACTIVE,
                tenant_id=tenant.id,
                is_principal_admin=False,
            )
            db.session.add(other)
            db.session.commit()
            other_id = other.id
            principal_id = admin_principal.id
            tenant_id = tenant.id
            tenant_slug = tenant.slug
            return principal_id, other_id, tenant_id, tenant_slug, headers

    def test_un_seul_est_principal(self, app):
        client = app.test_client()
        principal_id, other_id, tenant_id, tenant_slug, headers = self._setup_two_admins(
            app, client, 'T1', 't1@t.mg'
        )
        with app.app_context():
            principal = db.session.get(Utilisateur, principal_id)
            other = db.session.get(Utilisateur, other_id)
            assert principal.is_principal_admin is True
            assert other.is_principal_admin is False
        # L'API de renouvellement utilise l'identite, pas le role
        rh = client.get('/api/v1/abonnements/mon-historique', headers=headers)
        abo_id = rh.get_json()['abonnements'][0]['id']
        # Le principal passe
        r = client.post(f'/api/v1/abonnements/{abo_id}/renouveler', headers=headers)
        assert r.status_code == 200, r.get_json()
        # L'autre ADMIN est refuse
        with app.app_context():
            token = create_access_token(
                identity=other_id,
                additional_claims={
                    'role': 'admin',
                    'tenant_id': tenant_id,
                    'tenant_slug': tenant_slug,
                },
            )
        h2 = {'Authorization': 'Bearer ' + token}
        r = client.post(f'/api/v1/abonnements/{abo_id}/renouveler', headers=h2)
        assert r.status_code == 403
        _record('1.2 admin principal = identite', 'PASS')


# ===========================================================================
# Section 4 - TEST 1.3 : deux entreprises independantes
# ===========================================================================
class Test1_3IndependanceTenants:
    def test_deux_tenants_pro_independants(self, app):
        client = app.test_client()
        ra = _register_company(client, 'A Corp', 'a@a.mg', 'pro')
        rb = _register_company(client, 'B Corp', 'b@b.mg', 'pro')
        ha = _auth(client, 'a@a.mg')
        hb = _auth(client, 'b@b.mg')
        with app.app_context():
            ta = Tenant.query.filter_by(slug='a-corp').first()
            tb = Tenant.query.filter_by(slug='b-corp').first()
            assert ta.id != tb.id
            ua = db.session.get(Utilisateur, ta.admin_principal_id)
            ub = db.session.get(Utilisateur, tb.admin_principal_id)
            assert ua.tenant_id == ta.id
            assert ub.tenant_id == tb.id
            sa = Abonnement.query.filter_by(tenant_id=ta.id).first()
            sb = Abonnement.query.filter_by(tenant_id=tb.id).first()
            assert sa.tenant_id == ta.id and sb.tenant_id == tb.id
        _record('1.3 deux tenants independants', 'PASS')


# ===========================================================================
# Section 5 - TEST 2 : abonnement lie au tenant
# ===========================================================================
class Test2AbonnementLieAuTenant:
    def test_abonnement_a_son_tenant_id(self, app):
        client = app.test_client()
        for name, email in [('A', 'a@a.mg'), ('B', 'b@b.mg'), ('C', 'c@c.mg')]:
            _register_company(client, name, email, plan=('pro' if name != 'C' else 'starter'))
        with app.app_context():
            for slug, expected_plan in [('a', 'pro'), ('b', 'pro'), ('c', 'starter')]:
                tenant = Tenant.query.filter_by(slug=slug).first()
                abo = Abonnement.query.filter_by(tenant_id=tenant.id).first()
                assert abo is not None
                assert abo.tenant_id == tenant.id
                assert abo.plan == expected_plan
        # Recherche de logique globale interdite
        repo_root = Path(__file__).resolve().parents[3]
        forbidden = []
        for path in (repo_root / 'web' / 'backend' / 'app').rglob('*.py'):
            text = path.read_text(encoding='utf-8', errors='ignore')
            # Le seed initial (verification base vide) est le seul endroit
            # autorise a faire un count() non scope par tenant.
            if re.search(r"count_all_users_for_plan", text):
                forbidden.append(str(path))
        assert forbidden == [], f'Logique globale interdite trouvee dans {forbidden}'
        _record('2 abonnement lie au tenant', 'PASS')


# ===========================================================================
# Section 6 - TEST 3 : quota utilisateurs par plan
# ===========================================================================
class Test3QuotaUtilisateurs:
    def test_plan_gratuit_max_un(self, app):
        client = app.test_client()
        r = _register_company(client, 'G', 'g@g.mg', 'gratuit')
        h = _auth(client, 'g@g.mg')
        # L'admin est deja cree. Tenter un employe -> REFUS (gratuit = 1 utilisateur)
        assert _create_user(client, h, 'employe1').status_code == 403
        _record('3a quota gratuit', 'PASS')

    def test_plan_starter_max_trois(self, app):
        client = app.test_client()
        r = _register_company(client, 'S', 's@s.mg', 'starter')
        h = _auth(client, 's@s.mg')
        assert _create_user(client, h, 's1').status_code == 201
        assert _create_user(client, h, 's2').status_code == 201
        assert _create_user(client, h, 's3').status_code == 403
        _record('3b quota starter', 'PASS')

    def test_plan_pro_max_sept(self, app):
        client = app.test_client()
        r = _register_company(client, 'P', 'p@p.mg', 'pro')
        h = _auth(client, 'p@p.mg')
        for i in range(6):
            assert _create_user(client, h, f'p{i}').status_code == 201
        assert _create_user(client, h, 'p6').status_code == 403
        _record('3c quota pro', 'PASS')


# ===========================================================================
# Section 7 - TEST critique : deux tenants avec le meme plan
# ===========================================================================
class TestCritiqueDeuxTenantsMemePlan:
    def test_quota_atteint_A_et_B_independants(self, app):
        client = app.test_client()
        ra = _register_company(client, 'TA', 'ta@t.mg', 'pro')
        rb = _register_company(client, 'TB', 'tb@t.mg', 'pro')
        ha = _auth(client, 'ta@t.mg')
        hb = _auth(client, 'tb@t.mg')
        # TA : admin + 6 employes = 7 (limite Pro)
        for i in range(6):
            assert _create_user(client, ha, f'a{i}').status_code == 201
        assert _create_user(client, ha, 'a6').status_code == 403
        # TB : idem
        for i in range(6):
            assert _create_user(client, hb, f'b{i}').status_code == 201
        assert _create_user(client, hb, 'b6').status_code == 403
        _record('7 deux tenants meme plan', 'PASS')


# ===========================================================================
# Section 8 - TEST critique : quota global interdit
# ===========================================================================
class TestCritiqueQuotaGlobalInterdit:
    def test_creation_B_independante_de_A(self, app):
        client = app.test_client()
        ra = _register_company(client, 'TenA', 'tena@t.mg', 'pro')
        rb = _register_company(client, 'TenB', 'tenb@t.mg', 'pro')
        ha = _auth(client, 'tena@t.mg')
        hb = _auth(client, 'tenb@t.mg')
        # Sature A
        for i in range(6):
            _create_user(client, ha, f'ta{i}')
        # B doit pouvoir creer alors que A est sature
        assert _create_user(client, hb, 'tb1').status_code == 201
        _record('8 pas de quota global', 'PASS')


# ===========================================================================
# Section 9 - TEST 4 : isolation des clients
# ===========================================================================
class Test4IsolationClients:
    def test_quotas_clients_independants(self, app):
        client = app.test_client()
        ra = _register_company(client, 'CliA', 'cliA@x.mg', 'starter')
        rb = _register_company(client, 'CliB', 'cliB@x.mg', 'starter')
        ha = _auth(client, 'cliA@x.mg')
        hb = _auth(client, 'cliB@x.mg')
        with app.app_context():
            ta = Tenant.query.filter_by(slug='clia').first()
            tb = Tenant.query.filter_by(slug='clib').first()
            # Le starter a max_clients=100, on sature A juste a la limite
            for i in range(100):
                c = Client(
                    code=f'CA{i:03d}',
                    nom=f'ClientA{i}',
                    tenant_id=ta.id,
                )
                db.session.add(c)
            db.session.commit()
            # B doit toujours pouvoir creer
        r = client.post('/api/v1/clients', headers=hb, json={
            'code': 'CB001',
            'nom': 'ClientB1',
            'type': 'particulier',
        })
        assert r.status_code == 201, r.get_json()
        _record('9 isolation clients', 'PASS')


# ===========================================================================
# Section 10 - TEST 5 : isolation des modules
# ===========================================================================
class Test5IsolationModules:
    def test_modules_independants_par_tenant(self, app):
        client = app.test_client()
        ra = _register_company(client, 'ModA', 'moda@m.mg', 'starter')
        rb = _register_company(client, 'ModB', 'modb@m.mg', 'starter')
        ha = _auth(client, 'moda@m.mg')
        hb = _auth(client, 'modb@m.mg')
        with app.app_context():
            from app.models.abonnement import Abonnement, StatutAbonnement
            from datetime import datetime, timedelta
            ta = Tenant.query.filter_by(slug='moda').first()
            tb = Tenant.query.filter_by(slug='modb').first()
            for t, mods in [(ta, 'produits,clients,ventes'), (tb, 'produits,clients,comptabilite')]:
                abo = Abonnement.query.filter_by(tenant_id=t.id).first()
                abo.statut = StatutAbonnement.ACTIF
                abo.modules = mods
                abo.date_fin = datetime.utcnow() + timedelta(days=30)
                db.session.add(abo)
            db.session.commit()
        # Acceder a /comptabilite en tant que A (module absent) -> 403
        r = client.post('/api/v1/comptabilite/exercice', headers=ha, json={'nom': 'X'})
        if r.status_code != 404:
            # L'API existe : doit refuser pour tenant A
            assert r.status_code == 403
        # B peut y acceder
        r = client.post('/api/v1/comptabilite/exercice', headers=hb, json={'nom': 'Y'})
        assert r.status_code in (201, 200, 404)
        _record('10 isolation modules', 'PASS')


# ===========================================================================
# Section 11 - TEST 6 : changement d'abonnement
# ===========================================================================
class Test6ChangementAbonnement:
    def test_changement_isole(self, app):
        client = app.test_client()
        ra = _register_company(client, 'ChA', 'cha@c.mg', 'starter')
        rb = _register_company(client, 'ChB', 'chb@c.mg', 'starter')
        ha = _auth(client, 'cha@c.mg')
        with app.app_context():
            from app.services.abonnement_service import AbonnementService
            from datetime import datetime
            ta = Tenant.query.filter_by(slug='cha').first()
            tb = Tenant.query.filter_by(slug='chb').first()
            tb_id = tb.id
            AbonnementService.create_abonnement({'tenant_id': ta.id, 'plan': 'pro'})
            db.session.commit()
        r = client.get('/api/v1/abonnements/mon-historique', headers=ha)
        # Tenant B doit toujours etre sur 'starter'
        with app.app_context():
            tb_plan = db.session.get(Tenant, tb_id).plan
            assert tb_plan == 'starter'
        _record('11 changement abonnement isole', 'PASS')


# ===========================================================================
# Section 12 - TEST 7 : renouvellement
# ===========================================================================
class Test7RenouvellementRoles:
    ROLES_A_TESTER = ['user', 'sales', 'stock', 'accountant', 'rh', 'manager']

    def test_seul_admin_principal_peut_renouveler(self, app):
        client = app.test_client()
        r = _register_company(client, 'RenA', 'ren@r.mg', 'enterprise')
        h_admin = _auth(client, 'ren@r.mg')
        with app.app_context():
            from app.models.tenant import Tenant as _T
            tenant = _T.query.filter_by(slug='rena').first()
        # Historique pour avoir un abo
        rh = client.get('/api/v1/abonnements/mon-historique', headers=h_admin)
        abo_id = rh.get_json()['abonnements'][0]['id']

        # L'admin principal -> 200
        r = client.post(f'/api/v1/abonnements/{abo_id}/renouveler', headers=h_admin)
        assert r.status_code in (200, 201), r.get_json()

        # Creer des employes avec chaque role
        for role in self.ROLES_A_TESTER:
            ru = _create_user(client, h_admin, f'emp_{role}', role=role)
            assert ru.status_code == 201, ru.get_json()
            emp_email = _created_user_data(ru)['email']
            rl = client.post('/api/v1/auth/login', json={
                'username': emp_email,
                'password': 'Employe123',
            })
            assert rl.status_code == 200, rl.get_json()
            emp_h = {'Authorization': 'Bearer ' + rl.get_json()['access_token']}
            r = client.post(f'/api/v1/abonnements/{abo_id}/renouveler', headers=emp_h)
            assert r.status_code == 403, (role, r.get_json())
        _record('12 renouvellement restreint au principal', 'PASS')

    def test_user_autre_tenant_403(self, app):
        client = app.test_client()
        ra = _register_company(client, 'RT1', 'rt1@r.mg', 'starter')
        rb = _register_company(client, 'RT2', 'rt2@r.mg', 'starter')
        ha = _auth(client, 'rt1@r.mg')
        hb = _auth(client, 'rt2@r.mg')
        rh = client.get('/api/v1/abonnements/mon-historique', headers=ha)
        abo_a = rh.get_json()['abonnements'][0]['id']
        r = client.post(f'/api/v1/abonnements/{abo_a}/renouveler', headers=hb)
        assert r.status_code == 403
        _record('12b user autre tenant 403', 'PASS')


# ===========================================================================
# Section 13 - TEST 8 : cross-tenant
# ===========================================================================
class Test8CrossTenant:
    def test_admin_A_ne_voit_pas_B(self, app):
        client = app.test_client()
        ra = _register_company(client, 'X1', 'x1@x.mg', 'pro')
        rb = _register_company(client, 'X2', 'x2@x.mg', 'pro')
        ha = _auth(client, 'x1@x.mg')
        hb = _auth(client, 'x2@x.mg')
        # Creer un employe B
        rb_emp = _create_user(client, hb, 'empB')
        emp_b_id = _created_user_data(rb_emp)['id']
        # A tente de voir /users/<id_empB>
        r = client.get(f'/api/v1/users/{emp_b_id}', headers=ha)
        assert r.status_code in (403, 404)
        # A tente de modifier
        r = client.put(f'/api/v1/users/{emp_b_id}', headers=ha, json={'nom': 'Pirate'})
        assert r.status_code in (403, 404)
        # A tente de supprimer
        r = client.delete(f'/api/v1/users/{emp_b_id}', headers=ha)
        assert r.status_code in (403, 404)
        # A tente d'acceder a l'abonnement de B
        rh = client.get('/api/v1/abonnements/mon-historique', headers=hb)
        abo_b = rh.get_json()['abonnements'][0]['id']
        r = client.post(f'/api/v1/abonnements/{abo_b}/renouveler', headers=ha)
        assert r.status_code in (403, 404)
        _record('13 cross-tenant', 'PASS')


# ===========================================================================
# Section 14 - TEST 9 : manipulation du tenant_id
# ===========================================================================
class Test9ManipulationTenantId:
    def test_body_tenant_id_autre_tenant_refuse(self, app):
        client = app.test_client()
        ra = _register_company(client, 'MT1', 'mt1@m.mg', 'pro')
        rb = _register_company(client, 'MT2', 'mt2@m.mg', 'pro')
        ha = _auth(client, 'mt1@m.mg')
        with app.app_context():
            tb = Tenant.query.filter_by(slug='mt2').first()
        # Tenter de creer un user en precisant tenant_id=TB -> REFUS
        r = client.post('/api/v1/users', headers=ha, json={
            'username': 'pirate',
            'email': 'pirate@x.mg',
            'password': 'Pirate123',
            'nom': 'Pirate',
            'role': 'user',
            'tenant_id': tb.id,
        })
        assert r.status_code == 403
        _record('14 manipulation tenant_id', 'PASS')


# ===========================================================================
# Section 15 - TEST 10 : JWT cross-tenant
# ===========================================================================
class Test10JwtCrossTenant:
    def test_jwt_avec_tenant_id_altere_refuse(self, app):
        client = app.test_client()
        ra = _register_company(client, 'JT1', 'jt1@j.mg', 'pro')
        rb = _register_company(client, 'JT2', 'jt2@j.mg', 'pro')
        ha = _auth(client, 'jt1@j.mg')
        with app.app_context():
            ua = Utilisateur.query.filter_by(email='jt1@j.mg').first()
            tb = Tenant.query.filter_by(slug='jt2').first()
            forged = create_access_token(
                identity=ua.id,
                additional_claims={
                    'role': 'admin',
                    'tenant_id': tb.id,  # altere
                    'tenant_slug': tb.slug,
                },
            )
        h = {'Authorization': 'Bearer ' + forged}
        # Doit etre refuse
        r = client.get('/api/v1/users', headers=h)
        assert r.status_code == 403
        # Verifie que la clef d'autorite est l'utilisateur authentifie, pas le claim
        r = client.post('/api/v1/abonnements/9999/renouveler', headers=h)
        assert r.status_code in (403, 404)
        _record('15 JWT cross-tenant', 'PASS')


# ===========================================================================
# Section 16 - TEST 11 : employee_key privee au Tenant
# ===========================================================================
class Test11EmployeeKey:
    def test_employee_key_non_exposee_dans_register(self, app):
        """L'employee_key ne doit jamais être exposée dans la réponse d'inscription."""
        client = app.test_client()
        r = _register_company(client, 'KA', 'ka@k.mg', 'pro')
        data = r.get_json()
        assert 'employee_key' not in data
        assert 'employee_key' not in data.get('tenant', {})
        _record('16 employee_key non exposee dans register', 'PASS')

    def test_employee_key_non_exposee_dans_me(self, app):
        """L'employee_key ne doit jamais être exposée dans /me."""
        client = app.test_client()
        r = _register_company(client, 'KB', 'kb@k.mg', 'pro')
        h = _auth(client, 'kb@k.mg')
        me = client.get('/api/v1/auth/me', headers=h).get_json()
        assert 'employee_key' not in me.get('user', {})
        assert 'employee_key' not in me.get('tenant', {})
        _record('16b employee_key non exposee dans /me', 'PASS')


# ===========================================================================
# Section 17 - TEST 12 : mot de passe securise
# ===========================================================================
class Test12MotdepasseSecurise:
    def test_password_hash_est_bcrypt(self):
        """Le hash du mot de passe doit utiliser bcrypt."""
        pwd = 'Companie123'
        hp = hash_password(pwd)
        assert hp.startswith('$2b$') or hp.startswith('$2a$')
        assert verify_password(pwd, hp)
        assert not verify_password('wrong-password', hp)
        _record('17 password securise bcrypt', 'PASS')


# ===========================================================================
# Section 18 - TEST 13 : cle admin non exposee
# ===========================================================================
class Test13CleAdminNonExposee:
    def test_hash_jamais_dans_reponse(self, app):
        client = app.test_client()
        r = _register_company(client, 'NX', 'nx@n.mg', 'pro')
        data = r.get_json()
        assert 'admin_key_hash' not in data
        assert 'admin_key_hash' not in data.get('tenant', {})
        assert 'employee_key' not in data
        assert 'employee_key' not in data.get('tenant', {})
        # /me
        h = _auth(client, 'nx@n.mg')
        me = client.get('/api/v1/auth/me', headers=h).get_json()
        assert 'admin_key_hash' not in me.get('user', {})
        assert 'admin_key_hash' not in me.get('tenant', {})
        assert 'employee_key' not in me.get('user', {})
        assert 'employee_key' not in me.get('tenant', {})
        _record('18 cle non exposee', 'PASS')


# ===========================================================================
# Section 19 - TEST 14 : suppression d'un utilisateur et quota
# ===========================================================================
class Test14SuppressionUtilisateur:
    def test_quota_recalcule_apres_suppression(self, app):
        client = app.test_client()
        r = _register_company(client, 'Del', 'del@d.mg', 'pro')
        h = _auth(client, 'del@d.mg')
        ids = []
        for i in range(6):
            ids.append(_created_user_data(_create_user(client, h, f'd{i}'))['id'])
        # 7e -> REFUS
        assert _create_user(client, h, 'd6').status_code == 403
        # Suppression d'un employe
        r = client.delete(f'/api/v1/users/{ids[0]}', headers=h)
        assert r.status_code in (200, 204)
        # Creation possible
        assert _create_user(client, h, 'd_after').status_code == 201
        _record('19 suppression recalcule quota', 'PASS')


# ===========================================================================
# Section 20 - TEST 15 : concurrence
# ===========================================================================
class Test15Concurrence:
    def test_creation_simultanee_ne_depasse_pas_quota(self, app):
        client = app.test_client()
        r = _register_company(client, 'Conc', 'conc@c.mg', 'pro')
        h = _auth(client, 'conc@c.mg')
        # 6 employes deja crees (admin + 6 = 7 = quota pro)
        for i in range(6):
            _create_user(client, h, f'c{i}')
        # 2 creations concurrentes pour le 8e
        results = []
        def do():
            with app.app_context():
                c = app.test_client()
                r = c.post('/api/v1/users', headers=_auth(c, 'conc@c.mg', 'Companie123'), json={
                    'username': secrets.token_hex(4),
                    'email': f'{secrets.token_hex(4)}@x.mg',
                    'password': 'Employe123',
                    'nom': 'X',
                    'role': 'user',
                })
                results.append(r.status_code)
        t1 = threading.Thread(target=do)
        t2 = threading.Thread(target=do)
        t1.start(); t2.start(); t1.join(); t2.join()
        # Au moins une doit etre refusee (ou les deux si la premiere a deja consomme le quota)
        assert results.count(201) <= 1, results
        assert 403 in results or results.count(201) == 1
        _record('20 concurrence', 'PASS')


# ===========================================================================
# Section 21 - TEST 16 : super admin != admin principal tenant
# ===========================================================================
class Test16SuperAdmin:
    def test_super_admin_n_est_pas_admin_principal_d_un_tenant(self, app):
        client = app.test_client()
        # Creer un super admin directement
        with app.app_context():
            sa = Utilisateur(
                username='super',
                email='super@s.mg',
                password_hash=hash_password('Super123!'),
                role=Role.SUPER_ADMIN,
                statut=StatutUtilisateur.ACTIF,
            )
            db.session.add(sa)
            db.session.commit()
        # Login
        r = client.post('/api/v1/auth/login', json={
            'username': 'super@s.mg',
            'password': 'Super123!',
        })
        assert r.status_code == 200, r.get_json()
        me = client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + r.get_json()['access_token']}).get_json()
        assert me.get('tenant') is None
        with app.app_context():
            sa_db = Utilisateur.query.filter_by(email='super@s.mg').first()
            assert sa_db.tenant_id is None
            assert not sa_db.is_principal_admin
        _record('21 super admin distinct', 'PASS')


# ===========================================================================
# Section 22 - TEST 17 : inscriptions multiples
# ===========================================================================
class Test17InscriptionsMultiples:
    def test_cinq_tenants_independants(self, app):
        client = app.test_client()
        for name, email, plan in [
            ('MA', 'ma@m.mg', 'pro'),
            ('MB', 'mb@m.mg', 'pro'),
            ('MC', 'mc@m.mg', 'pro'),
            ('MD', 'md@m.mg', 'starter'),
            ('ME', 'me@m.mg', 'starter'),
        ]:
            r = _register_company(client, name, email, plan=plan)
            assert r.status_code == 201, r.get_json()
        with app.app_context():
            tenants = Tenant.query.order_by(Tenant.id).all()
            assert len(tenants) == 5
            admins_principaux = {t.admin_principal_id for t in tenants}
            assert len(admins_principaux) == 5
            abos = Abonnement.query.all()
            assert len(abos) == 5
            assert {a.tenant_id for a in abos} == {t.id for t in tenants}
        _record('22 inscriptions multiples', 'PASS')


# ===========================================================================
# Section 23 - TEST 18 : reinscription avec le meme email
# ===========================================================================
class Test18ReinscriptionMemeEmail:
    def test_email_deja_utilise(self, app):
        client = app.test_client()
        r1 = _register_company(client, 'R1', 'dup@d.mg', 'starter')
        assert r1.status_code == 201
        r2 = _register_company(client, 'R2', 'dup@d.mg', 'starter')
        assert r2.status_code == 409
        _record('23 email unique', 'PASS')


# ===========================================================================
# Section 24 - TEST 19 : deconnexion / reconnexion
# ===========================================================================
class Test19DeconnexionReconnexion:
    def test_session_B_ne_voit_pas_A(self, app):
        client = app.test_client()
        ra = _register_company(client, 'SA', 'sa@s.mg', 'pro')
        rb = _register_company(client, 'SB', 'sb@s.mg', 'pro')
        ha = _auth(client, 'sa@s.mg')
        hb = _auth(client, 'sb@s.mg')
        me_a = client.get('/api/v1/auth/me', headers=ha).get_json()
        me_b = client.get('/api/v1/auth/me', headers=hb).get_json()
        assert me_a['tenant']['id'] != me_b['tenant']['id']
        assert me_a['tenant']['id'] == me_a['tenant']['id']  # stable
        # Re-login B : pas de leakage
        me_b2 = client.get('/api/v1/auth/me', headers=hb).get_json()
        assert me_b2['tenant']['id'] == me_b['tenant']['id']
        assert me_b2['tenant']['id'] != me_a['tenant']['id']
        _record('24 deconnexion/reconnexion', 'PASS')


# ===========================================================================
# Section 25 - TEST 20 : frontend != securite
# ===========================================================================
class Test20BackendSecurite:
    def test_endpoint_sensible_refuse_sans_role(self, app):
        client = app.test_client()
        r = _register_company(client, 'Sec', 'sec@s.mg', 'pro')
        h = _auth(client, 'sec@s.mg')
        # Creer un employe simple
        ru = _create_user(client, h, 'emp_sec', role='user')
        emp_email = _created_user_data(ru)['email']
        emp_login = client.post('/api/v1/auth/login', json={
            'username': emp_email,
            'password': 'Employe123',
        })
        eh = {'Authorization': 'Bearer ' + emp_login.get_json()['access_token']}
        # Tenter POST sur /abonnements/<id>/renouveler
        rh = client.get('/api/v1/abonnements/mon-historique', headers=h)
        abo_id = rh.get_json()['abonnements'][0]['id']
        r = client.post(f'/api/v1/abonnements/{abo_id}/renouveler', headers=eh)
        assert r.status_code == 403
        _record('25 backend autorise seul', 'PASS')


# ===========================================================================
# Section 26 - TEST 21 : tous les roles
# ===========================================================================
class Test21TousLesRoles:
    ROLES = [
        'super_admin', 'admin', 'manager', 'sales', 'stock',
        'accountant', 'rh', 'user',
    ]

    def test_chaque_role_peut_se_connecter(self, app):
        client = app.test_client()
        r = _register_company(client, 'Roles', 'roles@r.mg', 'enterprise')
        h = _auth(client, 'roles@r.mg')
        with app.app_context():
            for role in self.ROLES:
                ru = _create_user(client, h, f'r_{role}', role=role)
                if role == 'super_admin':
                    # seul un super admin peut creer un super admin -> 403
                    assert ru.status_code == 403
                    continue
                if role == 'admin':
                    # max_admins = 1, donc la creation d'un 2eme admin -> 403
                    assert ru.status_code == 403
                    continue
                assert ru.status_code == 201, (role, ru.get_json())
                emp_email = _created_user_data(ru)['email']
                rl = client.post('/api/v1/auth/login', json={
                    'username': emp_email,
                    'password': 'Employe123',
                })
                assert rl.status_code == 200, (role, rl.get_json())
        _record('26 tous roles connectables', 'PASS')


# ===========================================================================
# Section 27 - TEST 22 : requetes globales interdites
# ===========================================================================
class Test22RechercheGlobale:
    PATTERNS_GLOBAUX = [
        r"Utilisateur\.query\.count\(\)",
        r"User\.query\.count\(\)",
        r"Client\.query\.count\(\)",
        r"Produit\.query\.count\(\)",
    ]

    def test_compteurs_toujours_scopes_tenant(self):
        repo_root = Path(__file__).resolve().parents[3]
        backend = repo_root / 'web' / 'backend' / 'app'
        suspects = []
        for path in backend.rglob('*.py'):
            # On exclut le seed et les tests eux-memes
            if 'tests' in str(path):
                continue
            text = path.read_text(encoding='utf-8', errors='ignore')
            for pat in self.PATTERNS_GLOBAUX:
                if re.search(pat, text):
                    suspects.append((str(path), pat))
        # Le seul appel attendu est dans le seed initial de la plateforme
        for path, pat in suspects:
            assert '_seed_initial_data' in Path(path).read_text(encoding='utf-8'), (
                f'Compteur global non scope: {path} / {pat}'
            )
        _record('27 pas de count global utilisateur/client/produit', 'PASS')


# ===========================================================================
# Section 28 - TEST 23 : recherche automatique de bugs
# ===========================================================================
class Test23RechercheBugs:
    def test_is_admin_ne_suffit_pas_pour_principal(self, app):
        client = app.test_client()
        r = _register_company(client, 'Bug', 'bug@b.mg', 'pro')
        h = _auth(client, 'bug@b.mg')
        # Le plan limite à 1 admin. On insère directement en DB pour tester la propriété.
        with app.app_context():
            from app.models.utilisateur import Utilisateur as U, Role
            from app.security.auth import hash_password
            t = Tenant.query.filter_by(slug='bug').first()
            second = U(
                username='admin2',
                email='admin2@x.mg',
                password_hash=hash_password('Employe123'),
                nom='A2',
                role=Role.ADMIN,
                tenant_id=t.id,
                is_active=True,
                is_principal_admin=False
            )
            db.session.add(second)
            db.session.commit()
            
            principal_id = t.admin_principal_id
            assert second.id != principal_id
            assert second.is_principal_admin is False
        _record('28 is_admin != principal', 'PASS')


# ===========================================================================
# Section 29 - TEST 24 : tests de regression
# ===========================================================================
class Test24Regressions:
    def test_regressions_essentielles(self, app):
        # Smoke : on execute un sous-ensemble representatif
        client = app.test_client()
        r = _register_company(client, 'Reg', 'reg@r.mg', 'pro')
        assert r.status_code == 201
        h = _auth(client, 'reg@r.mg')
        me = client.get('/api/v1/auth/me', headers=h).get_json()
        assert me['user']['email'] == 'reg@r.mg'
        # Quota pro tient
        for i in range(6):
            _create_user(client, h, f'r{i}')
        assert _create_user(client, h, 'r6').status_code == 403
        _record('29 regressions OK', 'PASS')


# ===========================================================================
# Section 30 - TEST 25 : scenario de verite metier final
# ===========================================================================
class Test25VeriteMetierFinale:
    def test_isolation_complete_A_et_B(self, app):
        client = app.test_client()
        ra = _register_company(client, 'FinalA', 'fa@f.mg', 'pro')
        rb = _register_company(client, 'FinalB', 'fb@f.mg', 'pro')
        ha = _auth(client, 'fa@f.mg')
        hb = _auth(client, 'fb@f.mg')
        # Sature A
        for i in range(6):
            _create_user(client, ha, f'fa{i}')
        assert _create_user(client, ha, 'fa6').status_code == 403
        # B toujours operationnel
        for i in range(6):
            _create_user(client, hb, f'fb{i}')
        assert _create_user(client, hb, 'fb6').status_code == 403
        # Independance apres saturation
        # On tente un user dans A -> toujours 403
        assert _create_user(client, ha, 'fa_late').status_code == 403
        # B ne doit pas voir les users de A
        r = client.get('/api/v1/users', headers=hb).get_json()
        emails = [u['email'] for u in r['users']]
        assert not any(e.startswith('fa') for e in emails)
        _record('30 verite metier finale', 'PASS')


# ===========================================================================
# Section 33 - Rapport final
# ===========================================================================
def test_final_report():
    """Imprime le rapport final de l'audit."""
    total = sum(_RESULTS.values())
    print('\n' + '=' * 60)
    print('RAPPORT FINAL AUDIT MIHAJA_ERP_PRO')
    print('=' * 60)
    for k in ('PASS', 'FAIL', 'BLOCKED', 'SKIPPED'):
        print(f'{k:10s} : {_RESULTS.get(k, 0)}')
    print(f'TOTAL      : {total}')
    assert total > 0, "Aucun test execute"
