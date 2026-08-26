import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.audit_log import AuditLog, TypeActionAudit
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_context():
    """Crée deux tenants (A et B) + un admin + un abonnement actif pour le tenant A."""
    ta = Tenant(nom='Tenant A', slug='tenant-a', statut=StatutTenant.ACTIF, plan='pro')
    tb = Tenant(nom='Tenant B', slug='tenant-b', statut=StatutTenant.ACTIF, plan='pro')
    db.session.add_all([ta, tb])
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=ta.id, montant=100.0, plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    ))
    admin_a = Utilisateur(
        username='admin_a', email='admin@a.mg',
        password_hash=hash_password('Admin123!'), role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
    )
    super_admin = Utilisateur(
        username='super', email='super@x.mg',
        password_hash=hash_password('Super123!'), role=Role.SUPER_ADMIN,
        statut=StatutUtilisateur.ACTIF,
    )
    user_a = Utilisateur(
        username='user_a', email='ua@a.mg',
        password_hash=hash_password('User123!'), role=Role.USER,
        statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
    )
    user_b = Utilisateur(
        username='user_b', email='ub@b.mg',
        password_hash=hash_password('User123!'), role=Role.USER,
        statut=StatutUtilisateur.ACTIF, tenant_id=tb.id,
    )
    db.session.add_all([admin_a, super_admin, user_a, user_b])
    db.session.commit()
    return ta, admin_a, super_admin, user_a, user_b


def _login(client, identifier, password, tenant_slug=None):
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestUsersApiTenantIsolation:
    def test_admin_tenant_ne_voit_que_son_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.get('/api/v1/users', headers=headers)
        assert r.status_code == 200, r.get_json()
        users = r.get_json()['users']
        usernames = {u['username'] for u in users}
        # Seuls les utilisateurs du tenant A (et l'admin) sont visibles
        assert 'admin_a' in usernames
        assert 'user_a' in usernames
        # Pas de fuite cross-tenant ni de super admin global
        assert 'user_b' not in usernames
        assert 'super' not in usernames

    def test_admin_tenant_ne_peut_pas_lire_user_autre_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        user_b_id = Utilisateur.query.filter_by(username='user_b').first().id

        r = client.get(f'/api/v1/users/{user_b_id}', headers=headers)
        assert r.status_code == 404, r.get_json()

    def test_admin_tenant_est_scope_vers_son_propre_tenant(self, app):
        ta, admin_a, _, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'nouveau', 'email': 'nouveau@a.mg',
                              'password': 'Pass123!', 'role': 'sales', 'statut': 'actif'})
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == ta.id

    def test_admin_tenant_ne_peut_pas_creer_super_admin(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'evil', 'email': 'evil@x.mg',
                              'password': 'Pass123!', 'role': 'super_admin', 'statut': 'actif'})
        assert r.status_code == 403, r.get_json()

    def test_super_admin_voit_tous_les_utilisateurs(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.get('/api/v1/users', headers=headers)
        assert r.status_code == 200, r.get_json()
        users = r.get_json()['users']
        usernames = {u['username'] for u in users}
        assert {'admin_a', 'super', 'user_a', 'user_b'} <= usernames

    def test_roles_accessibles_par_admin_tenant(self, app):
        # Le module utilisateur charge aussi la liste des rôles pour les filtres/formulaires
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.get('/api/v1/roles', headers=headers)
        assert r.status_code == 200, r.get_json()
        assert 'roles' in r.get_json()


class TestUsersApiSecurity:
    def test_admin_tenant_ne_peut_pas_creer_user_autre_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        tb = Tenant.query.filter_by(slug='tenant-b').first()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'evil', 'email': 'evil@b.mg',
                              'password': 'Pass123!', 'tenant_id': tb.id})
        assert r.status_code == 403, r.get_json()

    def test_creation_user_tenant_inexistant_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'ghost', 'email': 'ghost@x.mg',
                              'password': 'Pass123!', 'tenant_id': 99999})
        assert r.status_code == 404, r.get_json()

    def test_creation_user_mot_de_passe_faible_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'faible', 'email': 'faible@a.mg',
                              'password': '1234567'})
        assert r.status_code == 400, r.get_json()

    def test_creation_user_mot_de_passe_sans_lettre_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'faible2', 'email': 'faible2@a.mg',
                              'password': '12345678'})
        assert r.status_code == 400, r.get_json()

    def test_creation_user_mot_de_passe_sans_chiffre_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'faible3', 'email': 'faible3@a.mg',
                              'password': 'abcdefgh'})
        assert r.status_code == 400, r.get_json()

    def test_creation_user_mot_de_passe_valide_ok(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'nouveau', 'email': 'nouveau@a.mg',
                              'password': 'Pass123!'})
        assert r.status_code == 201, r.get_json()

    def test_creation_user_created_by_renseigne(self, app):
        ta, admin_a, _, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'trace1', 'email': 'trace1@a.mg',
                              'password': 'Pass123!'})
        assert r.status_code == 201, r.get_json()
        created_id = r.get_json()['id']
        user = Utilisateur.query.get(created_id)
        assert user is not None
        assert user.created_by == admin_a.id

    def test_modification_user_updated_by_renseigne(self, app):
        ta, admin_a, _, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        user_a = Utilisateur.query.filter_by(username='user_a').first()

        r = client.put(f'/api/v1/users/{user_a.id}', headers=headers,
                       json={'nom': 'NouveauNom'})
        assert r.status_code == 200, r.get_json()
        updated_user = Utilisateur.query.get(user_a.id)
        assert updated_user.updated_by == admin_a.id

    def test_creation_user_audit_enregistre(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'audit1', 'email': 'audit1@a.mg',
                              'password': 'Pass123!'})
        assert r.status_code == 201, r.get_json()
        created_id = r.get_json()['id']
        log = AuditLog.query.filter_by(type_action=TypeActionAudit.CREATION_UTILISATEUR).first()
        assert log is not None
        assert 'audit1' in log.description

    def test_super_admin_peut_creer_user_tenant_existant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')
        ta = Tenant.query.filter_by(slug='tenant-a').first()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'supernew', 'email': 'supernew@a.mg',
                              'password': 'Pass123!', 'tenant_id': ta.id})
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == ta.id