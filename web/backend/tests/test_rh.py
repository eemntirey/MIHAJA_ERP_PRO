import pytest
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.employe import Employe
from app.models.stagiaire import Stagiaire
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from datetime import datetime, timedelta


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


def _make_tenant(slug, plan='pro'):
    tenant = Tenant(nom=slug, slug=slug, domaine=f'{slug}.local', statut=StatutTenant.ACTIF, plan=plan)
    db.session.add(tenant)
    db.session.commit()
    abonnement = Abonnement(
        tenant_id=tenant.id,
        plan=plan,
        statut=StatutAbonnement.ACTIF,
        date_debut=datetime.utcnow() - timedelta(days=30),
        date_fin=datetime.utcnow() + timedelta(days=30),
        modules='rh',
        max_employees=5,
        max_interns=2,
    )
    db.session.add(abonnement)
    db.session.commit()
    return tenant


def _make_user(tenant, username, role=Role.ADMIN):
    user = Utilisateur(
        username=username,
        email=f'{username}@example.com',
        password_hash=hash_password('Password123!'),
        nom=username,
        prenom=username,
        role=role,
        tenant_id=tenant.id,
        statut=StatutUtilisateur.ACTIF,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username, password, tenant_slug):
    payload = {'username': username, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


def test_create_stagiaire(app):
    tenant = _make_tenant('tenant-stg')
    user = _make_user(tenant, 'admin-stg')
    client = app.test_client()
    headers = _login(client, 'admin-stg', 'Password123!', 'tenant-stg')

    r = client.post('/api/v1/stagiaires', headers=headers, json={
        'matricule': 'STG-001',
        'nom': 'Dupont',
        'prenom': 'Jean',
        'etablissement': 'Université A',
        'formation': 'Informatique',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
        'statut': 'en_stage',
    })
    assert r.status_code == 201, r.get_json()
    data = r.get_json()
    assert data['matricule'] == 'STG-001'
    assert data['nom'] == 'Dupont'
    assert data['tenant_id'] == tenant.id


def test_cross_tenant_stagiaires_denied(app):
    ta = _make_tenant('tenant-a')
    tb = _make_tenant('tenant-b')
    _make_user(ta, 'admin_a', Role.ADMIN)
    _make_user(tb, 'admin_b', Role.ADMIN)
    client = app.test_client()
    headers_a = _login(client, 'admin_a', 'Password123!', 'tenant-a')

    with app.app_context():
        s_b = Stagiaire(nom='Stagiaire B', prenom='B', matricule='STG-B', tenant_id=tb.id, etablissement='Univ B')
        db.session.add(s_b)
        db.session.commit()
        sid_b = s_b.id

    r = client.get(f'/api/v1/stagiaires/{sid_b}', headers=headers_a)
    assert r.status_code == 404, r.get_json()

    r = client.put(f'/api/v1/stagiaires/{sid_b}', headers=headers_a, json={'nom': 'Hacked'})
    assert r.status_code == 404, r.get_json()

    r = client.delete(f'/api/v1/stagiaires/{sid_b}', headers=headers_a)
    assert r.status_code == 404, r.get_json()


def test_stagiaire_tuteur_meme_tenant(app):
    tenant = _make_tenant('tenant-tuteur')
    user = _make_user(tenant, 'admin-tuteur')
    client = app.test_client()
    headers = _login(client, 'admin-tuteur', 'Password123!', 'tenant-tuteur')

    with app.app_context():
        e = Employe(nom='Employe Tuteur', prenom='T', matricule='EMP-T', tenant_id=tenant.id, salaire_base=1000)
        db.session.add(e)
        db.session.commit()
        eid = e.id

    r = client.post('/api/v1/stagiaires', headers=headers, json={
        'matricule': 'STG-T',
        'nom': 'Stagiaire',
        'prenom': 'S',
        'etablissement': 'Univ',
        'formation': 'Info',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
        'tuteur_id': eid,
    })
    assert r.status_code == 201, r.get_json()


def test_stagiaire_tuteur_autre_tenant_refuse(app):
    ta = _make_tenant('tenant-a')
    tb = _make_tenant('tenant-b')
    _make_user(ta, 'admin_a', Role.ADMIN)
    _make_user(tb, 'admin_b', Role.ADMIN)
    client = app.test_client()
    headers_a = _login(client, 'admin_a', 'Password123!', 'tenant-a')

    with app.app_context():
        e_b = Employe(nom='Employe B', prenom='B', matricule='EMP-B', tenant_id=tb.id, salaire_base=1000)
        db.session.add(e_b)
        db.session.commit()
        eid_b = e_b.id

    r = client.post('/api/v1/stagiaires', headers=headers_a, json={
        'matricule': 'STG-X',
        'nom': 'Stagiaire',
        'prenom': 'S',
        'etablissement': 'Univ',
        'formation': 'Info',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
        'tuteur_id': eid_b,
    })
    assert r.status_code == 400, r.get_json()
    assert 'tuteur' in r.get_json()['message'].lower()


def test_employe_plan_limit(app):
    tenant = _make_tenant('tenant-limit', plan='gratuit')
    user = _make_user(tenant, 'admin-limit')
    client = app.test_client()
    headers = _login(client, 'admin-limit', 'Password123!', 'tenant-limit')

    with app.app_context():
        for i in range(5):
            e = Employe(nom=f'Employe {i}', prenom='E', matricule=f'EMP-{i}', tenant_id=tenant.id, salaire_base=1000)
            db.session.add(e)
        db.session.commit()

    r = client.post('/api/v1/employes', headers=headers, json={
        'matricule': 'EMP-OVER',
        'nom': 'Overflow',
        'prenom': 'O',
        'salaire_base': 1000,
    })
    assert r.status_code == 403, r.get_json()
    assert 'limite' in r.get_json()['message'].lower()


def test_stagiaire_plan_limit(app):
    tenant = _make_tenant('tenant-stg-limit', plan='gratuit')
    user = _make_user(tenant, 'admin-stg-limit')
    client = app.test_client()
    headers = _login(client, 'admin-stg-limit', 'Password123!', 'tenant-stg-limit')

    with app.app_context():
        for i in range(2):
            s = Stagiaire(nom=f'Stagiaire {i}', prenom='S', matricule=f'STG-{i}', tenant_id=tenant.id, etablissement='Univ')
            db.session.add(s)
        db.session.commit()

    r = client.post('/api/v1/stagiaires', headers=headers, json={
        'matricule': 'STG-OVER',
        'nom': 'Overflow',
        'prenom': 'O',
        'etablissement': 'Univ',
        'formation': 'Info',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
    })
    assert r.status_code == 403, r.get_json()
    assert 'limite' in r.get_json()['message'].lower()
