import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.document_genere import DocumentGenere
from app.models.modele_document import ModeleDocument
from app.security.auth import hash_password


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


def _make_tenant():
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro'
    )
    db.session.add(tenant)
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=tenant.id,
        montant=100.0,
        plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    ))
    user = Utilisateur(
        username='admin',
        email='admin@test.com',
        password_hash=hash_password('Admin123!'),
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(user)
    db.session.commit()
    return tenant, user


def _login(client, email, password, tenant_slug=None):
    payload = {'username': email, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestDashboardAPI:
    def test_dashboard_returns_stats(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.get('/api/v1/dashboard/', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'stats' in data

    def test_sales_stats(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.get('/api/v1/dashboard/sales-stats', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'ca_total' in data
        assert 'ventes_mois' in data


class TestSubscriptionAPI:
    def test_create_subscription(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/abonnements/demander', json={
            'montant': 100.0,
            'plan': 'pro',
        }, headers=headers)
        assert r.status_code == 201
        data = r.get_json()
        assert 'abonnement' in data

    def test_get_my_subscription(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.get('/api/v1/abonnements/mon-abonnement', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'abonnement' in data


class TestNotificationAPI:
    def test_create_and_list_notifications(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/notifications', json={
            'title': 'Test',
            'message': 'Hello',
            'type': 'info',
        }, headers=headers)
        assert r.status_code == 201
        r = client.get('/api/v1/notifications', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)


class TestAccountingAPI:
    def test_create_account(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/comptes', json={
            'numero': '701',
            'nom': 'Ventes',
            'type_compte': 'produit',
        }, headers=headers)
        assert r.status_code == 201
        data = r.get_json()
        assert data['numero'] == '701'

    def test_create_entry(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        compte = client.post('/api/v1/comptes', json={
            'numero': '701',
            'nom': 'Ventes',
            'type_compte': 'produit',
        }, headers=headers).get_json()
        r = client.post('/api/v1/ecritures', json={
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'compte_id': compte['id'],
            'montant_debit': 0,
            'montant_credit': 100,
            'libelle': 'Test entry',
        }, headers=headers)
        assert r.status_code == 201


class TestDeliveryAPI:
    def test_create_delivery(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/livraisons', json={
            'adresse_livraison': '123 Main St',
            'statut': 'en_attente',
        }, headers=headers)
        assert r.status_code == 201


class TestDocumentAPI:
    def test_create_document(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        modele = ModeleDocument(
            nom='Test Modele',
            type_document='facture',
            contenu_modele='<html>{{reference}}</html>',
            tenant_id=tenant.id,
        )
        db.session.add(modele)
        db.session.commit()
        r = client.post('/api/v1/documents', json={
            'modele_id': modele.id,
            'type_document': 'facture',
            'reference': 'DOC-001',
            'entite_type': 'vente',
            'entite_id': 1,
            'contenu_html': '<html>DOC-001</html>',
        }, headers=headers)
        assert r.status_code == 201


class TestPublicAPI:
    def test_public_catalogue(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        produit = Produit(
            nom='Public Product',
            reference='PUB-001',
            tenant_id=tenant.id,
            prix_achat_ht=10,
            prix_vente_ht=15,
        )
        db.session.add(produit)
        db.session.commit()
        r = client.get('/public/produits')
        assert r.status_code == 200

    def test_public_checkout(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        produit = Produit(
            nom='Public Product',
            reference='PUB-002',
            tenant_id=tenant.id,
            prix_achat_ht=10,
            prix_vente_ht=15,
            quantite_stock=100,
        )
        db.session.add(produit)
        db.session.commit()
        r = client.post('/public/commandes', json={
            'nom_client': 'John Doe',
            'email_client': 'john@example.com',
            'items': [{'produit_id': produit.id, 'quantite': 2}],
        })
        assert r.status_code == 201
