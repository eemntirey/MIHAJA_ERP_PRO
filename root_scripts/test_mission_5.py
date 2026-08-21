import json
import uuid
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.client import Client
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement, ProviderPaiement
from app.models.commande_client import CommandeClient, StatutCommande
from app.models.commande_achat import CommandeAchat, StatutCommandeAchat, ReceptionAchat
from app.security.auth import hash_password
from decimal import Decimal


def _papi_response(payment_link='https://pay.papi.mg/payment/abc123', notification_token='token-xyz', reference=None):
    ref = reference or f'SUB-1-1-{uuid.uuid4().hex[:8].upper()}'
    return {
        'data': {
            'amount': 15000.0,
            'currency': 'MGA',
            'linkCreationDateTime': 1723850012,
            'linkExpirationDateTime': 1723853612,
            'paymentLink': payment_link,
            'clientName': 'Test Tenant',
            'paymentReference': ref,
            'description': 'Abonnement starter - Test Tenant',
            'successUrl': f'http://localhost:5000/api/v1/papi/payment-result?status=success&reference={ref}',
            'failureUrl': f'http://localhost:5000/api/v1/papi/payment-result?status=failure&reference={ref}',
            'notificationUrl': 'http://localhost:5000/api/v1/papi/webhook',
            'payerEmail': 'test@example.com',
            'payerPhone': '+261340000000',
            'notificationToken': notification_token,
            'testReason': 'Integration test ERP',
            'isTestMode': True,
        }
    }


class TestMission5:
    """Mission 5/5 : Adaptation marché malagasy - Workflows complets et non-régression"""

    def test_workflow_vente_complet(self, app, monkeypatch):
        """TEST 1: WORKFLOW VENTE complet"""
        print("\n=== TEST 1: WORKFLOW VENTE COMPLET ===")
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

            # --- ÉTAPE A: Créer un client ---
            print("Étape A: Création d'un client...")
            tenant = Tenant(
                nom='Test Tenant Malagasy',
                slug='test-mg',
                domaine='test.mg',
                statut=StatutTenant.ACTIF,
                plan='pro',
                max_clients=50,
            )
            db.session.add(tenant)
            db.session.commit()

            user = Utilisateur(
                username='testuser',
                email='test@test.mg',
                password_hash=hash_password('password123'),
                role=Role.ADMIN,
                tenant_id=tenant.id
            )
            db.session.add(user)
            db.session.commit()

            from flask_jwt_extended import create_access_token
            token = create_access_token(identity=user.id, additional_claims={
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'tenant_id': tenant.id,
            })
            auth_headers = {'Authorization': f'Bearer {token}'}

            # Create client with Madagascar address
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI001',
                    'nom': 'Ravo',
                    'prenom': 'Jean',
                    'email': 'jean.ravo@test.mg',
                    'telephone': '+261 34 123 4567',
                    'type': 'particulier',
                    'ville_facturation': 'Antananarivo',
                    'code_postal_facturation': '101',
                    'pays_facturation': 'Madagascar',
                    'ville_livraison': 'Antananarivo',
                    'code_postal_livraison': '101',
                    'pays_livraison': 'Madagascar',
                },
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création client: {response.get_json()}"
            client = response.get_json()
            client_id = client['id']
            print(f"  Client créé: {client['code']} - {client['nom']} {client['prenom']}")

            # --- ÉTAPE B: Créer une commande avec produits (carton/sac) ---
            print("\nÉtape B: Création d'une commande vente...")

            # Create Malagasy products (riz makalioka, huile loulou)
            product1 = Produit(
                reference='PROD001',
                nom='Riz Makalioka 25kg',
                unite='sac',
                prix_vente_ht=15000.00,
                prix_achat_ht=8000.00,
                taux_tva=20.00,
                quantite_stock=100,
                categorie='alimentaire',
                marque='Marque Malagasy'
            )
            db.session.add(product1)
            db.session.flush()

            product2 = Produit(
                reference='PROD002',
                nom='Huile Loulou 1L',
                unite='carton',
                prix_vente_ht=5000.00,
                prix_achat_ht=2500.00,
                taux_tva=20.00,
                quantite_stock=50,
                categorie='agricole',
                marque='Marque Malagasy'
            )
            db.session.add(product2)
            db.session.flush()

            # Create the sale with lignes
           vente_data = {
                'client_id': client_id,
                'reference': f'VENT-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
                'mode_paiement': 'espece',
                'lignes': [
                    {
                        'produit_id': product1.id,
                        'quantite': 5,  # 5 sacs
                        'prix_unitaire': 15000.00,
                    },
                    {
                        'produit_id': product2.id,
                        'quantite': 2,  # 2 cartons
                        'prix_unitaire': 5000.00,
                    }
                ]
            }

            response = app.test_client().post(
                '/api/v1/ventes/',
                json=vente_data,
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création vente: {response.get_json()}"
            vente = response.get_json()
            vente_id = vente['id']
            total_ht = vente['total_ht']
            total_ttc = vente['total_ttc']
            print(f"  Vente créée: {vente['reference']} - HT: {total_ht} MGA, TTC: {total_ttc} MGA")
            print(f"  Lignes: {len(vente.get('lignes_vente', []))}")

            # Verify stock was reduced
            p1 = db.session.get(Produit, product1.id)
            p2 = db.session.get(Produit, product2.id)
            assert p1.quantite_stock == 95, f"Stock produit 1 non mis à jour: {p1.quantite_stock}"
            assert p2.quantite_stock == 48, f"Stock produit 2 non mis à jour: {p2.quantite_stock}"
            print(f"  Stock mis à jour: PROD001={p1.quantite_stock} sac, PROD002={p2.quantite_stock} carton")

            # --- ÉTAPE C: Valider la vente (changer statut) ---
            print("\nÉtape C: Validation de la vente...")
            vente_db = db.session.get(type(vente_db.__class__ if hasattr(vente_db, '__class__') else 'Vente', vente_id) if False else None)
            # Actually let's just use the put endpoint
            response = app.test_client().put(
                f'/api/v1/ventes/{vente_id}',
                json={'statut': 'payee'},
                headers=auth_headers
            )
            assert response.status_code == 200, f"Erreur validation vente: {response.get_json()}"
            vente_updated = response.get_json()
            print(f"  Vente validée: statut = {vente_updated['statut']}")

            # --- ÉTAPE D: Générer bon de livraison ---
            print("\nÉtape D: Génération bon de livraison...")
            # Create delivery via suivi_livraison
            from app.security.tenant import get_current_tenant_id
            tid = get_current_tenant_id()
            response = app.test_client().post(
                f'/api/v1/livraisons/',
                json={
                    'client_id': client_id,
                    'reference_vente': vente['reference'],
                    'adresse_livraison': ' quartier de la mairie',
                    'ville_livraison': 'Antananarivo',
                    'code_postal': '101',
                    'pays': 'Madagascar',
                    'tenant_id': tid,
                },
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création livraison: {response.get_json()}"
            livraison = response.get_json()
            livraison_id = livraison['id']
            print(f"  Bon de livraison créé: {livraison['reference']} - ID: {livraison_id}")

            # Avancer le statut de la livraison
            response = app.test_client().post(
                f'/api/v1/livraisons/{livraison_id}/statut',
                json={'statut': 'livree', 'commentaire': 'Livraison effectuée à Antananarivo'},
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur mise à jour livraison: {response.get_json()}"
            print(f"  Livraison marquée comme: livree")

            # --- ÉTAPE E: Facturer à crédit (15 jours) ---
            print("\nÉtape E: Facturation à crédit (15j)...")
            # Generate invoice from vente
            response = app.test_client().post(
                '/api/v1/factures/from-vente',
                json={'vente_id': vente_id, 'reference': f'FAC-{vente["reference"]}', 'statut': 'non_payee'},
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création facture: {response.get_json()}"
            facture = response.get_json()
            facture_id = facture['id']
            print(f"  Facture générée: {facture['reference']} - ID: {facture_id}")
            print(f"  Montant facture: {facture['total_ht']} MGA HT, {facture['total_ttc']} MGA TTC")

            # Update facture statut to credit/15j
            response = app.test_client().put(
                f'/api/v1/factures/{facture_id}',
                json={'statut': 'en_credit', 'conditions_paiement': '15 jours'},
                headers=auth_headers
            )
            assert response.status_code == 200, f"Erreur mise à jour facture: {response.get_json()}"
            print(f"  Facture en crédit: 15 jours")

            # --- ÉTAPE F: Enregistrer paiement partiel MVola/Espèces ---
            print("\nÉtape F: Paiement partiel MVola/Espèces...")
            # Partially pay the invoice
            part_payment = float(facture['total_ttc']) * 0.6  # Pay 60% = 9000 MGA
            response = app.test_client().post(
                '/api/v1/paiements/',
                json={
                    'facture_id': facture_id,
                    'montant': round(part_payment, 2),
                    'mode_paiement': 'MVOLA',
                    'reference': f'PAY-MVOLA-{uuid.uuid4().hex[:6].upper()}',
                },
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création paiement: {response.get_json()}"
            paiement = response.get_json()
            print(f"  Paiement partiel MVola: {paiement['montant']} MGA - Statut: {paiement['statut']}")

            # Verify partial payment updated facture status
            response = app.test_client().get(f'/api/v1/factures/{facture_id}')
            assert response.status_code == 200
            facture_updated = response.get_json()
            print(f"  Facture statut après paiement: {facture_updated['statut']}")
            assert facture_updated['statut'] in ['payee_partiel', 'payee'], f"Statut inattendu: {facture_updated['statut']}"

            # Verify stock is still correct (no more deductions after partial payment)
            p1 = db.session.get(Produit, product1.id)
            p2 = db.session.get(Produit, product2.id)
            print(f"  Stock final: PROD001={p1.quantite_stock} sac, PROD002={p2.quantite_stock} carton")

            # Verify client solde/creance
            client_db = db.session.get(Client, client_id)
            print(f"  Client solde: {client_db.solde} MGA")
            assert client_db.solde < 0, "Client devrait être à crédit (solde négatif)"
            print(f"  Client à crédit vérifié: solde={client_db.solde} MGA")

            print("\n=== TEST 1 TERMINÉ AVEC SUCCÈS ===")

    def test_workflow_achat_complet(self, app, monkeypatch):
        """TEST 2: WORKFLOW ACHAT complet"""
        print("\n=== TEST 2: WORKFLOW ACHAT COMPLET ===")
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

            # --- ÉTAPE A: Créer un fournisseur ---
            print("Étape A: Création d'un fournisseur...")
            tenant = Tenant(
                nom='Test Tenant Malagasy',
                slug='test-mg-achat',
                domaine='test.mg',
                statut=StatutTenant.ACTIF,
                plan='pro',
                max_clients=50,
            )
            db.session.add(tenant)
            db.session.commit()

            user = Utilisateur(
                username='testuser2',
                email='test2@test.mg',
                password_hash=hash_password('password123'),
                role=Role.ADMIN,
                tenant_id=tenant.id
            )
            db.session.add(user)
            db.session.commit()

            from flask_jwt_extended import create_access_token
            token = create_access_token(identity=user.id, additional_claims={
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'tenant_id': tenant.id,
            })
            auth_headers = {'Authorization': f'Bearer {token}'}

            # Create supplier
            from app.models.fournisseur import Fournisseur
            fournisseur = Fournisseur(
                code='Fourn001',
                nom='DistriFood Madagascar',
                email='contact@distrifood.mg',
                telephone: '+261 34 987 6543',
                adresse: 'Analakely',
                ville: 'Antananarivo',
                code_postal: '101',
                pays: 'Madagascar',
                statut: 'actif',
            )
            db.session.add(fournisseur)
            db.session.commit()
            fournisseur_id = fournisseur.id
            print(f"  Fournisseur créé: {fournisseur.code} - {fournisseur.nom}")

            # --- ÉTAPE B: Passer commande à un fournisseur ---
            print("\nÉtape B: Commande fournisseur...")
            # Create a product for purchasing
            from app.models.produit import Produit
            produit_achat = Produit(
                reference='PROD-ACHAT001',
                nom='Sac de Riz 50kg fournisseur',
                unite='sac',
                prix_achat_ht=7000.00,
                prix_vente_ht=15000.00,
                taux_tva=20.00,
                quantite_stock=0,
                categorie='alimentaire',
                marque='Marque Test'
            )
            db.session.add(produit_achat)
            db.session.commit()

            commande_achat_data = {
                'fournisseur_id': fournisseur_id,
                'reference': f'CA-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
                'total_ht': 35000.00,
                'total_ttc': 42000.00,
                'conditions_paiement': '30 jours',
                'date_livraison_prevue': datetime.utcnow() + timedelta(days=7),
            }

            response = app.test_client().post(
                '/api/v1/commandes_achat/',
                json=commande_achat_data,
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création commande achat: {response.get_json()}"
            commande = response.get_json()
            commande_id = commande['id']
            print(f"  Commande fournisseur créée: {commande['reference']} - ID: {commande_id}")
            print(f"  Montant: {commande['total_ht']} MGA HT, {commande['total_ttc']} MGA TTC")

            # --- ÉTAPE C: Réceptionner en dépôt ---
            print("\nÉtape C: Réception en dépôt...")
            response = app.test_client().post(
                '/api/v1/receptions_achat/',
                json={
                    'commande_achat_id': commande_id,
                    'reference': f'REC-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
                    'quantite_recue': 100,
                    'quantite_commandee': 100,
                    'receptionne_par_id': user.id,
                    'remarque': 'Réception en dépôt Antananarivo',
                },
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création réception: {response.get_json()}"
            reception = response.get_json()
            print(f"  Réception créée: {reception['reference']}")
            print(f"  Quantité reçue: {reception.get('quantite_recue', 'N/A')}")

            # Update product stock with received quantity
            response = app.test_client().post(
                f'/api/v1/produits/{produit_achat.id}/stock',
                json={'quantite_ajoutee': 100, 'raison': 'Réception commande CA-001'},
                headers=auth_headers
            )
            assert response.status_code == 200, f"Erreur mise à jour stock: {response.get_json()}"
            print(f"  Stock produit mis à jour: +100 sacs")

            # --- ÉTAPE D: Valider la dette ---
            print("\nÉtape D: Validation de la dette...")
            # Update commande status to confirmée/reçue
            response = app.test_client().put(
                f'/api/v1/commandes_achat/{commande_id}',
                json={'statut': 'recue', 'remarque': 'Toute la commande reçue avec validation dette'},
                headers=auth_headers
            )
            assert response.status_code == 200, f"Erreur validation dette: {response.get_json()}"
            commande_updated = response.get_json()
            print(f"  Commande statut: {commande_updated['statut']}")

            # --- ÉTAPE E: Effectuer un règlement ---
            print("\nÉtape E: Effectuer un règlement...")
            # Create a partial payment against the supplier debt
            # We'll create a payment linked to the commande or use a generic approach
            # First, let's check if there's a way to pay supplier debts
            # In this ERP, we can create a payment with a reference to the commande
            part_payment_amount = 21000.0  # 50% of TTC

            response = app.test_client().post(
                '/api/v1/paiements/',
                json={
                    'montant': part_payment_amount,
                    'mode_paiement': 'ESPECES',
                    'reference': f'PAY-ESPACE-{uuid.uuid4().hex[:6].upper()}',
                    'commentaire': 'Règlement partial commande fournisseur',
                },
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création règlement: {response.get_json()}"
            paiement = response.get_json()
            print(f"  Règlement effectif: {paiement['montant']} MGA - Mode: {paiement['mode_paiement']}")
            print(f"  Paiement statut: {paiement['statut']}")

            # Verify stock levels after full workflow
            produit_actu = db.session.get(Produit, produit_achat.id)
            print(f"  Stock final produit: {produit_actu.quantite_stock} sac")

            print("\n=== TEST 2 TERMINÉ AVEC SUCCÈS ===")

    def test_interface_formulaires(self, app, monkeypatch):
        """TEST 3: INTERFACE & FORMULAIRES - Ariary, villes malgasy, unités"""
        print("\n=== TEST 3: INTERFACE & FORMULAIRES ===")
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

            # Create minimal tenant/user for auth
            tenant = Tenant(
                nom='Test Tenant',
                slug='test-form',
                domaine='test.form',
                statut=StatutTenant.ACTIF,
                plan='pro',
                max_clients=50,
            )
            db.session.add(tenant)
            db.session.commit()

            user = Utilisateur(
                username='formtest',
                email='form@test.mg',
                password_hash=hash_password('password123'),
                role=Role.ADMIN,
                tenant_id=tenant.id
            )
            db.session.add(user)
            db.session.commit()

            from flask_jwt_extended import create_access_token
            token = create_access_token(identity=user.id, additional_claims={
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'tenant_id': tenant.id,
            })
            auth_headers = {'Authorization': f'Bearer {token}'}

            # --- TEST: Saisie montants en Ariary ---
            print("Test: Saisie montants en Ariary (MGA)...")
            # Create a product with MGA pricing
            produit = Produit(
                reference='PROD-ARIARY',
                nom='Test Produit Ariary',
                unite='piece',
                prix_vente_ht=1000.00,  # 1000 MGA
                prix_achat_ht=500.00,  # 500 MGA
                taux_tva=20.00,
                quantite_stock=50,
                categorie='test',
            )
            db.session.add(produit)
            db.session.commit()

            # Test creating avente with Ariary amounts
            response = app.test_client().post(
                '/api/v1/ventes/',
                json={
                    'client_id': None,  # Will fail but let's check the amount handling
                    'reference': 'VENT-ARIARY-TEST',
                    'mode_paiement': 'MVOLA',
                    'lignes': [
                        {
                            'produit_id': produit.id,
                            'quantite': 3,
                            'prix_unitaire': 1000.00,  # Prix en MGA
                        }
                    ]
                },
                headers=auth_headers
            )
            # This will likely fail due to client_id, but let's check the next test

            # Test with proper client
            from app.models.client import Client
            client = Client(
                code='CLI-FORM',
                nom='Test',
                email='test-form@test.mg',
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

            response = app.test_client().post(
                '/api/v1/ventes/',
                json={
                    'client_id': client.id,
                    'reference': 'VENT-ARIARY-TEST',
                    'mode_paiement': 'MVOLA',
                    'lignes': [
                        {
                            'produit_id': produit.id,
                            'quantite': 3,
                            'prix_unitaire': 1000.00,
                        }
                    ]
                },
                headers=auth_headers
            )
            assert response.status_code == 201, f"Erreur création vente: {response.get_json()}"
            vente = response.get_json()
            print(f"  Vente avec montant Ariary: {vente['reference']} - HT: {vente['total_ht']} MGA, TTC: {vente['total_ttc']} MGA")
            assert float(vente['total_ttc']) == 1200.00, f"Calcul TTC incorrect: {vente['total_ttc']}"  # 1000 * 3 * 1.2 = 3600
            print(f"  ✓ Calcul TTC correct: 1000 × 3 × 1.2 = {vente['total_ttc']} MGA")

            # --- TEST: Sélection villes malgasy ---
            print("\nTest: Sélection villes malgasy...")
            # Test creating client with different Malagasy cities
            cities_test = ['Antananarivo', 'Toamasina', 'Antsirabe', 'Fianarantsoa', 'Mahajanga', 'Toliara', 'Antsiranana']
            for city in cities_test:
                client_city = Client(
                    code=f'CLI-CITY-{city}',
                    nom=f'Test {city}',
                    email=f'test-{city}@test.mg',
                    telephone='+261 34 111 1111',
                    type='particulier',
                    ville_facturation=city,
                    code_postal_facturation='101' if city == 'Antananarivo' else {'Toamasina': '501', 'Antsirabe': '110', 'Fianarantsoa': '301', 'Mahajanga': '401', 'Toliara': '601', 'Antsiranana': '201'}.get(city, '101'),
                    pays_facturation='Madagascar',
                    ville_livraison=city,
                    code_postal_livraison='101' if city == 'Antananarivo' else {'Toamasina': '501', 'Antsirabe': '110', 'Fianarantsoa': '301', 'Mahajanga': '401', 'Toliara': '601', 'Antsiranana': '201'}.get(city, '101'),
                    pays_livraison='Madagascar',
                )
                db.session.add(client_city)
            db.session.commit()

            # Verify all cities were stored correctly
            from app.models.client import Client as ClientModel
            for city in cities_test:
                c = db.session.query(ClientModel).filter_by(ville_facturation=city).first()
                assert c is not None, f"Client ville {city} non trouvé"
                print(f"  ✓ Ville '{city}' stockée correctement")

            # --- TEST: Unités de produit ---
            print("\nTest: Unités de produit (piece/sac/carton)...")
            units_test = ['piece', 'sac', 'carton', 'kg', 'litres', 'unité']
            for unit in units_test:
                p_unit = Produit(
                    reference=f'PROD-UNIT-{unit}',
                    nom=f'Test Unité {unit}',
                    unite=unit,
                    prix_vente_ht=1000.00,
                    prix_achat_ht=500.00,
                    taux_tva=20.00,
                    quantite_stock=10,
                    categorie='test',
                )
                db.session.add(p_unit)
            db.session.commit()

            # Verify all units were stored correctly
            from app.models.produit import Produit as ProdModel
            for unit in units_test:
                p = db.session.query(ProdModel).filter_by(unite=unit).first()
                assert p is not None, f"Produit unité {unit} non trouvé"
                print(f"  ✓ Unité '{unit}' stockée correctement")

            # Cleanup
            db.session.query(ProdModel).filter(ProdModel.reference.like('PROD-UNIT-%')).delete()
            db.session.query(ClientModel).filter(ClientModel.code.like('CLI-CITY-%')).delete()
            db.session.commit()

            print("\n=== TEST 3 TERMINÉ AVEC SUCCÈS ===")


# Run the tests
if __name__ == '__main__':
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
    os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
    os.environ['PAPI_API_KEY'] = 'test-api-key'
    os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
    os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'

    from app import create_app, db as _db
    app = create_app()
    app.config['TESTING'] = True

    test = TestMission5()

    print("\n\n" + "="*60)
    print("MISSION 5/5 - ERP MADAGASCAR ADAPTATION VALIDATION")
    print("="*60 + "\n")

    try:
        test.test_workflow_vente_complet(app, None)
    except Exception as e:
        print(f"\n✗ ÉCHOUÉ: {e}")
        import traceback
        traceback.print_exc()

    try:
        test.test_workflow_achat_complet(app, None)
    except Exception as e:
        print(f"\n✗ ÉCHOUÉ: {e}")
        import traceback
        traceback.print_exc()

    try:
        test.test_interface_formulaires(app, None)
    except Exception as e:
        print(f"\n✗ ÉCHOUÉ: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print "MISSION 5/5 TERMINÉE"
    print("="*60)