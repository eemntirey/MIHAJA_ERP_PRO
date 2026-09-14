"""Idempotence facturation — audit 14/09/2026, défaut #6.

Une double soumission avait créé 3 factures (#5, #6, #7) pour la même
vente. Garanties testées ici :
- 1er  POST /api/v1/factures/  -> 201 ;
- POST suivant sur la MÊME vente -> 409 avec la facture existante
  renvoyée (idempotence), et jamais une 2e facture en base ;
- payload invalide -> 400 explicite, jamais 500 générique ;
- deux ventes distinctes -> deux factures (pas de faux conflit).
"""
import pytest
import uuid
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.client import Client
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password, create_access_token_for_user
from tests._db_utils import reset_schema

_TEST_DB = 'postgresql+psycopg://postgres:<REDACTED_DB_PASSWORD>@localhost:55432/erp_test'


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', _TEST_DB)
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key')
    application = create_app()
    application.config['TESTING'] = True
    with application.app_context():
        # Etat hermetique : schema propre + roles/permissions seedes pour
        # chaque test (le fixture `app` de ce module remplace celui du
        # conftest, qui ne serait sinon pas execute).
        reset_schema(db)
        db.create_all()
        from scripts.seed_roles import seed_roles
        seed_roles()
        yield application
        db.session.rollback()


@pytest.fixture
def tenant(app):
    suffix = uuid.uuid4().hex[:8]
    tenant = Tenant(
        nom=f'Tenant Facturation {suffix}',
        slug=f'tenant-facturation-{suffix}',
        domaine=f'facturation-{suffix}.local',
        statut=StatutTenant.ACTIF,
        plan='pro',
    )
    db.session.add(tenant)
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=tenant.id,
        montant=79.0,
        plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    ))
    db.session.commit()
    return tenant


@pytest.fixture
def utilisateur(app, tenant):
    user = Utilisateur(
        username='factadmin',
        email='factadmin@test.com',
        password_hash=hash_password('password123'),
        role=Role.ADMIN,
        tenant_id=tenant.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_headers(app, utilisateur):
    with app.app_context():
        token = create_access_token_for_user(utilisateur)
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def client_obj(app, tenant):
    client = Client(
        code='CLI-FAC-001',
        nom='Rakoto',
        prenom='Jean',
        email='rakoto@test.mg',
        tenant_id=tenant.id,
    )
    db.session.add(client)
    db.session.commit()
    return client


def _make_vente(ref_suffix):
    vente = Vente(
        reference=f'VENTE-{ref_suffix}',
        client_id=Client.query.first().id,
        tenant_id=Tenant.query.first().id,
        total_ht=10000,
        total_ttc=11000,
    )
    db.session.add(vente)
    db.session.commit()
    return vente


class TestFactureIdempotence:
    def test_double_soumission_meme_vente_une_seule_facture(
        self, app, auth_headers, tenant, client_obj
    ):
        """Defaut #6 : la double soumission ne doit pas dupliquer la facture."""
        with app.app_context():
            vente = _make_vente('IDEM-001')
            test_client = app.test_client()
            payload = {'vente_id': vente.id, 'client_id': client_obj.id}

            r1 = test_client.post('/api/v1/factures/', json=payload, headers=auth_headers)
            assert r1.status_code == 201, r1.get_json()
            ref_1 = r1.get_json()['reference']

            # Double soumission (double-clic, retry reseau, refresh)
            r2 = test_client.post('/api/v1/factures/', json=payload, headers=auth_headers)
            assert r2.status_code == 409, r2.get_json()
            body = r2.get_json()
            assert body.get('facture'), 'La facture existante doit etre renvoyee'
            assert body['facture']['reference'] == ref_1

            # Une seule facture active pour cette vente en base
            assert Facture.query.filter_by(
                vente_id=vente.id, is_active=True
            ).count() == 1

    def test_payload_invalide_400_pas_500(self, app, auth_headers, tenant, client_obj):
        """Validation serveur : vente_id ou client_id manquant -> 400 explicite."""
        with app.app_context():
            vente = _make_vente('INVAL-001')
            test_client = app.test_client()

            r = test_client.post(
                '/api/v1/factures/',
                json={'vente_id': vente.id},  # client_id manquant
                headers=auth_headers,
            )
            assert r.status_code == 400, r.get_json()
            assert 'client_id' in r.get_json()['message']

    def test_ventes_distinctes_factures_distinctes(
        self, app, auth_headers, tenant, client_obj
    ):
        """L'idempotence ne doit pas bloquer les ventes legitimes distinctes."""
        with app.app_context():
            vente_a = _make_vente('OK-A')
            vente_b = _make_vente('OK-B')
            test_client = app.test_client()

            r1 = test_client.post(
                '/api/v1/factures/',
                json={'vente_id': vente_a.id, 'client_id': client_obj.id},
                headers=auth_headers,
            )
            r2 = test_client.post(
                '/api/v1/factures/',
                json={'vente_id': vente_b.id, 'client_id': client_obj.id},
                headers=auth_headers,
            )
            assert r1.status_code == 201, r1.get_json()
            assert r2.status_code == 201, r2.get_json()
            assert r1.get_json()['reference'] != r2.get_json()['reference']
