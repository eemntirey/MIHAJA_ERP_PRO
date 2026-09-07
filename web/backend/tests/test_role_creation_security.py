import pytest
from app import db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.role_permission import RoleModel, Permission
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from datetime import datetime, timedelta


@pytest.fixture
def client(app):
    return app.test_client()


def _make_tenant(slug):
    tenant = Tenant(nom=slug, slug=slug, domaine=f'{slug}.local', statut=StatutTenant.ACTIF, plan='pro')
    db.session.add(tenant)
    db.session.commit()
    abonnement = Abonnement(
        tenant_id=tenant.id, plan='pro', statut=StatutAbonnement.ACTIF,
        date_debut=datetime.utcnow() - timedelta(days=30),
        date_fin=datetime.utcnow() + timedelta(days=30),
    )
    db.session.add(abonnement)
    db.session.commit()
    return tenant


def _make_user(tenant, username, role=Role.ADMIN):
    user = Utilisateur(
        username=username, email=f'{username}@example.com',
        password_hash=hash_password('Password123!'), nom=username, prenom=username,
        role=role, tenant_id=tenant.id, statut=StatutUtilisateur.ACTIF,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username, tenant_slug):
    r = client.post('/api/v1/auth/login', json={'username': username, 'password': 'Password123!', 'tenant_slug': tenant_slug})
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestRoleCreationSecurity:
    # TEST 1 - clé admin valide -> SUCCESS
    def test_valid_new_role_ok(self, app, client):
        t = _make_tenant('tenant-sec-valid')
        _make_user(t, 'admin-sec-valid')
        h = _login(client, 'admin-sec-valid', 'tenant-sec-valid')
        r = client.post('/api/v1/roles', headers=h, json={'name': 'brand_new_role_x', 'display_name': 'X'})
        assert r.status_code == 201, r.get_json()

    # TEST 2 - clé admin invalide -> 401 jamais 500
    def test_invalid_key_refused(self, app, client):
        t = _make_tenant('tenant-sec-invalid')
        _make_user(t, 'admin-sec-invalid')
        r = client.post('/api/v1/roles', headers={'Authorization': 'Bearer badtoken'}, json={'name': 'x', 'display_name': 'X'})
        assert r.status_code in (401, 403), r.get_json()
        assert r.status_code != 500

    # TEST 3 - mauvais tenant -> refus, jamais accès aux données de B
    def test_wrong_tenant_cannot_operate_on_other_tenant_role(self, app, client):
        ta = _make_tenant('tenant-sec-a')
        tb = _make_tenant('tenant-sec-b')
        _make_user(ta, 'admin-sec-a')
        _make_user(tb, 'admin-sec-b')
        ha = _login(client, 'admin-sec-a', 'tenant-sec-a')
        hb = _login(client, 'admin-sec-b', 'tenant-sec-b')
        ra = client.post('/api/v1/roles', headers=ha, json={'name': 'role_only_a', 'display_name': 'A'})
        assert ra.status_code == 201, ra.get_json()
        role_id = ra.get_json()['id']
        # Tenant B ne doit pas voir/modifier le rôle de A
        rb_get = client.get(f'/api/v1/roles/{role_id}', headers=hb)
        assert rb_get.status_code == 404, rb_get.get_json()
        rb_put = client.put(f'/api/v1/roles/{role_id}', headers=hb, json={'display_name': 'hacked'})
        assert rb_put.status_code == 404, rb_put.get_json()

    # TEST 4 - rôle existant -> erreur contrôlée, jamais 500
    def test_collision_with_system_role(self, app, client):
        t = _make_tenant('tenant-sec-sys')
        _make_user(t, 'admin-sec-sys')
        h = _login(client, 'admin-sec-sys', 'tenant-sec-sys')
        r = client.post('/api/v1/roles', headers=h, json={'name': 'manager', 'display_name': 'Manager', 'is_system': True})
        assert r.status_code == 409, r.get_json()
        assert r.status_code != 500

    def test_collision_with_other_tenant_role(self, app, client):
        t1 = _make_tenant('tenant-sec-a2')
        t2 = _make_tenant('tenant-sec-b2')
        _make_user(t1, 'admin-sec-a2')
        _make_user(t2, 'admin-sec-b2')
        h1 = _login(client, 'admin-sec-a2', 'tenant-sec-a2')
        h2 = _login(client, 'admin-sec-b2', 'tenant-sec-b2')
        r1 = client.post('/api/v1/roles', headers=h1, json={'name': 'shared_role_name', 'display_name': 'S'})
        assert r1.status_code == 201, r1.get_json()
        r2 = client.post('/api/v1/roles', headers=h2, json={'name': 'shared_role_name', 'display_name': 'S'})
        assert r2.status_code == 409, r2.get_json()
        assert r2.status_code != 500

    # TEST 5 - permission invalide -> validation contrôlée, jamais 500
    def test_invalid_permission_id_ignored(self, app, client):
        t = _make_tenant('tenant-sec-perm')
        _make_user(t, 'admin-sec-perm')
        h = _login(client, 'admin-sec-perm', 'tenant-sec-perm')
        r = client.post('/api/v1/roles', headers=h, json={'name': 'role_with_bad_perm', 'display_name': 'P', 'permission_ids': [999999]})
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['permissions'] == []
