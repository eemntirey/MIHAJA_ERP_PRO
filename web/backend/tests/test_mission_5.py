import json
import uuid
from datetime import datetime, timedelta

import pytest
from decimal import Decimal

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.client import Client
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement, ProviderPaiement
from app.models.fournisseur import Fournisseur, TypeFournisseur
from app.models.commande_achat import CommandeAchat, StatutCommandeAchat, ReceptionAchat
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.livraison import Livraison
from app.security.auth import hash_password, create_access_token_for_user


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('PAPI_API_URL', 'https://test.papi.mg/dashboard/api/payment-links')
    monkeypatch.setenv('PAPI_API_KEY', 'test-api-key')
    monkeypatch.setenv('PAPI_ENVIRONMENT', 'sandbox')
    monkeypatch.setenv('PAPI_CALLBACK_URL', 'http://localhost:5000/api/v1/papi/webhook')

    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def tenant_id(app):
    with app.app_context():
        tenant = Tenant(
            nom='Test Tenant Malagasy',
            slug='test-mg-mission5',
            domaine='test.mg',
            statut=StatutTenant.ACTIF,
            plan='pro',
            max_clients=50,
        )
        db.session.add(tenant)
        db.session.commit()

        abonnement = Abonnement(
            tenant_id=tenant.id,
            montant=79.0,
            plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            methode_paiement='especes',
            reference_paiement='SUB-MISSION5-001',
            is_active=True
        )
        db.session.add(abonnement)
        db.session.commit()
        return tenant.id


@pytest.fixture
def abonnement_id(app, tenant_id):
    with app.app_context():
        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=79.0,
            plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            methode_paiement='especes',
            reference_paiement='SUB-TEST-001',
            is_active=True,
        )
        db.session.add(abonnement)
        db.session.commit()
        return abonnement.id


@pytest.fixture
def utilisateur_id(app, tenant_id):
    with app.app_context():
        user = Utilisateur(
            username='testuser',
            email='test@test.mg',
            password_hash=hash_password('password123'),
            role=Role.ADMIN,
            tenant_id=tenant_id,
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def auth_headers(app, utilisateur_id):
    with app.app_context():
        user = db.session.get(Utilisateur, utilisateur_id)
        token = create_access_token_for_user(user)
    return {'Authorization': f'Bearer {token}'}


class TestWorkflowVenteComplet:
    """WORKFLOW VENTE COMPLET"""

    def test_workflow_vente_end_to_end(self, app, auth_headers, tenant_id, utilisateur_id, abonnement_id):
        with app.app_context():
            client = Client(
                code='CLI001',
                nom='Ravo',
                prenom='Jean',
                email='jean.ravo@test.mg',
                telephone='+261 34 123 4567',
                type='particulier',
                ville_facturation='Antananarivo',
                code_postal_facturation='101',
                pays_facturation='Madagascar',
                ville_livraison='Antananarivo',
                code_postal_livraison='101',
                pays_livraison='Madagascar',
            )
            db.session.add(client)
            db.session.commit()
            client_id = client.id

            product1 = Produit(
                reference='PROD001',
                nom='Riz Makalioka 25kg',
                unite='sac',
                prix_vente_ht=15000.00,
                prix_achat_ht=8000.00,
                taux_tva=20.00,
                quantite_stock=100,
                categorie='alimentaire',
                tenant_id=tenant_id,
            )
            product2 = Produit(
                reference='PROD002',
                nom='Huile Loulou 1L carton',
                unite='carton',
                prix_vente_ht=5000.00,
                prix_achat_ht=2500.00,
                taux_tva=20.00,
                quantite_stock=50,
                categorie='agricole',
                tenant_id=tenant_id,
            )
            db.session.add_all([product1, product2])
            db.session.commit()
            prod1_id = product1.id
            prod2_id = product2.id

            stock_prod1_before = float(product1.quantite_stock)
            stock_prod2_before = float(product2.quantite_stock)

        # Créer commande vente
        response = app.test_client().post(
            '/api/v1/ventes/',
            json={
                'client_id': client_id,
                'reference': 'VENT-TEST-001',
                'mode_paiement': 'especes',
                'lignes': [
                    {'produit_id': prod1_id, 'quantite': 5, 'prix_unitaire': 15000.00},
                    {'produit_id': prod2_id, 'quantite': 2, 'prix_unitaire': 5000.00},
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, f"Creation vente failed: {response.get_json()}"
        vente = response.get_json()
        vente_id = vente['id']

        with app.app_context():
            p1 = db.session.get(Produit, prod1_id)
            p2 = db.session.get(Produit, prod2_id)
            assert float(p1.quantite_stock) == stock_prod1_before - 5
            assert float(p2.quantite_stock) == stock_prod2_before - 2

        # Valider vente
        response = app.test_client().put(
            f'/api/v1/ventes/{vente_id}',
            json={'statut': 'confirmee'},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.get_json()['statut'] == 'confirmee'

        # Générer bon de livraison
        response = app.test_client().post(
            '/api/v1/livraisons/',
            json={
                'vente_id': vente_id,
                'adresse_livraison': 'Analakely',
                'ville_livraison': 'Antananarivo',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        livraison = response.get_json()
        livraison_id = livraison['id']

        response = app.test_client().post(
            f'/api/v1/livraisons/{livraison_id}/statut',
            json={'statut': 'livree', 'commentaire': 'Livrée à Antananarivo'},
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Facturer à crédit 15j
        response = app.test_client().post(
            f'/api/v1/factures/from-vente/{vente_id}',
            json={'reference': f'FAC-{vente["reference"]}', 'statut': 'non_payee'},
            headers=auth_headers,
        )
        assert response.status_code == 201
        facture = response.get_json()
        facture_id = facture['id']

        response = app.test_client().put(
            f'/api/v1/factures/{facture_id}',
            json={'statut': 'en_credit', 'conditions_paiement': '15 jours'},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Paiement partiel MVola
        part = round(float(facture['total_ttc']) * 0.6, 2)
        response = app.test_client().post(
            '/api/v1/paiements/',
            json={
                'facture_id': facture_id,
                'montant': part,
                'mode_paiement': 'MVOLA',
                'reference': f'PAY-MV-{uuid.uuid4().hex[:6].upper()}',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        paiement = response.get_json()
        assert float(paiement['montant']) == part

        response = app.test_client().get(f'/api/v1/factures/{facture_id}', headers=auth_headers)
        assert response.status_code == 200
        facture_after = response.get_json()
        assert facture_after['statut'] in ('payee_partiel', 'payee')


class TestWorkflowAchatComplet:
    """WORKFLOW ACHAT COMPLET"""

    def test_workflow_achat_end_to_end(self, app, auth_headers, tenant_id, utilisateur_id, abonnement_id):
        with app.app_context():
            fournisseur = Fournisseur(
                code='FOURN001',
                raison_sociale='DistriFood Madagascar',
                nom_commercial='DistriFood',
                email='contact@distrifood.mg',
                telephone='+261 34 987 6543',
                adresse='Analakely',
                ville='Antananarivo',
                code_postal='101',
                pays='Madagascar',
                type='fournisseur_local',
                est_actif=True,
            )
            db.session.add(fournisseur)
            db.session.commit()
            fournisseur_id = fournisseur.id

            produit = Produit(
                reference='PROD-ACHAT001',
                nom='Sac Riz 50kg',
                unite='sac',
                prix_achat_ht=7000.00,
                prix_vente_ht=15000.00,
                taux_tva=20.00,
                quantite_stock=0,
                categorie='alimentaire',
                tenant_id=tenant_id,
            )
            db.session.add(produit)
            db.session.commit()
            produit_id = produit.id

        # Passer commande fournisseur
        response = app.test_client().post(
            '/api/v1/commandes-achat/',
            json={
                'fournisseur_id': fournisseur_id,
                'reference': 'CA-TEST-001',
                'total_ht': 35000.0,
                'total_ttc': 42000.0,
                'conditions_paiement': '30 jours',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        commande = response.get_json()
        commande_id = commande['id']

        # Réceptionner en dépôt
        response = app.test_client().post(
            '/api/v1/receptions/',
            json={
                'commande_achat_id': commande_id,
                'reference': 'REC-TEST-001',
                'quantite_recue': 100,
                'quantite_commandee': 100,
                'receptionne_par_id': utilisateur_id,
                'remarque': 'Reception depot Antananarivo',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        reception = response.get_json()

        # Update stock after reception using stock API
        response = app.test_client().post(
            '/api/v1/stocks/',
            json={
                'produit_id': produit_id,
                'quantite': 100,
                'type_mouvement': 'entree',
                'raison': 'Reception CA-TEST-001',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        with app.app_context():
            p = db.session.get(Produit, produit_id)
            assert float(p.quantite_stock) == 100

        # Valider la dette
        response = app.test_client().put(
            f'/api/v1/commandes-achat/{commande_id}',
            json={'statut': 'recue', 'remarque': 'Dette validee'},
            headers=auth_headers,
        )
        assert response.status_code == 200
        commande_updated = response.get_json()
        assert commande_updated['statut'] == 'recue'

        # Effectuer un règlement partiel
        response = app.test_client().post(
            '/api/v1/paiements/',
            json={
                'montant': 21000.0,
                'mode_paiement': 'ESPECES',
                'reference': f'PAY-ESP-{uuid.uuid4().hex[:6].upper()}',
                'notes': 'Reglement partial commande fournisseur',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        paiement = response.get_json()
        assert float(paiement['montant']) == 21000.0


class TestInterfaceFormulaires:
    """INTERFACE & FORMULAIRES"""

    def test_ariary_amounts_and_malagasy_cities_and_units(self, app, auth_headers, tenant_id, utilisateur_id, abonnement_id):
        with app.app_context():
            client = Client(
                code='CLI-FORM',
                nom='FormTest',
                email='form@test.mg',
                telephone='+261 34 555 5555',
                type='particulier',
                ville_facturation='Antananarivo',
                code_postal_facturation='101',
                pays_facturation='Madagascar',
                ville_livraison='Antananarivo',
                code_postal_livraison='101',
                pays_livraison='Madagascar',
            )
            db.session.add(client)
            db.session.commit()
            client_id = client.id

            produit = Produit(
                reference='PROD-ARIARY',
                nom='Produit Test Ariary',
                unite='piece',
                prix_vente_ht=1000.00,
                prix_achat_ht=500.00,
                taux_tva=20.00,
                quantite_stock=50,
                categorie='test',
                tenant_id=tenant_id,
            )
            db.session.add(produit)
            db.session.commit()
            produit_id = produit.id

        # Saisie montant Ariary
        response = app.test_client().post(
            '/api/v1/ventes/',
            json={
                'client_id': client_id,
                'reference': 'VENT-ARIARY-TEST',
                'mode_paiement': 'MVOLA',
                'lignes': [
                    {'produit_id': produit_id, 'quantite': 3, 'prix_unitaire': 1000.00},
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        vente = response.get_json()
        assert round(float(vente['total_ttc']), 2) == 3600.00

        # Villes malgaches
        cities = [
            ('Antananarivo', '101'),
            ('Toamasina', '501'),
            ('Antsirabe', '110'),
            ('Fianarantsoa', '301'),
            ('Mahajanga', '401'),
            ('Toliara', '601'),
            ('Antsiranana', '201'),
        ]
        with app.app_context():
            created_clients = []
            for city, cp in cities:
                c = Client(
                    code=f'CLI-CITY-{city}',
                    nom=f'Test {city}',
                    email=f'test-{city}@test.mg',
                    telephone='+261 34 111 1111',
                    type='particulier',
                    ville_facturation=city,
                    code_postal_facturation=cp,
                    pays_facturation='Madagascar',
                    ville_livraison=city,
                    code_postal_livraison=cp,
                    pays_livraison='Madagascar',
                )
                db.session.add(c)
                created_clients.append(c)
            db.session.commit()
            for c in created_clients:
                assert c.ville_facturation in [city for city, _ in cities]

        # Unités produit
        units = ['piece', 'sac', 'carton', 'kg', 'litres', 'unité']
        with app.app_context():
            for u in units:
                p = Produit(
                    reference=f'PROD-U-{u}',
                    nom=f'Test {u}',
                    unite=u,
                    prix_vente_ht=1000.00,
                    prix_achat_ht=500.00,
                    taux_tva=20.00,
                    quantite_stock=10,
                    categorie='test',
                    tenant_id=tenant_id,
                )
                db.session.add(p)
            db.session.commit()
            for u in units:
                p = db.session.query(Produit).filter_by(reference=f'PROD-U-{u}').first()
                assert p is not None
                assert p.unite == u
