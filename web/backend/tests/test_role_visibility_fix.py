"""Verification du correctif 'role existe mais n'apparait pas dans la liste'.

Scenario exact du bug signale :
  - GET /api/v1/roles doit inclure les roles systeme (tenant_id NULL, ex. 'rh')
    pour un admin de tenant.
  - POST /api/v1/roles avec name='rh' doit retourner 409 (collision systeme).
  - POST /api/v1/roles avec un nom inexistant doit retourner 201.
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


def _login_token(user_id, tenant_id, tenant_slug, role='admin'):
    return create_access_token(
        identity=user_id,
        additional_claims={'role': role, 'tenant_id': tenant_id, 'tenant_slug': tenant_slug},
    )


def test_rh_apparait_dans_liste_et_collision_409():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()

        # Le role 'rh' systeme existe-t-il bien en base ?
        rh_row = RoleModel.query.filter_by(name='rh').first()
        assert rh_row is not None, "Le role 'rh' systeme aurait du etre cree par le seed"
        assert rh_row.tenant_id is None, "Le role 'rh' systeme doit avoir tenant_id=NULL"

        # Creer un tenant + admin
        tenant = Tenant(nom='TestRH', slug='testrh', domaine='testrh.local',
                        statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(tenant)
        db.session.commit()
        abo = Abonnement(tenant_id=tenant.id, plan='pro', statut=StatutAbonnement.ACTIF,
                          date_debut=datetime.utcnow() - timedelta(days=1),
                          date_fin=datetime.utcnow() + timedelta(days=30))
        db.session.add(abo)
        admin = Utilisateur(username='admin_rh', email='admin_rh@x.mg',
                             password_hash=hash_password('Admin123!'),
                             role=Role.ADMIN, tenant_id=tenant.id,
                             statut=StatutUtilisateur.ACTIF,
                             is_principal_admin=True)
        db.session.add(admin)
        db.session.commit()

        client = app.test_client()
        token = _login_token(admin.id, tenant.id, tenant.slug, 'admin')
        h = {'Authorization': 'Bearer ' + token}

        # 1. GET /api/v1/roles doit inclure 'rh'
        r = client.get('/api/v1/roles', headers=h)
        assert r.status_code == 200, r.get_json()
        roles = r.get_json()['roles']
        names = [r_['name'] for r_ in roles]
        assert 'rh' in names, (
            f"BUG : le role 'rh' est dans la base (systeme) mais absent de la liste "
            f"renvoyee a l'admin du tenant. Liste = {names}"
        )
        # Et la liste doit aussi contenir les autres roles systeme
        for n in ('admin', 'manager', 'user', 'rh', 'sales', 'stock', 'accountant'):
            assert n in names, f"Role systeme '{n}' manquant dans la liste affichee"

        # 2. POST avec name='rh' (systeme, collision) -> 409
        r = client.post('/api/v1/roles', headers=h,
                        json={'name': 'rh', 'display_name': 'RH'})
        assert r.status_code == 409, r.get_json()

        # 3. POST avec un nom qui n'existe nulle part -> 201
        r = client.post('/api/v1/roles', headers=h,
                        json={'name': 'nouveau_role_unique_xyz', 'display_name': 'X'})
        assert r.status_code == 201, r.get_json()

        # 4. POST avec casse differente d'un nom systeme ('RH') : la cle unique
        #    SQL n'est pas case-insensitive, mais on documente le comportement.
        r = client.post('/api/v1/roles', headers=h,
                        json={'name': 'RH', 'display_name': 'RH'})
        # 201 ou 409 selon collation. On accepte les deux mais on verifie la liste.
        assert r.status_code in (201, 409), r.get_json()

        # 5. Apres toutes ces operations, GET /api/v1/roles reflete bien l'etat
        r = client.get('/api/v1/roles', headers=h)
        names_after = [r_['name'] for r_ in r.get_json()['roles']]
        assert 'rh' in names_after
        # Le role cree par le tenant doit apparaitre
        assert 'nouveau_role_unique_xyz' in names_after

    print("OK : 'rh' systeme est visible dans la liste + collision 409 + creation 201.")


def test_super_admin_voit_tous_les_roles():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        # Creer 2 tenants avec chacun un role custom
        t1 = Tenant(nom='T1', slug='t1', domaine='t1.local', statut=StatutTenant.ACTIF, plan='pro')
        t2 = Tenant(nom='T2', slug='t2', domaine='t2.local', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add_all([t1, t2]); db.session.commit()
        for t in (t1, t2):
            db.session.add(Abonnement(
                tenant_id=t.id, plan='pro', statut=StatutAbonnement.ACTIF,
                date_debut=datetime.utcnow() - timedelta(days=1),
                date_fin=datetime.utcnow() + timedelta(days=30),
            ))
        db.session.add_all([
            RoleModel(name='role_de_t1', display_name='R1', tenant_id=t1.id),
            RoleModel(name='role_de_t2', display_name='R2', tenant_id=t2.id),
        ])
        sa = Utilisateur(username='sa', email='sa@s.mg', password_hash=hash_password('SA123!'),
                          role=Role.SUPER_ADMIN, statut=StatutUtilisateur.ACTIF)
        db.session.add(sa); db.session.commit()

        client = app.test_client()
        token = create_access_token(identity=sa.id, additional_claims={'role': 'super_admin'})
        h = {'Authorization': 'Bearer ' + token}
        r = client.get('/api/v1/roles', headers=h)
        names = [r_['name'] for r_ in r.get_json()['roles']]
        # Super admin doit voir systeme + role_de_t1 + role_de_t2
        assert 'rh' in names
        assert 'role_de_t1' in names
        assert 'role_de_t2' in names
    print("OK : super admin voit les roles de tous les tenants + les roles systeme.")


if __name__ == '__main__':
    test_rh_apparait_dans_liste_et_collision_409()
    test_super_admin_voit_tous_les_roles()
