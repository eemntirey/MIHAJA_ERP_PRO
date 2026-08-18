import pytest
from decimal import Decimal
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.produit import Produit
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.security.auth import hash_password


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def tenant(app):
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro'
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant


@pytest.fixture
def utilisateur(app, tenant):
    user = Utilisateur(
        username='testuser',
        email='test@test.com',
        password_hash=hash_password('password123'),
        role=Role.ADMIN,
        tenant_id=tenant.id
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestTenantModel:
    def test_create_tenant(self, app):
        tenant = Tenant(
            nom='Test Tenant',
            slug='test-slug',
            domaine='test.com',
            statut=StatutTenant.ACTIF
        )
        db.session.add(tenant)
        db.session.commit()
        
        assert tenant.id is not None
        assert tenant.nom == 'Test Tenant'
        assert tenant.slug == 'test-slug'
        assert tenant.statut == StatutTenant.ACTIF

    def test_tenant_utilisateurs_relation(self, app, tenant):
        user = Utilisateur(
            username='user1',
            email='user1@test.com',
            password_hash=hash_password('password'),
            tenant_id=tenant.id
        )
        db.session.add(user)
        db.session.commit()
        
        assert user in tenant.utilisateurs.all()


class TestMultiTenancy:
    def test_produit_tenant_isolation(self, app, tenant):
        # Créer deux produits pour le même tenant
        p1 = Produit(
            nom='Produit 1',
            reference='P001',
            tenant_id=tenant.id,
            prix_achat_ht=10,
            prix_vente_ht=15
        )
        p2 = Produit(
            nom='Produit 2',
            reference='P002',
            tenant_id=tenant.id,
            prix_achat_ht=20,
            prix_vente_ht=30
        )
        db.session.add_all([p1, p2])
        db.session.commit()
        
        # Vérifier l'isolation
        produits = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(produits) == 2
        
        # Un produit d'un autre tenant ne doit pas apparaître
        autre_tenant = Tenant(nom='Autre', slug='autre', statut=StatutTenant.ACTIF)
        db.session.add(autre_tenant)
        db.session.commit()
        p3 = Produit(
            nom='Produit 3',
            reference='P003',
            tenant_id=autre_tenant.id,
            prix_achat_ht=5,
            prix_vente_ht=10
        )
        db.session.add(p3)
        db.session.commit()
        
        produits_tenant1 = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(produits_tenant1) == 2
        assert p3 not in produits_tenant1

    def test_client_tenant_isolation(self, app, tenant):
        c1 = Client(
            code='CLI001',
            nom='Client 1',
            tenant_id=tenant.id
        )
        c2 = Client(
            code='CLI002',
            nom='Client 2',
            tenant_id=tenant.id
        )
        db.session.add_all([c1, c2])
        db.session.commit()
        
        clients = Client.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(clients) == 2

    def test_fournisseur_tenant_isolation(self, app, tenant):
        f1 = Fournisseur(
            code='FOU001',
            raison_sociale='Fournisseur 1',
            tenant_id=tenant.id
        )
        f2 = Fournisseur(
            code='FOU002',
            raison_sociale='Fournisseur 2',
            tenant_id=tenant.id
        )
        db.session.add_all([f1, f2])
        db.session.commit()
        
        fournisseurs = Fournisseur.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(fournisseurs) == 2

    def test_utilisateur_tenant_relation(self, app, tenant):
        user = Utilisateur(
            username='testuser',
            email='test@test.com',
            password_hash=hash_password('password'),
            tenant_id=tenant.id
        )
        db.session.add(user)
        db.session.commit()
        
        assert user.tenant_id == tenant.id
        assert user.tenant.id == tenant.id


class TestProduitModel:
    def test_produit_creation(self, app, tenant):
        produit = Produit(
            nom='Test Produit',
            reference='TEST001',
            prix_achat_ht=Decimal('10.00'),
            prix_vente_ht=Decimal('15.00'),
            quantite_stock=100,
            tenant_id=tenant.id
        )
        db.session.add(produit)
        db.session.commit()
        
        assert produit.id is not None
        assert produit.nom == 'Test Produit'
        assert produit.tenant_id == tenant.id
