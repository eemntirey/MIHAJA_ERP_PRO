"""Tests de conformité pour le catalogue public — Protection du stock et des données privées.

Vérifie :
- §1  : Produit publié avec stock > seuil => visible publiquement
- §2  : Produit au seuil d'alerte => masqué du catalogue public
- §3  : Produit sous le seuil d'alerte => masqué du catalogue public
- §4  : Produit à stock zéro => masqué du catalogue public
- §5  : Produit non publié => masqué du catalogue public
- §6  : API publique ne retourne jamais stock_quantity, prix d'achat, marge, fournisseur_id
- §7  : Produit masqué sans révéler la raison (absent, pas message "stock faible")
"""
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.produit import Produit
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch, tmp_path):
    db_file = tmp_path / 'test.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db_file}')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    application = create_app()
    application.config['TESTING'] = True
    application.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'timeout': 30},
    }
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.engine.dispose()
        db.drop_all()


def _make_tenant_and_admin(client, name, email, plan='starter'):
    tenant = Tenant(
        nom=name,
        slug=name.lower().replace(' ', '-'),
        domaine=f'{name.lower().replace(" ", "-")}.test',
        statut=StatutTenant.ACTIF,
        plan=plan,
    )
    db.session.add(tenant)
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=tenant.id,
        montant=100.0,
        plan=plan,
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    ))
    admin = Utilisateur(
        username=email,
        email=email,
        password_hash=hash_password('Companie123'),
        nom='Admin',
        prenom='Test',
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
        is_principal_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    return tenant, admin


def _auth(client, email, password='Companie123'):
    r = client.post('/api/v1/auth/login', json={
        'username': email,
        'password': password,
    })
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestPublicCatalogStockFiltering:

    def test_published_product_above_alert_is_visible(self, app):
        """Produit publié avec stock > seuil => visible publiquement."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant Visible', 'tv@test.mg')
        produit = Produit(
            nom='Produit Visible',
            reference='VIS-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=20,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        db.session.add(produit)
        db.session.commit()

        r = client.get('/public/produits')
        assert r.status_code == 200
        data = r.get_json()
        ids = [p['id'] for p in data.get('produits', [])]
        assert produit.id in ids

    def test_product_at_alert_threshold_is_hidden(self, app):
        """Produit au seuil d'alerte (stock == seuil) => masqué."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant Seuil', 'ts@test.mg')
        produit = Produit(
            nom='Produit Seuil',
            reference='SEUIL-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=5,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        db.session.add(produit)
        db.session.commit()

        r = client.get('/public/produits')
        assert r.status_code == 200
        data = r.get_json()
        ids = [p['id'] for p in data.get('produits', [])]
        assert produit.id not in ids

    def test_product_below_alert_threshold_is_hidden(self, app):
        """Produit sous le seuil d'alerte => masqué."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant Bas', 'tb@test.mg')
        produit = Produit(
            nom='Produit Bas',
            reference='BAS-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=3,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        db.session.add(produit)
        db.session.commit()

        r = client.get('/public/produits')
        assert r.status_code == 200
        data = r.get_json()
        ids = [p['id'] for p in data.get('produits', [])]
        assert produit.id not in ids

    def test_product_zero_stock_is_hidden(self, app):
        """Produit à stock zéro => masqué."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant Zero', 'tz@test.mg')
        produit = Produit(
            nom='Produit Zero',
            reference='ZERO-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=0,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        db.session.add(produit)
        db.session.commit()

        r = client.get('/public/produits')
        assert r.status_code == 200
        data = r.get_json()
        ids = [p['id'] for p in data.get('produits', [])]
        assert produit.id not in ids

    def test_unpublished_product_is_hidden(self, app):
        """Produit non publié => masqué."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant NonPub', 'tnp@test.mg')
        produit = Produit(
            nom='Produit Non Publié',
            reference='NONPUB-001',
            tenant_id=tenant.id,
            published=False,
            quantite_stock=100,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        db.session.add(produit)
        db.session.commit()

        r = client.get('/public/produits')
        assert r.status_code == 200
        data = r.get_json()
        ids = [p['id'] for p in data.get('produits', [])]
        assert produit.id not in ids

    def test_public_api_never_exposes_sensitive_fields(self, app):
        """API publique ne retourne jamais stock, prix d'achat, marge, fournisseur."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant Sensible', 'tsens@test.mg')
        produit = Produit(
            nom='Produit Sensible',
            reference='SENS-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=20,
            seuil_alerte=5,
            prix_achat_ht=500,
            prix_vente_ht=1000,
            marge_standard=50,
            fournisseur_id=1,
        )
        db.session.add(produit)
        db.session.commit()

        r = client.get('/public/produits')
        assert r.status_code == 200
        data = r.get_json()
        produits = data.get('produits', [])
        assert len(produits) == 1
        p = produits[0]

        assert 'quantite_stock' not in p
        assert 'stock' not in p
        assert 'prix_achat_ht' not in p
        assert 'prix_achat_ttc' not in p
        assert 'marge_standard' not in p
        assert 'fournisseur_id' not in p
        assert 'valeur_stock' not in p
        assert 'marge_unitaire' not in p
        assert 'taux_marge' not in p
        assert 'stock_avant' not in p
        assert 'stock_apres' not in p

    def test_hidden_product_does_not_reveal_reason(self, app):
        """Produit masqué => simplement absent, pas de message 'stock faible'."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant Secret', 'tsec@test.mg')
        produit = Produit(
            nom='Produit Secret',
            reference='SEC-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=2,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        db.session.add(produit)
        db.session.commit()

        r = client.get('/public/produits')
        assert r.status_code == 200
        data = r.get_json()
        produits = data.get('produits', [])
        assert produit.id not in [p['id'] for p in produits]

        # Le détail individuel doit aussi retourner 404
        r2 = client.get(f'/public/produits/{produit.id}')
        assert r2.status_code == 404

    def test_public_product_detail_respects_stock_rule(self, app):
        """Détail public d'un produit respecte les mêmes règles que la liste."""
        client = app.test_client()
        tenant, _ = _make_tenant_and_admin(client, 'Tenant Detail', 'td@test.mg')

        produit_visible = Produit(
            nom='Produit Visible Detail',
            reference='VIS-DET-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=20,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        produit_cache = Produit(
            nom='Produit Cache Detail',
            reference='CACHE-DET-001',
            tenant_id=tenant.id,
            published=True,
            quantite_stock=2,
            seuil_alerte=5,
            prix_vente_ht=1000,
        )
        db.session.add_all([produit_visible, produit_cache])
        db.session.commit()

        r_visible = client.get(f'/public/produits/{produit_visible.id}')
        assert r_visible.status_code == 200
        assert 'quantite_stock' not in r_visible.get_json()

        r_cache = client.get(f'/public/produits/{produit_cache.id}')
        assert r_cache.status_code == 404
