import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password


EMPLOYEE_ROLES = [
    (Role.USER, 'user', 'Utilisateur'),
    (Role.MANAGER, 'manager', 'Manager'),
    (Role.SALES, 'sales', 'Commercial'),
    (Role.STOCK, 'stock', 'Stock'),
    (Role.ACCOUNTANT, 'accountant', 'Comptable'),
    (Role.RH, 'rh', 'RH'),
]


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
    ta = Tenant(nom='Tenant A', slug='tenant-a', statut=StatutTenant.ACTIF, plan='pro')
    db.session.add(ta)
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=ta.id, montant=100.0, plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=365),
        statut=StatutAbonnement.ACTIF,
    ))
    admin_a = Utilisateur(
        username='admin_a', email='admin@a.mg',
        password_hash=hash_password('Admin123!'), role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
    )
    db.session.add(admin_a)
    db.session.commit()
    return ta, admin_a


def _login(client, identifier, password, tenant_slug=None):
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestCreationEmployeSystemeRoles:
    """Vérifie qu'un rôle système (non-custom) n'est jamais traité comme un custom_role.

    Régression : le frontend envoie `custom_role_id: ''` quand aucun rôle custom
    n'est sélectionné. Le backend ne doit pas déclencher la logique
    _validate_custom_role dans ce cas.
    """

    @pytest.mark.parametrize(
        'role_enum,role_value,label',
        [(r, v, l) for r, v, l in EMPLOYEE_ROLES],
        ids=[v for _, v, _ in EMPLOYEE_ROLES],
    )
    def test_creation_avec_role_systeme_sans_custom_role_id(self, app, role_enum, role_value, label):
        ta, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post(
            '/api/v1/users',
            headers=headers,
            json={
                'username': f'emp_{role_value}',
                'email': f'emp_{role_value}@a.mg',
                'password': 'Pass123!',
                'role': role_value,
                'statut': 'actif',
            },
        )
        assert r.status_code == 201, r.get_json()
        data = r.get_json()
        assert data['role'] == role_value
        assert data['tenant_id'] == ta.id
        assert data['custom_role_id'] is None

        created = Utilisateur.query.filter_by(username=f'emp_{role_value}').first()
        assert created is not None
        assert created.role == role_enum
        assert created.custom_role_id is None

    @pytest.mark.parametrize(
        'role_enum,role_value,label',
        [(r, v, l) for r, v, l in EMPLOYEE_ROLES],
        ids=[v for _, v, _ in EMPLOYEE_ROLES],
    )
    def test_creation_avec_role_systeme_et_custom_role_id_vide(self, app, role_enum, role_value, label):
        """Cas reproduisant le bug initial : le formulaire envoie custom_role_id=''."""
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post(
            '/api/v1/users',
            headers=headers,
            json={
                'username': f'emp2_{role_value}',
                'email': f'emp2_{role_value}@a.mg',
                'password': 'Pass123!',
                'role': role_value,
                'statut': 'actif',
                'custom_role_id': '',
            },
        )
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['role'] == role_value
        assert r.get_json()['custom_role_id'] is None
        assert 'Role personnalise introuvable' not in str(r.get_json())

    @pytest.mark.parametrize(
        'role_enum,role_value,label',
        [(r, v, l) for r, v, l in EMPLOYEE_ROLES],
        ids=[v for _, v, _ in EMPLOYEE_ROLES],
    )
    def test_creation_avec_role_systeme_et_custom_role_id_explicit_null(self, app, role_enum, role_value, label):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post(
            '/api/v1/users',
            headers=headers,
            json={
                'username': f'emp3_{role_value}',
                'email': f'emp3_{role_value}@a.mg',
                'password': 'Pass123!',
                'role': role_value,
                'statut': 'actif',
                'custom_role_id': None,
            },
        )
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['custom_role_id'] is None

    def test_creation_avec_custom_role_id_invalide_retourne_404(self, app):
        """Un custom_role_id non-numérique doit toujours produire l'erreur 'Role personnalise introuvable'."""
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post(
            '/api/v1/users',
            headers=headers,
            json={
                'username': 'bad',
                'email': 'bad@a.mg',
                'password': 'Pass123!',
                'role': 'sales',
                'statut': 'actif',
                'custom_role_id': 'not-an-int',
            },
        )
        assert r.status_code == 404
        assert 'Role personnalise introuvable' in r.get_json()['message']

    def test_utilisateur_apparait_dans_liste_apres_creation(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers, json={
            'username': 'commercial1', 'email': 'commercial1@a.mg',
            'password': 'Pass123!', 'role': 'sales', 'statut': 'actif',
        })
        assert r.status_code == 201
        created_id = r.get_json()['id']

        r = client.get('/api/v1/users', headers=headers)
        assert r.status_code == 200
        ids = [u['id'] for u in r.get_json()['users']]
        assert created_id in ids
        listed = next(u for u in r.get_json()['users'] if u['id'] == created_id)
        assert listed['role'] == 'sales'

    def test_modification_avec_custom_role_id_vide_n_ecrase_pas(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers, json={
            'username': 'modif', 'email': 'modif@a.mg',
            'password': 'Pass123!', 'role': 'sales', 'statut': 'actif',
        })
        assert r.status_code == 201
        user_id = r.get_json()['id']

        r = client.put(f'/api/v1/users/{user_id}', headers=headers, json={
            'role': 'stock',
            'custom_role_id': '',
        })
        assert r.status_code == 200, r.get_json()
        assert r.get_json()['role'] == 'stock'
        assert r.get_json()['custom_role_id'] is None