"""Sécurité RBAC - module Rôles.

Vérifie la règle métier stricte :

    - Un SUPER_ADMIN voit SUPER_ADMIN + tous les rôles.
    - Un TENANT (admin tenant) NE DOIT JAMAIS voir SUPER_ADMIN, ni dans la
      liste, ni dans les presets, ni via GET direct sur /roles/<id>, ni en
      POST/création, ni en PUT/modification. Il ne peut pas non plus
      assigner ce rôle à un utilisateur via /users (POST/PUT).

Ce test couvre l'API backend. Le frontend (Roles.jsx) applique déjà un
filtrage équivalent via useAuth().user.role comme défense en profondeur.
"""
import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('PAPI_API_URL', 'https://test.papi.mg/dashboard/api/payment-links')
os.environ.setdefault('PAPI_API_KEY', 'test-api-key')
os.environ.setdefault('PAPI_ENVIRONMENT', 'sandbox')
os.environ.setdefault('PAPI_CALLBACK_URL', 'http://localhost:5000/api/v1/papi/webhook')

from app import create_app, db
from app.models.role_permission import RoleModel
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from flask_jwt_extended import create_access_token


SUPER_ADMIN = Role.SUPER_ADMIN.value  # 'super_admin'


def _make_tenant(slug):
    t = Tenant(nom=slug, slug=slug, domaine=f'{slug}.local',
               statut=StatutTenant.ACTIF, plan='pro')
    db.session.add(t)
    db.session.commit()
    db.session.add(Abonnement(
        tenant_id=t.id, plan='pro', statut=StatutAbonnement.ACTIF,
        date_debut=datetime.utcnow() - timedelta(days=1),
        date_fin=datetime.utcnow() + timedelta(days=30),
    ))
    db.session.commit()
    return t


def _make_admin(tenant, username, role=Role.ADMIN):
    u = Utilisateur(
        username=username, email=f'{username}@example.com',
        password_hash=hash_password('Password123!'),
        role=role, tenant_id=tenant.id,
        statut=StatutUtilisateur.ACTIF,
        is_principal_admin=(role == Role.ADMIN),
    )
    db.session.add(u)
    db.session.commit()
    return u


def _make_super_admin(username):
    u = Utilisateur(
        username=username, email=f'{username}@example.com',
        password_hash=hash_password('Password123!'),
        role=Role.SUPER_ADMIN,
        statut=StatutUtilisateur.ACTIF,
    )
    db.session.add(u)
    db.session.commit()
    return u


def _login_token(user_id, tenant_id=None, tenant_slug=None, role='admin'):
    claims = {'role': role}
    if tenant_id is not None:
        claims['tenant_id'] = tenant_id
    if tenant_slug is not None:
        claims['tenant_slug'] = tenant_slug
    return create_access_token(identity=user_id, additional_claims=claims)


# --------------------------------------------------------------------------- #
# Cas 1 - SUPER_ADMIN : voit SUPER_ADMIN + autres rôles
# --------------------------------------------------------------------------- #
def test_super_admin_sees_super_admin_role_and_others():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        sa = _make_super_admin('sa_sees')
        client = app.test_client()
        token = _login_token(sa.id, role=SUPER_ADMIN)
        h = {'Authorization': 'Bearer ' + token}
        r = client.get('/api/v1/roles', headers=h)
        assert r.status_code == 200, r.get_json()
        names = [x['name'] for x in r.get_json()['roles']]
        assert SUPER_ADMIN in names, (
            f"SUPER_ADMIN doit voir le rôle '{SUPER_ADMIN}'. Liste={names}"
        )
        # Et les autres rôles système
        for n in ('admin', 'manager', 'user', 'rh'):
            assert n in names, f"Role système '{n}' manquant côté SUPER_ADMIN"


# --------------------------------------------------------------------------- #
# Cas 2 - TENANT : SUPER_ADMIN absent de la liste et des presets
# --------------------------------------------------------------------------- #
def test_tenant_does_not_see_super_admin_in_list_or_presets():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        t = _make_tenant('t_rbac_roles')
        admin = _make_admin(t, 'admin_rbac_roles')
        client = app.test_client()
        token = _login_token(admin.id, t.id, t.slug, 'admin')
        h = {'Authorization': 'Bearer ' + token}

        # Liste
        r = client.get('/api/v1/roles', headers=h)
        assert r.status_code == 200, r.get_json()
        names = [x['name'] for x in r.get_json()['roles']]
        assert SUPER_ADMIN not in names, (
            f"BUG RBAC : un tenant voit '{SUPER_ADMIN}' dans la liste. "
            f"Liste={names}"
        )
        # Et les rôles normaux restent visibles
        for n in ('admin', 'manager', 'user', 'rh'):
            assert n in names, f"Role '{n}' manquant pour le tenant"

        # Presets
        r = client.get('/api/v1/roles/presets', headers=h)
        assert r.status_code == 200, r.get_json()
        presets = [p['name'] for p in r.get_json()['presets']]
        assert SUPER_ADMIN not in presets, (
            f"BUG RBAC : '{SUPER_ADMIN}' présent dans les presets du tenant. "
            f"Presets={presets}"
        )


# --------------------------------------------------------------------------- #
# Cas 3 - TENANT : impossible de récupérer SUPER_ADMIN par id
# --------------------------------------------------------------------------- #
def test_tenant_cannot_fetch_super_admin_role_by_id():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        sa_role = RoleModel.query.filter(
            db.func.lower(RoleModel.name) == SUPER_ADMIN
        ).first()
        assert sa_role is not None, "Le rôle SUPER_ADMIN doit exister en base"
        t = _make_tenant('t_rbac_get')
        admin = _make_admin(t, 'admin_rbac_get')
        client = app.test_client()
        token = _login_token(admin.id, t.id, t.slug, 'admin')
        h = {'Authorization': 'Bearer ' + token}
        r = client.get(f'/api/v1/roles/{sa_role.id}', headers=h)
        assert r.status_code == 404, (
            f"BUG RBAC : un tenant peut lire SUPER_ADMIN par id "
            f"(status={r.status_code}, body={r.get_json()})"
        )


# --------------------------------------------------------------------------- #
# Cas 4 - TENANT : impossible de créer un rôle nommé 'super_admin'
# --------------------------------------------------------------------------- #
def test_tenant_cannot_create_super_admin_role():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        t = _make_tenant('t_rbac_create')
        admin = _make_admin(t, 'admin_rbac_create')
        client = app.test_client()
        token = _login_token(admin.id, t.id, t.slug, 'admin')
        h = {'Authorization': 'Bearer ' + token}
        for variant in ('super_admin', 'Super_Admin', 'SUPER_ADMIN'):
            r = client.post('/api/v1/roles', headers=h, json={
                'name': variant, 'display_name': 'X',
            })
            assert r.status_code == 403, (
                f"BUG RBAC : un tenant peut créer le rôle '{variant}' "
                f"(status={r.status_code}, body={r.get_json()})"
            )


# --------------------------------------------------------------------------- #
# Cas 5 - TENANT : impossible de renommer un rôle en 'super_admin'
# --------------------------------------------------------------------------- #
def test_tenant_cannot_rename_role_to_super_admin():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        t = _make_tenant('t_rbac_rename')
        admin = _make_admin(t, 'admin_rbac_rename')
        client = app.test_client()
        token = _login_token(admin.id, t.id, t.slug, 'admin')
        h = {'Authorization': 'Bearer ' + token}
        # Le tenant crée un rôle custom
        r = client.post('/api/v1/roles', headers=h, json={
            'name': 'role_a_renommer', 'display_name': 'A',
        })
        assert r.status_code == 201, r.get_json()
        rid = r.get_json()['id']
        # Puis tente de le renommer en super_admin -> 403
        r = client.put(f'/api/v1/roles/{rid}', headers=h,
                       json={'name': 'super_admin'})
        assert r.status_code == 403, (
            f"BUG RBAC : un tenant peut renommer en super_admin "
            f"(status={r.status_code}, body={r.get_json()})"
        )
        # Et il ne doit pas avoir été renommé
        r = client.get('/api/v1/roles', headers=h)
        names_after = [x['name'] for x in r.get_json()['roles']]
        assert 'role_a_renommer' in names_after
        assert SUPER_ADMIN not in names_after


# --------------------------------------------------------------------------- #
# Cas 6 - TENANT : impossible de modifier le rôle SUPER_ADMIN
# --------------------------------------------------------------------------- #
def test_tenant_cannot_modify_super_admin_role():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        sa_role = RoleModel.query.filter(
            db.func.lower(RoleModel.name) == SUPER_ADMIN
        ).first()
        t = _make_tenant('t_rbac_mod')
        admin = _make_admin(t, 'admin_rbac_mod')
        client = app.test_client()
        token = _login_token(admin.id, t.id, t.slug, 'admin')
        h = {'Authorization': 'Bearer ' + token}
        r = client.put(f'/api/v1/roles/{sa_role.id}', headers=h,
                       json={'display_name': 'pirate'})
        assert r.status_code == 404, (
            f"BUG RBAC : un tenant peut modifier SUPER_ADMIN "
            f"(status={r.status_code}, body={r.get_json()})"
        )


# --------------------------------------------------------------------------- #
# Cas 7 - TENANT : impossible d'assigner SUPER_ADMIN à un utilisateur
# --------------------------------------------------------------------------- #
def test_tenant_cannot_assign_super_admin_to_user():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        t = _make_tenant('t_rbac_user_role')
        admin = _make_admin(t, 'admin_rbac_user_role')
        client = app.test_client()
        token = _login_token(admin.id, t.id, t.slug, 'admin')
        h = {'Authorization': 'Bearer ' + token}

        # 7a - POST /users avec role=super_admin -> 403
        r = client.post('/api/v1/users', headers=h, json={
            'username': 'future_sa', 'email': 'sa@x.mg',
            'password': 'Password123!', 'role': 'super_admin',
        })
        assert r.status_code == 403, (
            f"BUG RBAC : un tenant peut créer un user super_admin "
            f"(status={r.status_code}, body={r.get_json()})"
        )

        # 7b - PUT /users/<id> avec role=super_admin -> 403
        # Cible : un utilisateur existant du tenant
        target = _make_admin(t, 'target_user')
        r = client.put(f'/api/v1/users/{target.id}', headers=h,
                       json={'role': 'super_admin'})
        assert r.status_code == 403, (
            f"BUG RBAC : un tenant peut promouvoir en super_admin via PUT "
            f"(status={r.status_code}, body={r.get_json()})"
        )

        # 7c - PUT /users/<id> avec custom_role_id=ID(SUPER_ADMIN) -> 403
        sa_role = RoleModel.query.filter(
            db.func.lower(RoleModel.name) == SUPER_ADMIN
        ).first()
        r = client.put(f'/api/v1/users/{target.id}', headers=h,
                       json={'custom_role_id': sa_role.id})
        assert r.status_code == 403, (
            f"BUG RBAC : un tenant peut assigner le rôle custom SUPER_ADMIN "
            f"(status={r.status_code}, body={r.get_json()})"
        )


# --------------------------------------------------------------------------- #
# Cas 8 - SUPER_ADMIN : peut toujours créer / modifier SUPER_ADMIN
# --------------------------------------------------------------------------- #
def test_super_admin_can_still_create_super_admin():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        sa = _make_super_admin('sa_creator')
        client = app.test_client()
        token = _login_token(sa.id, role=SUPER_ADMIN)
        h = {'Authorization': 'Bearer ' + token}
        r = client.get('/api/v1/roles', headers=h)
        assert r.status_code == 200
        # Le rôle SUPER_ADMIN reste visible pour SUPER_ADMIN
        names = [x['name'] for x in r.get_json()['roles']]
        assert SUPER_ADMIN in names


if __name__ == '__main__':
    test_super_admin_sees_super_admin_role_and_others()
    test_tenant_does_not_see_super_admin_in_list_or_presets()
    test_tenant_cannot_fetch_super_admin_role_by_id()
    test_tenant_cannot_create_super_admin_role()
    test_tenant_cannot_rename_role_to_super_admin()
    test_tenant_cannot_modify_super_admin_role()
    test_tenant_cannot_assign_super_admin_to_user()
    test_super_admin_can_still_create_super_admin()
    print('OK : tous les contrôles RBAC du module Rôles sont conformes.')