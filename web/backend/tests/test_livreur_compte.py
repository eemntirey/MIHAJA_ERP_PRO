import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur, StatutAdmin
from app.models.livreur import Livreur
from app.models.livraison import Livraison
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from app.models.admin_device import AdminDevice, StatutDevice


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        yield app
        db.drop_all()


def _make_context():
    ta = Tenant.query.filter_by(slug='tenant-a').first()
    tb = Tenant.query.filter_by(slug='tenant-b').first()
    if not ta:
        ta = Tenant(nom='Tenant A', slug='tenant-a', domaine='a.local', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(ta)
    if not tb:
        tb = Tenant(nom='Tenant B', slug='tenant-b', domaine='b.local', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(tb)
    db.session.flush()

    if not Abonnement.query.filter_by(tenant_id=ta.id).first():
        db.session.add(Abonnement(
            tenant_id=ta.id, montant=100.0, plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
        ))
    if not Abonnement.query.filter_by(tenant_id=tb.id).first():
        db.session.add(Abonnement(
            tenant_id=tb.id, montant=100.0, plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
        ))

    admin_a = Utilisateur.query.filter_by(username='admin_a').first()
    admin_b = Utilisateur.query.filter_by(username='admin_b').first()
    super_admin = Utilisateur.query.filter_by(username='super').first()
    if not admin_a:
        admin_a = Utilisateur(
            username='admin_a', email='admin@a.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
            admin_statut=StatutAdmin.ACTIVE,
        )
        db.session.add(admin_a)
        db.session.flush()
        device_a = AdminDevice(
            user_id=admin_a.id,
            device_id='device-a-123',
            device_name='Device A',
            statut=StatutDevice.ACTIVE,
        )
        db.session.add(device_a)
        admin_a.device_id = 'device-a-123'
    if not admin_b:
        admin_b = Utilisateur(
            username='admin_b', email='admin@b.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tb.id,
            admin_statut=StatutAdmin.ACTIVE,
        )
        db.session.add(admin_b)
        db.session.flush()
        device_b = AdminDevice(
            user_id=admin_b.id,
            device_id='device-b-456',
            device_name='Device B',
            statut=StatutDevice.ACTIVE,
        )
        db.session.add(device_b)
        admin_b.device_id = 'device-b-456'
    if not super_admin:
        super_admin = Utilisateur(
            username='super', email='super@x.mg',
            password_hash=hash_password('Super123!'), role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
    db.session.commit()
    return ta, tb, admin_a, admin_b, super_admin


def _login(client, identifier, password, tenant_slug=None, device_id=None):
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    if device_id:
        payload['device_id'] = device_id
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestLivreurCompte:
    def test_a_livreur_sans_compte(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a', device_id='device-a-123')

        with app.app_context():
            livreur = Livreur(nom='Dupont', prenom='Jean', tenant_id=Tenant.query.filter_by(slug='tenant-a').first().id)
            db.session.add(livreur)
            db.session.commit()
            lid = livreur.id

        r = client.get(f'/api/v1/livreurs/{lid}', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert data['utilisateur_id'] is None

    def test_b_association_valide(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a', device_id='device-a-123')

        with app.app_context():
            user = Utilisateur(
                username='livreur_a', email='livreur_a@a.mg',
                password_hash=hash_password('Livreur123!'),
                role=Role.LIVREUR, statut=StatutUtilisateur.ACTIF,
                tenant_id=ta.id,
            )
            db.session.add(user)
            db.session.flush()
            livreur = Livreur(nom='Dupont', prenom='Jean', tenant_id=ta.id)
            db.session.add(livreur)
            db.session.commit()
            lid = livreur.id
            uid = user.id

        r = client.post(f'/api/v1/livreurs/{lid}/associer-utilisateur', json={'utilisateur_id': uid}, headers=headers)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data['utilisateur_id'] == uid

        with app.app_context():
            assert Livreur.query.get(lid).utilisateur_id == uid

    def test_c_association_cross_tenant(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a', device_id='device-a-123')

        with app.app_context():
            user_b = Utilisateur(
                username='livreur_b', email='livreur_b@b.mg',
                password_hash=hash_password('Livreur123!'),
                role=Role.LIVREUR, statut=StatutUtilisateur.ACTIF,
                tenant_id=tb.id,
            )
            db.session.add(user_b)
            db.session.flush()
            livreur_a = Livreur(nom='Dupont', prenom='Jean', tenant_id=ta.id)
            db.session.add(livreur_a)
            db.session.commit()
            lid = livreur_a.id
            uid = user_b.id

        r = client.post(f'/api/v1/livreurs/{lid}/associer-utilisateur', json={'utilisateur_id': uid}, headers=headers)
        assert r.status_code == 403, r.get_json()

    def test_d_compte_deja_associe(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a', device_id='device-a-123')

        with app.app_context():
            user = Utilisateur(
                username='livreur_a', email='livreur_a@a.mg',
                password_hash=hash_password('Livreur123!'),
                role=Role.LIVREUR, statut=StatutUtilisateur.ACTIF,
                tenant_id=ta.id,
            )
            db.session.add(user)
            db.session.flush()
            livreur1 = Livreur(nom='Dupont', prenom='Jean', tenant_id=ta.id)
            livreur2 = Livreur(nom='Martin', prenom='Marie', tenant_id=ta.id)
            db.session.add_all([livreur1, livreur2])
            db.session.commit()
            lid1 = livreur1.id
            lid2 = livreur2.id
            uid = user.id

        r = client.post(f'/api/v1/livreurs/{lid1}/associer-utilisateur', json={'utilisateur_id': uid}, headers=headers)
        assert r.status_code == 200, r.get_json()

        r = client.post(f'/api/v1/livreurs/{lid2}/associer-utilisateur', json={'utilisateur_id': uid}, headers=headers)
        assert r.status_code == 409, r.get_json()

    def test_e_isolation_livraisons(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()

        with app.app_context():
            user_a = Utilisateur(
                username='livreur_a', email='livreur_a@a.mg',
                password_hash=hash_password('Livreur123!'),
                role=Role.LIVREUR, statut=StatutUtilisateur.ACTIF,
                tenant_id=ta.id,
            )
            user_b = Utilisateur(
                username='livreur_b', email='livreur_b@a.mg',
                password_hash=hash_password('Livreur123!'),
                role=Role.LIVREUR, statut=StatutUtilisateur.ACTIF,
                tenant_id=ta.id,
            )
            db.session.add_all([user_a, user_b])
            db.session.flush()
            livreur_a = Livreur(nom='Dupont', prenom='Jean', tenant_id=ta.id, utilisateur_id=user_a.id)
            livreur_b = Livreur(nom='Martin', prenom='Marie', tenant_id=ta.id, utilisateur_id=user_b.id)
            db.session.add_all([livreur_a, livreur_b])
            db.session.flush()
            liv_a = Livraison(tenant_id=ta.id, livreur_id=livreur_a.id, statut='en_attente', adresse_livraison='Addr A')
            liv_b = Livraison(tenant_id=ta.id, livreur_id=livreur_b.id, statut='en_attente', adresse_livraison='Addr B')
            db.session.add_all([liv_a, liv_b])
            db.session.commit()
            lid_a = liv_a.id
            lid_b = liv_b.id

        headers_a = _login(client, 'livreur_a', 'Livreur123!', 'tenant-a', device_id='device-a-123')
        headers_b = _login(client, 'livreur_b', 'Livreur123!', 'tenant-a', device_id='device-a-123')

        r = client.get('/api/v1/livreurs/moi/livraisons', headers=headers_a)
        assert r.status_code == 200
        data = r.get_json()
        ids = {l['id'] for l in data['livraisons']}
        assert lid_a in ids
        assert lid_b not in ids

        r = client.get(f'/api/v1/livreurs/moi/livraisons/{lid_b}', headers=headers_a)
        assert r.status_code == 404

        r = client.post(f'/api/v1/livreurs/moi/livraisons/{lid_a}/statut', json={'statut': 'livree'}, headers=headers_a)
        assert r.status_code == 201, r.get_json()

    def test_f_isolation_tenant(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()

        with app.app_context():
            user_a = Utilisateur(
                username='livreur_a', email='livreur_a@a.mg',
                password_hash=hash_password('Livreur123!'),
                role=Role.LIVREUR, statut=StatutUtilisateur.ACTIF,
                tenant_id=ta.id,
            )
            db.session.add(user_a)
            db.session.flush()
            livreur_a = Livreur(nom='Dupont', prenom='Jean', tenant_id=ta.id, utilisateur_id=user_a.id)
            db.session.add(livreur_a)
            db.session.flush()
            liv_b = Livraison(tenant_id=tb.id, statut='en_attente', adresse_livraison='Addr B')
            db.session.add(liv_b)
            db.session.commit()
            lid_b = liv_b.id

        headers_a = _login(client, 'livreur_a', 'Livreur123!', 'tenant-a', device_id='device-a-123')

        r = client.get(f'/api/v1/livreurs/moi/livraisons/{lid_b}', headers=headers_a)
        assert r.status_code == 404

        r = client.post(f'/api/v1/livreurs/moi/livraisons/{lid_b}/statut', json={'statut': 'livree'}, headers=headers_a)
        assert r.status_code == 404

    def test_g_regression_roles_existants(self, app):
        _make_context()
        client = app.test_client()
        headers_admin = _login(client, 'admin_a', 'Admin123!', 'tenant-a', device_id='device-a-123')

        r = client.get('/api/v1/users', headers=headers_admin)
        assert r.status_code == 200

        r = client.get('/api/v1/livraisons', headers=headers_admin)
        assert r.status_code == 200

        r = client.post('/api/v1/livraisons', json={'adresse_livraison': 'Test'}, headers=headers_admin)
        assert r.status_code == 201, r.get_json()
