"""Un super administrateur ne doit JAMAIS pouvoir creer une facture
pour les produits (ventes) d'un tenant : supervision en lecture seule."""
import os
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.client import Client
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', os.environ.get('DATABASE_URL', 'postgresql+psycopg://postgres@localhost:55432/erp_test'))
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        # Etat hermetique : reset_schema evite le conflit ENUM orphelin
        # (pg_type_typname_nsp_index) et la contamination inter-fichiers
        # de la base erp_test (create_all seul ne suffit pas).
        from tests._db_utils import reset_schema
        reset_schema(db)
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        yield app
        db.session.rollback()


def _make_context():
    ta = Tenant(nom='Tenant A', slug='tenant-a', domaine='a.local',
                statut=StatutTenant.ACTIF, plan='pro')
    db.session.add(ta)
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=ta.id, montant=100.0, plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    ))

    super_admin = Utilisateur(
        username='super', email='super@x.mg',
        password_hash=hash_password('Super123!'), role=Role.SUPER_ADMIN,
        statut=StatutUtilisateur.ACTIF,
    )
    sales = Utilisateur(
        username='vendeur_a', email='vendeur@a.mg',
        password_hash=hash_password('Sales123!'), role=Role.SALES,
        statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
    )
    db.session.add_all([super_admin, sales])

    client = Client(code='CLI-A', nom='Client A', tenant_id=ta.id)
    db.session.add(client)
    db.session.flush()
    vente = Vente(client_id=client.id, tenant_id=ta.id,
                  total_ht=100, total_ttc=120, reference='VA-1')
    db.session.add(vente)
    db.session.commit()
    return ta, super_admin, sales, client, vente


def _login(client, identifier, password):
    r = client.post('/api/v1/auth/login', json={
        'username': identifier, 'password': password,
    })
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestSuperAdminFactureInterdite:
    def test_post_facture_refuse_pour_super_admin(self, app):
        ta, super_admin, sales, client, vente = _make_context()
        c = app.test_client()
        headers = _login(c, 'super', 'Super123!')

        r = c.post('/api/v1/factures/', json={
            'vente_id': vente.id,
            'client_id': client.id,
            'tenant_id': ta.id,  # tentative d'attachement explicite
            'reference': 'FAC-SUPER-1',
        }, headers=headers)

        assert r.status_code == 403, r.get_json()
        # Aucune facture ne doit avoir ete creee pour le tenant
        assert Facture.query.filter_by(tenant_id=ta.id).count() == 0

    def test_post_from_vente_refuse_pour_super_admin(self, app):
        ta, super_admin, sales, client, vente = _make_context()
        c = app.test_client()
        headers = _login(c, 'super', 'Super123!')

        r = c.post(f'/api/v1/factures/from-vente/{vente.id}', json={},
                   headers=headers)

        assert r.status_code == 403, r.get_json()
        assert Facture.query.filter_by(tenant_id=ta.id).count() == 0

    def test_refus_meme_sans_claim_role_dans_le_jwt(self, app):
        """Token forge sans claim 'role' : le role en base doit bloquer."""
        ta, super_admin, sales, client, vente = _make_context()
        c = app.test_client()

        from flask_jwt_extended import create_access_token
        with app.app_context():
            token = create_access_token(
                identity=super_admin.id,
                additional_claims={'username': 'super'},
            )
        headers = {'Authorization': 'Bearer ' + token}

        r = c.post('/api/v1/factures/', json={
            'vente_id': vente.id,
            'client_id': client.id,
            'tenant_id': ta.id,
            'reference': 'FAC-SUPER-2',
        }, headers=headers)

        assert r.status_code == 403, r.get_json()
        assert Facture.query.filter_by(tenant_id=ta.id).count() == 0

    def test_ensure_not_super_admin_leve_sur_role_en_base(self, app):
        """Garde service : fallback sur g.current_user (role en base)."""
        ta, super_admin, sales, client, vente = _make_context()
        from flask import g
        from app.services.facturation_service import (
            SuperAdminFactureInterdite,
            ensure_not_super_admin,
        )
        with app.test_request_context():
            g.current_user = super_admin
            with pytest.raises(SuperAdminFactureInterdite):
                ensure_not_super_admin()

    def test_ensure_not_super_admin_leve_sur_claim_jwt(self, app):
        """Garde service : le claim JWT 'role' suffit a bloquer."""
        ta, super_admin, sales, client, vente = _make_context()
        from flask_jwt_extended import create_access_token, verify_jwt_in_request
        from app.services.facturation_service import (
            SuperAdminFactureInterdite,
            ensure_not_super_admin,
        )
        with app.test_request_context():
            token = create_access_token(
                identity=super_admin.id,
                additional_claims={'role': 'super_admin'},
            )
        with app.test_request_context(
            headers={'Authorization': 'Bearer ' + token}
        ):
            verify_jwt_in_request()
            with pytest.raises(SuperAdminFactureInterdite):
                ensure_not_super_admin()


class TestNonRegressionTenant:
    def test_utilisateur_tenant_peut_toujours_creer_une_facture(self, app):
        ta, super_admin, sales, client, vente = _make_context()
        c = app.test_client()
        headers = _login(c, 'vendeur_a', 'Sales123!')

        r = c.post('/api/v1/factures/', json={
            'vente_id': vente.id,
            'client_id': client.id,
            'reference': 'FAC-TENANT-1',
        }, headers=headers)

        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == ta.id
