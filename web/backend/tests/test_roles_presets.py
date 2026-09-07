import pytest
from app import db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.role_permission import RoleModel, Permission
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.permission_matrix import ROLE_PERMISSIONS
from app.security.auth import hash_password
from datetime import datetime, timedelta


@pytest.fixture
def client(app):
    return app.test_client()


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


def _login(client, username, password, tenant_slug=None):
    payload = {'username': username, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestRolePresets:
    def test_all_system_roles_seeded(self, app):
        expected = {'super_admin', 'admin', 'manager', 'sales', 'stock', 'accountant', 'rh', 'user', 'support'}
        roles = RoleModel.query.all()
        names = {r.name for r in roles}
        assert expected.issubset(names)

    def test_system_roles_have_permissions(self, app):
        for role_name in ['admin', 'manager', 'sales', 'stock', 'accountant', 'rh', 'user', 'support']:
            role = RoleModel.query.filter_by(name=role_name).first()
            assert role is not None, f"Role {role_name} not found"
            assert len(role.permissions) > 0, f"Role {role_name} has no permissions"

    def test_super_admin_has_read_only_permissions_on_tenants(self, app):
        # Regle metier : SUPER_ADMIN agit sur la PLATEFORME (tenants, abonnements,
        # plans) et n'a qu'un acces en LECTURE SEULE aux donnees metier des
        # tenants. Il ne dispose PAS d'une wildcard `*` : toute ecriture
        # (create/update/delete) sur les ressources metier est reservee aux
        # utilisateurs du tenant (admin, manager, ...).
        sa_perms = ROLE_PERMISSIONS.get('super_admin', [])
        assert sa_perms, "super_admin doit avoir une liste de permissions explicite"
        assert '*' not in sa_perms, "super_admin ne doit PAS utiliser la wildcard"
        # Acces plateforme obligatoire.
        assert 'super_admin.access' in sa_perms
        assert 'admin.access' in sa_perms
        # Lecture seule sur les ressources metier des tenants.
        for view_perm in [
            'product.view', 'stock.view', 'sale.view', 'client.view',
            'invoice.view', 'payment.view', 'compte.view', 'ecriture.view',
            'tresorerie.view', 'delivery.view', 'report.view', 'dashboard.view',
            'user.view',
        ]:
            assert view_perm in sa_perms, f"{view_perm} doit etre present pour super_admin"
        # Aucune permission d'ecriture sur les ressources metier des tenants.
        forbidden_writes = {
            'product.create', 'product.update', 'product.delete',
            'sale.create', 'sale.update', 'sale.delete',
            'client.create', 'client.update', 'client.delete',
            'invoice.create', 'invoice.update', 'payment.create',
            'compte.create', 'compte.update', 'compte.delete',
            'ecriture.create', 'ecriture.update', 'ecriture.delete',
            'tresorerie.create', 'tresorerie.update', 'tresorerie.delete',
            'stock.update', 'delivery.update',
            'employe.create', 'employe.update', 'employe.delete',
            'presence.create', 'presence.update', 'presence.delete',
            'salaire.create', 'salaire.update', 'salaire.delete',
            'prime.create', 'prime.update', 'prime.delete',
            'stagiaire.create', 'stagiaire.update', 'stagiaire.delete',
            'user.create', 'user.update', 'user.delete',
            'notification.manage',
        }
        assert forbidden_writes.isdisjoint(sa_perms), (
            "super_admin ne doit avoir AUCUNE permission d'ecriture sur les "
            "ressources metier des tenants"
        )
        # En BDD, le seed peut creer ou non un RoleModel 'super_admin' selon
        # la politique de la plateforme. S'il est cree, il ne doit JAMAIS
        # contenir de permission d'ecriture sur les ressources metier.
        role = RoleModel.query.filter_by(name='super_admin').first()
        if role is not None and role.permissions:
            role_codes = {p.code for p in role.permissions}
            assert forbidden_writes.isdisjoint(role_codes), (
                "Le RoleModel super_admin en BDD ne doit contenir aucune "
                "permission d'ecriture sur les ressources metier"
            )

    def test_rh_permissions_exist(self, app):
        rh_perms = ['employe.view', 'employe.create', 'employe.update', 'employe.delete',
                    'presence.view', 'presence.create', 'presence.update', 'presence.delete',
                    'salaire.view', 'salaire.create', 'salaire.update', 'salaire.delete',
                    'prime.view', 'prime.create', 'prime.update', 'prime.delete',
                    'stagiaire.view', 'stagiaire.create', 'stagiaire.update', 'stagiaire.delete']
        for code in rh_perms:
            perm = Permission.query.filter_by(code=code).first()
            assert perm is not None, f"Permission {code} not found"
            assert perm.module == 'rh'

    def test_rh_role_has_correct_permissions(self, app):
        role = RoleModel.query.filter_by(name='rh').first()
        assert role is not None
        codes = sorted([p.code for p in role.permissions])
        expected = sorted([
            'employe.view', 'employe.create', 'employe.update', 'employe.delete',
            'presence.view', 'presence.create', 'presence.update', 'presence.delete',
            'salaire.view', 'salaire.create', 'salaire.update', 'salaire.delete',
            'prime.view', 'prime.create', 'prime.update', 'prime.delete',
            'stagiaire.view', 'stagiaire.create', 'stagiaire.update', 'stagiaire.delete',
            'profile.view', 'profile.update', 'report.view',
        ])
        assert codes == expected

    def test_manager_no_delete_permissions(self, app):
        role = RoleModel.query.filter_by(name='manager').first()
        assert role is not None
        codes = {p.code for p in role.permissions}
        forbidden = {'client.delete', 'compte.delete', 'ecriture.delete', 'product.delete', 'tresorerie.delete', 'user.delete'}
        assert forbidden.isdisjoint(codes)

    def test_admin_has_limited_delete(self, app):
        role = RoleModel.query.filter_by(name='admin').first()
        assert role is not None
        codes = {p.code for p in role.permissions}
        assert 'client.delete' in codes
        assert 'product.delete' in codes
        assert 'compte.delete' not in codes
        assert 'ecriture.delete' not in codes
        assert 'tresorerie.delete' not in codes
        assert 'user.delete' not in codes

    def test_presets_endpoint_returns_presets(self, app, client):
        tenant = _make_tenant('tenant-preset')
        user = _make_user(tenant, 'admin-preset')
        headers = _login(client, 'admin-preset', 'Password123!', 'tenant-preset')

        r = client.get('/api/v1/roles/presets', headers=headers)
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert 'presets' in data
        preset_names = {p['name'] for p in data['presets']}
        # Un admin de tenant ne doit JAMAIS voir le preset SUPER_ADMIN.
        assert 'super_admin' not in preset_names
        assert 'admin' in preset_names
        assert 'manager' in preset_names
        assert 'sales' in preset_names
        assert 'stock' in preset_names
        assert 'accountant' in preset_names
        assert 'rh' in preset_names
        assert 'user' in preset_names

    def test_presets_super_admin_voit_super_admin(self, app, client):
        tenant = _make_tenant('tenant-preset-sa')
        _make_user(tenant, 'admin-preset-sa')
        # Super admin (sans tenant) : le preset super_admin doit rester visible.
        sa = Utilisateur(
            username='sa-preset', email='sa-preset@x.mg',
            password_hash=hash_password('SA123!'), role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(sa)
        db.session.commit()
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=sa.id, additional_claims={'role': 'super_admin'})
        headers = {'Authorization': 'Bearer ' + token}

        r = client.get('/api/v1/roles/presets', headers=headers)
        assert r.status_code == 200, r.get_json()
        preset_names = {p['name'] for p in r.get_json()['presets']}
        assert 'super_admin' in preset_names

    def test_system_role_cannot_be_deleted(self, app, client):
        tenant = _make_tenant('tenant-sysrole')
        user = _make_user(tenant, 'admin-sysrole')
        headers = _login(client, 'admin-sysrole', 'Password123!', 'tenant-sysrole')

        role = RoleModel.query.filter_by(name='manager').first()
        assert role is not None

        r = client.delete(f'/api/v1/roles/{role.id}', headers=headers)
        assert r.status_code == 400, r.get_json()
        assert 'systeme' in r.get_json()['message'].lower()

    def test_custom_role_can_be_created_and_deleted(self, app, client):
        tenant = _make_tenant('tenant-custom')
        user = _make_user(tenant, 'admin-custom')
        headers = _login(client, 'admin-custom', 'Password123!', 'tenant-custom')

        r = client.post('/api/v1/roles', headers=headers, json={
            'name': 'custom_test',
            'display_name': 'Custom Test',
            'description': 'Test custom role',
            'is_system': False,
            'permission_ids': [],
        })
        assert r.status_code == 201, r.get_json()
        role_id = r.get_json()['id']

        r = client.delete(f'/api/v1/roles/{role_id}', headers=headers)
        assert r.status_code == 200, r.get_json()

    def test_role_enum_has_rh(self, app):
        assert Role.RH.value == 'rh'

    def test_user_with_rh_role_has_permissions(self, app):
        tenant = _make_tenant('tenant-rh')
        user = _make_user(tenant, 'rh-user', role=Role.RH)
        assert user.has_permission('employe.view')
        assert user.has_permission('employe.create')
        assert user.has_permission('stagiaire.delete')
        assert not user.has_permission('client.delete')
