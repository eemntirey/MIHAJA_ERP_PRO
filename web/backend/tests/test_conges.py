import pytest
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.employe import Employe
from app.models.conge import Conge, TypeConge, StatutConge
from app.models.presence import Presence, StatutPresence
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from datetime import datetime, timedelta


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


def _make_employe(tenant, matricule='EMP-1'):
    e = Employe(nom='Employe', prenom='Conge', matricule=matricule, tenant_id=tenant.id,
                salaire_base=1000, conges_credit_annuel=30)
    db.session.add(e)
    db.session.commit()
    return e


def test_create_conge_calcule_nb_jours(app):
    tenant = _make_tenant('tenant-conge')
    _make_user(tenant, 'admin-conge')
    client = app.test_client()
    headers = _login(client, 'admin-conge', 'Password123!', 'tenant-conge')

    with app.app_context():
        e = _make_employe(tenant)

    # Vendredi 01 -> mardi 05 (1+4+5 = 3 jours ouvrÃ©s, lundi entre)
    r = client.post('/api/v1/conges', headers=headers, json={
        'employe_id': e.id,
        'type_conge': 'maladie',
        'date_debut': '2026-05-08',
        'date_fin': '2026-05-12',
        'motif': 'Consultation',
    })
    assert r.status_code == 201, r.get_json()
    data = r.get_json()
    assert data['type_conge'] == 'maladie'
    assert data['statut'] == 'en_attente'
    assert data['annee'] == 2026
    assert data['nb_jours'] == 3


def test_conge_chevauchement_refuse(app):
    tenant = _make_tenant('tenant-overlap')
    _make_user(tenant, 'admin-overlap')
    client = app.test_client()
    headers = _login(client, 'admin-overlap', 'Password123!', 'tenant-overlap')

    with app.app_context():
        e = _make_employe(tenant)
        Conge(employe_id=e.id, type_conge=TypeConge.ANNUEL, date_debut='2026-06-01',
              date_fin='2026-06-10', nb_jours=8, annee=2026, statut=StatutConge.EN_ATTENTE, tenant_id=tenant.id)
        db.session.commit()

    r = client.post('/api/v1/conges', headers=headers, json={
        'employe_id': e.id,
        'type_conge': 'maladie',
        'date_debut': '2026-06-05',
        'date_fin': '2026-06-07',
        'motif': 'Chevauchement',
    })
    assert r.status_code == 400, r.get_json()
    assert 'chevauch' in r.get_json()['message'].lower()


def test_conge_solde_deduct_approbation(app):
    tenant = _make_tenant('tenant-solde')
    _make_user(tenant, 'admin-solde')
    client = app.test_client()
    headers = _login(client, 'admin-solde', 'Password123!', 'tenant-solde')

    with app.app_context():
        e = _make_employe(tenant)

    r = client.post('/api/v1/conges', headers=headers, json={
        'employe_id': e.id,
        'type_conge': 'maladie',
        'date_debut': '2026-03-02',
        'date_fin': '2026-03-04',
        'motif': 'Maladie',
    })
    assert r.status_code == 201, r.get_json()
    cid = r.get_json()['id']
    assert r.get_json()['nb_jours'] == 3

    # Avant approbation : solde intact
    r = client.get(f'/api/v1/conges/solde/{e.id}?annee=2026', headers=headers)
    assert r.status_code == 200, r.get_json()
    solde = r.get_json()
    assert solde['credit_annuel'] == 30
    assert solde['jours_pris'] == 0
    assert solde['solde_restant'] == 30

    # Approbation -> jours dÃ©comptÃ©s
    r = client.put(f'/api/v1/conges/{cid}', headers=headers, json={'statut': 'approuve'})
    assert r.status_code == 200, r.get_json()

    r = client.get(f'/api/v1/conges/solde/{e.id}?annee=2026', headers=headers)
    solde = r.get_json()
    assert solde['jours_pris'] == 3
    assert solde['solde_restant'] == 27


def test_conge_approuve_auto_presences(app):
    tenant = _make_tenant('tenant-auto')
    _make_user(tenant, 'admin-auto')
    client = app.test_client()
    headers = _login(client, 'admin-auto', 'Password123!', 'tenant-auto')

    with app.app_context():
        e = _make_employe(tenant)

    r = client.post('/api/v1/conges', headers=headers, json={
        'employe_id': e.id,
        'type_conge': 'maladie',
        'date_debut': '2026-06-08',
        'date_fin': '2026-06-12',
        'motif': 'Maladie',
    })
    assert r.status_code == 201, r.get_json()
    cid = r.get_json()['id']

    r = client.put(f'/api/v1/conges/{cid}', headers=headers, json={'statut': 'approuve'})
    assert r.status_code == 200, r.get_json()

    with app.app_context():
        presences = Presence.query.filter_by(employe_id=e.id).all()
        assert len(presences) == 5  # lun 8 -> ven 12
        for p in presences:
            assert p.statut == StatutPresence.CONGE
            assert 'auto' in (p.remarque or '').lower()
            assert p.remarque.startswith('Auto: conge #')


def test_conge_refus_retire_auto_presences(app):
    tenant = _make_tenant('tenant-refus')
    _make_user(tenant, 'admin-refus')
    client = app.test_client()
    headers = _login(client, 'admin-refus', 'Password123!', 'tenant-refus')

    with app.app_context():
        e = _make_employe(tenant)

    r = client.post('/api/v1/conges', headers=headers, json={
        'employe_id': e.id,
        'type_conge': 'exceptionnel',
        'date_debut': '2026-07-06',
        'date_fin': '2026-07-08',
        'motif': 'Event',
    })
    assert r.status_code == 201, r.get_json()
    cid = r.get_json()['id']

    r = client.put(f'/api/v1/conges/{cid}', headers=headers, json={'statut': 'approuve'})
    assert r.status_code == 200, r.get_json()
    with app.app_context():
        assert Presence.query.filter_by(employe_id=e.id).count() == 3

    r = client.put(f'/api/v1/conges/{cid}', headers=headers, json={'statut': 'refuse'})
    assert r.status_code == 200, r.get_json()
    with app.app_context():
        assert Presence.query.filter_by(employe_id=e.id).count() == 0


def test_conge_cross_tenant_denied(app):
    ta = _make_tenant('tenant-a-c')
    tb = _make_tenant('tenant-b-c')
    _make_user(ta, 'admin_a_c', Role.ADMIN)
    _make_user(tb, 'admin_b_c', Role.ADMIN)
    client = app.test_client()
    headers_a = _login(client, 'admin_a_c', 'Password123!', 'tenant-a-c')

    with app.app_context():
        cong_b = Conge(employe_id=1, type_conge=TypeConge.ANNUEL, date_debut='2026-01-01',
                       date_fin='2026-01-04', nb_jours=2, annee=2026, statut=StatutConge.EN_ATTENTE,
                       tenant_id=tb.id)
        db.session.add(cong_b)
        db.session.commit()
        cid_b = cong_b.id

    r = client.get(f'/api/v1/conges/{cid_b}', headers=headers_a)
    assert r.status_code == 404, r.get_json()

    r = client.put(f'/api/v1/conges/{cid_b}', headers=headers_a, json={'statut': 'approuve'})
    assert r.status_code == 404, r.get_json()

    r = client.delete(f'/api/v1/conges/{cid_b}', headers=headers_a)
    assert r.status_code == 404, r.get_json()