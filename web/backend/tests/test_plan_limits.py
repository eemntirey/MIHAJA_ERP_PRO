from tests._db_utils import test_database_url
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
    monkeypatch.setenv('DATABASE_URL', test_database_url())
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        # Ces tests valident les limites du MODE COMMERCIAL (toggle ACTIF) :
        # les quotas, modules et permissions restreints ne s'appliquent que
        # lorsque l'abonnement est actif (en mode dÃ©couverte ils sont levÃ©s).
        from app.models.platform_config import PlatformConfig
        cfg = PlatformConfig.get_config()
        cfg.is_subscription_active = True
        db.session.commit()
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
        assert 'employÃƒÂ©s' in r.get_json()['message']

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
        assert 'employÃƒÂ©s' in r.get_json()['message']

    def test_admin_can_still_list_users_when_employee_limit_reached(self, app):
        """La limite d'employes bloque la creation mais pas la consultation
        de la liste des utilisateurs (Ã‚Â§34 : la limite s'affiche, la liste
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
        assert 'employÃƒÂ©s' in r.get_json()['message']

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


class TestAlignmentDateFin:
    """P0 guardes tenant : abonnement ACTIF mais EXPIRE != abonnement actif.

    `tenant_required` (portail abonnement) exigeait deja date_fin > now ;
    `plan_limits` l'ignorait (un abonnement expire continuait de figer les
    limites du plan). Unifie : expiration => repli sur la configuration du
    plan du tenant (plus de limites figees pour un abonnement expire).
    """

    def test_abonnement_expire_plus_de_limites_figees(self, app):
        from app.security.plan_limits import (
            _get_active_abonnement, _get_limits, _get_modules,
        )
        tenant, admin = _make_tenant_with_abonnement(
            plan='pro', max_employees=3, modules='rh,stocks,produits'
        )
        abo = Abonnement.query.filter_by(tenant_id=tenant.id).first()
        abo.date_fin = datetime.utcnow() - timedelta(days=1)
        db.session.commit()

        assert _get_active_abonnement(tenant) is None
        limits = _get_limits(tenant)
        assert limits['max_employees'] == 6  # repli plan 'pro' au lieu des 3 figes
        modules = _get_modules(tenant)
        assert 'achats' in modules  # module hors abonnement (repli plan pro)

    def test_abonnement_actif_conserve_ses_limites(self, app):
        from app.security.plan_limits import (
            _get_active_abonnement, _get_limits,
        )
        tenant, admin = _make_tenant_with_abonnement(
            plan='pro', max_employees=3
        )
        assert _get_active_abonnement(tenant) is not None
        limits = _get_limits(tenant)
        assert limits['max_employees'] == 3

def test_plan_pricing_persists_across_config_reload(app):
    """Une modification de prix/durée survit au rechargement de PLAN_CONFIG."""
    from app.models.platform_config import PlatformConfig
    from app.security.plans import (
        PLAN_CONFIG,
        _persist_plan_override,
        get_plan_config,
        get_public_plans,
    )

    with app.app_context():
        cfg = PlatformConfig.get_config()
        cfg.plans_json = None
        db.session.commit()

        original = dict(PLAN_CONFIG['pro'])
        try:
            _persist_plan_override('pro', prix=17777, duree_jours=45)
            # Simule un redémarrage : on remet les valeurs mémoire par défaut.
            PLAN_CONFIG['pro']['prix'] = 15000
            PLAN_CONFIG['pro']['duree_jours'] = 30

            effective = get_plan_config('pro')
            assert effective['prix'] == 17777
            assert effective['duree_jours'] == 45

            public = next(p for p in get_public_plans() if p['code'] == 'pro')
            assert public['prix'] == 17777
            assert public['duree_jours'] == 45
        finally:
            cfg = PlatformConfig.get_config()
            cfg.plans_json = None
            db.session.commit()
            PLAN_CONFIG['pro'].update(original)

def test_starter_plan_contract(app):
    """Le plan Starter reste disponible et exposé avec ses limites."""
    from app.security.plans import get_plan_config, get_public_plans

    with app.app_context():
        cfg = get_plan_config('starter')
        assert cfg['prix'] == 5000
        assert cfg['duree_jours'] == 30
        assert cfg['max_utilisateurs'] == 3
        assert cfg['max_employees'] == 2
        assert 'starter' in {p['code'] for p in get_public_plans()}

def test_renewal_creates_pending_subscription_without_replacing_active(app):
    """Un renouvellement ne doit pas couper l'abonnement courant avant paiement."""
    from app.services.abonnement_service import AbonnementService
    from app.models.paiement import Paiement, TypePaiement, StatutPaiement

    with app.app_context():
        tenant, admin = _make_tenant_with_abonnement(plan='pro')
        current = Abonnement.query.filter_by(
            tenant_id=tenant.id,
            statut=StatutAbonnement.ACTIF,
            is_active=True,
        ).one()

        requested, paiement = AbonnementService.renew_subscription(
            current.id,
            new_plan='enterprise',
            payment_method='MVOLA',
        )

        assert current.statut == StatutAbonnement.ACTIF
        assert tenant.plan == 'pro'
        assert requested.id != current.id
        assert requested.plan == 'enterprise'
        assert requested.statut == StatutAbonnement.EN_ATTENTE
        assert paiement.subscription_id == requested.id
        assert paiement.type == TypePaiement.ABONNEMENT
        assert paiement.statut == StatutPaiement.EN_ATTENTE


def test_airt_money_provider_code_is_consistent(app):
    """Airtel doit utiliser AIRTEL_MONEY dans les flux Papi."""
    from app.services.papi.payment import PROVIDER_METHOD_MAP

    assert PROVIDER_METHOD_MAP['AIRTEL_MONEY'] == 'AIRTEL_MONEY'
