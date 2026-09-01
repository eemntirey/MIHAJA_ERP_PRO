"""Tests de sécurité RBAC : masquage du rôle SUPER_ADMIN aux tenants.

Règle métier stricte :
  - Un TENANT / ADMIN TENANT ne doit JAMAIS voir le rôle SUPER_ADMIN dans la
    liste des rôles, les selects/filtres, les formulaires de création/modif,
    ni via un accès direct par id (l'API renvoie 404 pour le masquer).
  - Le rôle SUPER_ADMIN reste présent en base de données et visible pour le
    SUPER_ADMIN connecté.
  - Un tenant ne peut pas attribuer le rôle SUPER_ADMIN à un utilisateur
    (ni via le role enum, ni via un custom_role).
"""
import pytest
from datetime import datetime, timedelta

from app import db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.role_permission import RoleModel, Permission
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from flask_jwt_extended import create_access_token


SUPER_ADMIN_ROLE_NAME = 'super_admin'


@pytest.fixture
def client(app):
    return app.test_client()


def _make_tenant(slug, plan='pro'):
    tenant = Tenant(nom=slug, slug=slug, domaine=f'{slug}.local',
                    statut=StatutTenant.ACTIF, plan=plan)
    db.session.add(tenant)
    db.session.commit()
    db.session.add(Abonnement(
        tenant_id=tenant.id, plan=plan, statut=StatutAbonnement.ACTIF,
        date_debut=datetime.utcnow() - timedelta(days=30),
        date_fin=datetime.utcnow() + timedelta(days=30),
    ))
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


def _make_super_admin(username='sa_mask_test'):
    sa = Utilisateur(
        username=username, email=f'{username}@x.mg',
        password_hash=hash_password('SA12345!'), role=Role.SUPER_ADMIN,
        statut=StatutUtilisateur.ACTIF,
    )
    db.session.add(sa)
    db.session.commit()
    return sa


def _login(client, username, password, tenant_slug=None):
    payload = {'username': username, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


def _sa_headers(sa):
    token = create_access_token(identity=sa.id, additional_claims={'role': 'super_admin'})
    return {'Authorization': 'Bearer ' + token}


def _sa_role():
    return RoleModel.query.filter_by(name=SUPER_ADMIN_ROLE_NAME).first()


class TestSuperAdminRoleMaskingForTenant:
    def test_role_super_admin_existe_en_base(self, app):
        role = _sa_role()
        assert role is not None, "Le role SUPER_ADMIN doit rester en base (non supprime)"

    def test_tenant_admin_ne_voit_pas_super_admin_dans_liste(self, app, client):
        tenant = _make_tenant('tenant-mask-list')
        admin = _make_user(tenant, 'admin-mask-list')
        headers = _login(client, 'admin-mask-list', 'Password123!', 'tenant-mask-list')

        r = client.get('/api/v1/roles', headers=headers)
        assert r.status_code == 200, r.get_json()
        names = [role['name'] for role in r.get_json()['roles']]
        assert 'super_admin' not in names, (
            f"BUG : le rôle SUPER_ADMIN apparaît dans la liste pour un tenant. names={names}"
        )
        # Les autres rôles système restent visibles pour le tenant.
        for n in ('admin', 'manager', 'user', 'rh', 'sales', 'stock', 'accountant'):
            assert n in names, f"Le rôle système '{n}' doit rester visible au tenant"

    def test_tenant_admin_ne_decouvre_pas_super_admin_via_search(self, app, client):
        tenant = _make_tenant('tenant-mask-search')
        admin = _make_user(tenant, 'admin-mask-search')
        headers = _login(client, 'admin-mask-search', 'Password123!', 'tenant-mask-search')

        r = client.get('/api/v1/roles?search=super', headers=headers)
        assert r.status_code == 200, r.get_json()
        names = [role['name'] for role in r.get_json()['roles']]
        assert 'super_admin' not in names, (
            f"BUG : un search 'super' révèle le rôle SUPER_ADMIN. names={names}"
        )

    def test_tenant_admin_get_super_admin_par_id_404(self, app, client):
        tenant = _make_tenant('tenant-mask-get')
        admin = _make_user(tenant, 'admin-mask-get')
        headers = _login(client, 'admin-mask-get', 'Password123!', 'tenant-mask-get')
        sa_role = _sa_role()
        assert sa_role is not None

        r = client.get(f'/api/v1/roles/{sa_role.id}', headers=headers)
        assert r.status_code == 404, r.get_json()

    def test_tenant_admin_ne_peut_pas_creer_super_admin(self, app, client):
        tenant = _make_tenant('tenant-mask-create')
        admin = _make_user(tenant, 'admin-mask-create')
        headers = _login(client, 'admin-mask-create', 'Password123!', 'tenant-mask-create')

        r = client.post('/api/v1/roles', headers=headers,
                        json={'name': 'super_admin', 'display_name': 'Super Admin'})
        assert r.status_code == 403, r.get_json()

        # Même refusal en casse différente.
        r = client.post('/api/v1/roles', headers=headers,
                        json={'name': 'SUPER_ADMIN', 'display_name': 'X'})
        assert r.status_code == 403, r.get_json()

    def test_tenant_admin_update_super_admin_404(self, app, client):
        tenant = _make_tenant('tenant-mask-put')
        admin = _make_user(tenant, 'admin-mask-put')
        headers = _login(client, 'admin-mask-put', 'Password123!', 'tenant-mask-put')
        sa_role = _sa_role()

        r = client.put(f'/api/v1/roles/{sa_role.id}', headers=headers,
                       json={'display_name': 'Piraté'})
        assert r.status_code == 404, r.get_json()

    def test_tenant_admin_delete_super_admin_404(self, app, client):
        tenant = _make_tenant('tenant-mask-del')
        admin = _make_user(tenant, 'admin-mask-del')
        headers = _login(client, 'admin-mask-del', 'Password123!', 'tenant-mask-del')
        sa_role = _sa_role()

        r = client.delete(f'/api/v1/roles/{sa_role.id}', headers=headers)
        assert r.status_code == 404, r.get_json()
        # Le role reste en base malgré la tentative de suppression.
        assert RoleModel.query.filter_by(name=SUPER_ADMIN_ROLE_NAME).first() is not None

    def test_tenant_admin_ne_peut_pas_ajouter_permission_super_admin(self, app, client):
        tenant = _make_tenant('tenant-mask-perm')
        admin = _make_user(tenant, 'admin-mask-perm')
        headers = _login(client, 'admin-mask-perm', 'Password123!', 'tenant-mask-perm')
        sa_role = _sa_role()
        perm = Permission.query.first()

        r = client.post('/api/v1/roles/permissions', headers=headers,
                        json={'role_id': sa_role.id, 'permission_id': perm.id})
        assert r.status_code == 404, r.get_json()

    def test_tenant_admin_ne_peut_pas_retirer_permission_super_admin(self, app, client):
        tenant = _make_tenant('tenant-mask-perm-rm')
        admin = _make_user(tenant, 'admin-mask-perm-rm')
        headers = _login(client, 'admin-mask-perm-rm', 'Password123!', 'tenant-mask-perm-rm')
        sa_role = _sa_role()
        perm = Permission.query.first()

        r = client.delete(f'/api/v1/roles/permissions/{sa_role.id}/{perm.id}', headers=headers)
        assert r.status_code == 404, r.get_json()


class TestSuperAdminRoleVisibleForSuperAdmin:
    def test_super_admin_voit_super_admin_dans_liste(self, app, client):
        sa = _make_super_admin('sa_list_mask')
        headers = _sa_headers(sa)

        r = client.get('/api/v1/roles', headers=headers)
        assert r.status_code == 200, r.get_json()
        names = [role['name'] for role in r.get_json()['roles']]
        assert 'super_admin' in names, "Le SUPER_ADMIN doit voir le rôle SUPER_ADMIN"
        assert 'rh' in names

    def test_super_admin_get_super_admin_par_id(self, app, client):
        sa = _make_super_admin('sa_get_mask')
        headers = _sa_headers(sa)
        sa_role = _sa_role()

        r = client.get(f'/api/v1/roles/{sa_role.id}', headers=headers)
        assert r.status_code == 200, r.get_json()
        assert r.get_json()['name'] == 'super_admin'

    def test_super_admin_voit_super_admin_preset(self, app, client):
        sa = _make_super_admin('sa_preset_mask')
        headers = _sa_headers(sa)

        r = client.get('/api/v1/roles/presets', headers=headers)
        assert r.status_code == 200, r.get_json()
        preset_names = {p['name'] for p in r.get_json()['presets']}
        assert 'super_admin' in preset_names


class TestTenantCannotAssignSuperAdminToUser:
    def test_tenant_admin_ne_peut_pas_assigner_role_enum_super_admin(self, app, client):
        tenant = _make_tenant('tenant-nocreate')
        _make_user(tenant, 'admin-nocreate')
        headers = _login(client, 'admin-nocreate', 'Password123!', 'tenant-nocreate')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'evil_sa', 'email': 'evil_sa@x.mg',
                              'password': 'Pass123!', 'role': 'super_admin',
                              'statut': 'actif'})
        assert r.status_code == 403, r.get_json()

    def test_tenant_admin_ne_peut_pas_assigner_super_admin_en_custom_role(self, app, client):
        tenant = _make_tenant('tenant-nocustom')
        _make_user(tenant, 'admin-nocustom')
        headers = _login(client, 'admin-nocustom', 'Password123!', 'tenant-nocustom')
        sa_role = _sa_role()
        assert sa_role is not None

        # Via la création d'utilisateur.
        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'custom_sa', 'email': 'custom_sa@x.mg',
                              'password': 'Pass123!', 'role': 'user',
                              'statut': 'actif', 'custom_role_id': sa_role.id})
        assert r.status_code == 403, r.get_json()

    def test_tenant_admin_ne_peut_pas_promouvoir_user_en_super_admin(self, app, client):
        tenant = _make_tenant('tenant-promote')
        _make_user(tenant, 'admin-promote')
        target = _make_user(tenant, 'target-promote', role=Role.USER)
        headers = _login(client, 'admin-promote', 'Password123!', 'tenant-promote')

        r = client.put(f'/api/v1/users/{target.id}', headers=headers,
                       json={'role': 'super_admin'})
        assert r.status_code == 403, r.get_json()
        # Le rôle de l'utilisateur n'a pas changé.
        assert Utilisateur.query.get(target.id).role == Role.USER


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
