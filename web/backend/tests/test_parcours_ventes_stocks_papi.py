"""Parcours de bout en bout : produits → stocks → ventes → factures, puis Papi.

Ces tests vérifient par l'API HTTP que les modules opérationnels restent
réellement utilisables de bout en bout :

1. Produits & stocks : création produit, mouvements (entrée / sortie /
   inventaire), statistiques, alertes, historique des mouvements.
2. Ventes : création d'une vente avec lignes, décrément réel du stock,
   mouvement de sortie tracé, facture automatique, stats et dashboard.
3. Papi (tenant marchand) : statut sans exposer la clé, refus d'une
   configuration invalide, activation de la vitrine conditionnée à la clé.
4. Paiement Papi d'une commande vitrine : création de la commande
   publique, lien de paiement (client Papi simulé), webhook refusé si la
   signature est invalide, webhook accepté et signé (commande confirmée),
   idempotence du webhook.
5. Paiement Papi d'un abonnement (clé plateforme) : lien de paiement,
   mode de paiement invalide, paiement hors ligne (espèces).

Les clés Papi ne sont jamais interrogées en réseau : le client HTTP Papi
est systématiquement remplacé par un double de test.
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement
from app.models.produit import Produit
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import create_access_token_for_user, hash_password


TENANT_ROLES_REQUIRING_SUBSCRIPTION = (Role.ADMIN, Role.MANAGER, Role.SALES, Role.STOCK)


@pytest.fixture
def tenant_admin(app):
    """Tenant actif + admin principal + abonnement actif + en-têtes JWT."""
    with app.app_context():
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'Parcours Test {suffix}',
            slug=f'parcours-{suffix}',
            statut=StatutTenant.ACTIF,
            plan='pro',
            email_contact=f'parcours-{suffix}@example.com',
            telephone='+261 34 000 0000',
        )
        db.session.add(tenant)
        db.session.flush()

        user = Utilisateur(
            username=f'parcours-{suffix}',
            email=f'parcours-{suffix}@example.com',
            password_hash=hash_password('Parcours123!'),
            role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant.id,
            is_principal_admin=True,
        )
        db.session.add(user)
        db.session.flush()

        tenant.admin_principal_id = user.id

        abonnement = Abonnement(
            tenant_id=tenant.id,
            montant=50000.0,
            devise='MGA',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            plan='pro',
        )
        db.session.add(abonnement)
        db.session.commit()

        token = create_access_token_for_user(user, tenant)
        return {
            'tenant_id': tenant.id,
            'tenant_slug': tenant.slug,
            'user_id': user.id,
            'abonnement_id': abonnement.id,
            'headers': {'Authorization': f'Bearer {token}'},
        }


def _create_produit(client, headers, suffix, quantite_stock=10, seuil_alerte=5):
    response = client.post(
        '/api/v1/produits/',
        json={
            'nom': f'Riz 25kg {suffix}',
            'reference': f'RIZ-{suffix}',
            'unite': 'sac',
            'prix_achat_ht': 30000.0,
            'prix_vente_ht': 40000.0,
            'taux_tva': 20.0,
            'quantite_stock': quantite_stock,
            'seuil_alerte': seuil_alerte,
            'published': True,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_client(client, headers, suffix):
    response = client.post(
        '/api/v1/clients/',
        json={
            'code': f'CLI{suffix}',
            'nom': 'Rakoto',
            'prenom': 'Jean',
            'email': f'client-{suffix}@example.com',
            'telephone': '+261 34 111 1111',
            'type': 'particulier',
            'ville_facturation': 'Antananarivo',
            'pays_facturation': 'Madagascar',
        },
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


class TestProduitsEtStocks:
    """Produit → mouvements de stock → statistiques / alertes."""

    def test_parcours_produit_et_mouvements_stock(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]

        with app.app_context():
            # seuil_alerte volontairement au-dessus du stock : le produit
            # apparaît dans le flux d'alertes exposé par GET /stocks (identique
            # à GET /stocks/alerts).
            produit = _create_produit(
                client, headers, suffix, quantite_stock=10, seuil_alerte=20
            )
            produit_id = produit['id']
            assert float(produit['quantite_stock']) == 10

            # Entrée de stock : 10 -> 15
            response = client.post(
                '/api/v1/stocks/mouvements',
                json={
                    'produit_id': produit_id,
                    'quantite': 5,
                    'type_mouvement': 'entree',
                    'raison': 'Reception fournisseur',
                },
                headers=headers,
            )
            assert response.status_code == 201, response.get_json()
            assert float(response.get_json()['quantite_stock']) == 15

            # Sortie de stock : 15 -> 12
            response = client.post(
                '/api/v1/stocks/mouvements',
                json={
                    'produit_id': produit_id,
                    'quantite': 3,
                    'type_mouvement': 'sortie',
                    'raison': 'Casse atelier',
                },
                headers=headers,
            )
            assert response.status_code == 201, response.get_json()
            assert float(response.get_json()['quantite_stock']) == 12

            # Inventaire : quantité absolue
            response = client.post(
                '/api/v1/stocks/mouvements',
                json={
                    'produit_id': produit_id,
                    'quantite': 12,
                    'type_mouvement': 'inventaire',
                    'raison': 'Inventaire mensuel',
                },
                headers=headers,
            )
            assert response.status_code == 201, response.get_json()
            assert float(response.get_json()['quantite_stock']) == 12

            # Sortie impossible : stock insuffisant -> 400 explicite
            response = client.post(
                '/api/v1/stocks/mouvements',
                json={
                    'produit_id': produit_id,
                    'quantite': 999,
                    'type_mouvement': 'sortie',
                },
                headers=headers,
            )
            assert response.status_code == 400, response.get_json()

            # Champs requis
            response = client.post(
                '/api/v1/stocks/mouvements',
                json={'produit_id': produit_id},
                headers=headers,
            )
            assert response.status_code == 400

            # Lecture : détail, mouvements, stats, alertes, feed stocks
            response = client.get(f'/api/v1/stocks/{produit_id}', headers=headers)
            assert response.status_code == 200
            assert float(response.get_json()['quantite_stock']) == 12

            # POST /stocks : quantité absolue (ajustement) + validation
            response = client.post(
                '/api/v1/stocks',
                json={
                    'produit_id': produit_id,
                    'quantite': 8,
                    'type_mouvement': 'ajustement',
                    'raison': 'Ajustement apres ecart de caisse',
                },
                headers=headers,
            )
            assert response.status_code == 201, response.get_json()
            assert float(response.get_json()['quantite_stock']) == 8

            # Erreur de saisie => 400, jamais 500
            response = client.post(
                '/api/v1/stocks',
                json={
                    'produit_id': produit_id,
                    'quantite': 999,
                    'type_mouvement': 'sortie',
                },
                headers=headers,
            )
            assert response.status_code == 400, response.get_json()

            response = client.post(
                '/api/v1/stocks',
                json={
                    'produit_id': produit_id,
                    'quantite': 5,
                    'type_mouvement': 'bidon',
                },
                headers=headers,
            )
            assert response.status_code == 400, response.get_json()

            response = client.get('/api/v1/stocks/mouvements', headers=headers)
            assert response.status_code == 200
            mouvements = response.get_json()['mouvements']
            types = {m['type_mouvement'] for m in mouvements if m['produit_id'] == produit_id}
            assert {'entree', 'sortie', 'inventaire', 'ajustement'}.issubset(types), (
                f'mouvements non traces: {types}'
            )

            response = client.get('/api/v1/stocks/stats', headers=headers)
            assert response.status_code == 200
            assert 'total_produits' in response.get_json()

            response = client.get('/api/v1/stocks/', headers=headers)
            assert response.status_code == 200
            assert any(
                p['id'] == produit_id for p in response.get_json()['stocks']
            )

            response = client.get('/api/v1/stocks/alerts', headers=headers)
            assert response.status_code == 200
            assert any(
                p['id'] == produit_id for p in response.get_json()['alerts']
            ), 'produit sous le seuil absent des alertes'


class TestParcoursVente:
    """Vente avec lignes : stock, mouvements, facture, stats, dashboard."""

    def test_parcours_vente_decremente_stock_et_facture(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]

        with app.app_context():
            produit = _create_produit(client, headers, suffix, quantite_stock=10)
            produit_id = produit['id']
            client_final = _create_client(client, headers, suffix)
            client_id = client_final['id']

            # Sous-total 3 x 40 000 HT + 20 % TVA = 144 000 TTC
            response = client.post(
                '/api/v1/ventes/',
                json={
                    'client_id': client_id,
                    'mode_paiement': 'especes',
                    'lignes': [
                        {
                            'produit_id': produit_id,
                            'quantite': 3,
                            'prix_unitaire': 40000.0,
                            'taux_tva': 20.0,
                        }
                    ],
                },
                headers=headers,
            )
            assert response.status_code == 201, response.get_json()
            vente = response.get_json()
            assert Decimal(str(vente['total_ttc'])) == Decimal('144000.00')
            vente_id = vente['id']

            # Le stock a réellement été décrémenté : 10 -> 7
            response = client.get(f'/api/v1/produits/{produit_id}', headers=headers)
            assert response.status_code == 200
            assert Decimal(str(response.get_json()['quantite_stock'])) == Decimal('7.00')

            # Le mouvement de sortie est tracé et rattaché à la vente
            response = client.get('/api/v1/stocks/mouvements', headers=headers)
            sorties = [
                m for m in response.get_json()['mouvements']
                if m['produit_id'] == produit_id and m['type_mouvement'] == 'sortie'
            ]
            assert sorties, 'aucun mouvement de sortie pour la vente'
            assert sorties[0]['reference'] == vente['reference']

            # Ligne, liste et statistiques
            response = client.get(f'/api/v1/ventes/{vente_id}', headers=headers)
            assert response.status_code == 200
            detail = response.get_json()
            assert detail['reference'] == vente['reference']
            assert len(detail['lignes_vente']) == 1

            response = client.get('/api/v1/ventes/', headers=headers)
            assert response.status_code == 200
            assert any(v['id'] == vente_id for v in response.get_json()['ventes'])

            response = client.get('/api/v1/ventes/summary', headers=headers)
            assert response.status_code == 200
            assert response.get_json()['count'] >= 1

            # Facture automatique liée à la vente
            response = client.post(
                '/api/v1/ventes/',
                json={
                    'client_id': client_id,
                    'mode_paiement': 'MVOLA',
                    'facture_auto': True,
                    'lignes': [
                        {
                            'produit_id': produit_id,
                            'quantite': 1,
                            'prix_unitaire': 40000.0,
                            'taux_tva': 20.0,
                        }
                    ],
                },
                headers=headers,
            )
            assert response.status_code == 201, response.get_json()
            vente_facturee = response.get_json()

            response = client.get('/api/v1/factures/', headers=headers)
            assert response.status_code == 200
            references = {
                f['reference'] for f in response.get_json().get('factures', [])
            }
            assert f"FAC-{vente_facturee['reference']}" in references

            # Stock insuffisant : 400, aucune vente créée
            response = client.post(
                '/api/v1/ventes/',
                json={
                    'client_id': client_id,
                    'lignes': [
                        {
                            'produit_id': produit_id,
                            'quantite': 999,
                            'prix_unitaire': 40000.0,
                        }
                    ],
                },
                headers=headers,
            )
            assert response.status_code == 400
            response = client.get(f'/api/v1/produits/{produit_id}', headers=headers)
            assert Decimal(str(response.get_json()['quantite_stock'])) == Decimal('6.00')

            # Tableau de bord : les ventes remontent au dashboard
            response = client.get('/api/v1/dashboard/', headers=headers)
            assert response.status_code == 200


class TestPapiConfiguration:
    """Configuration Papi marchand + vitrine du tenant."""

    def test_configuration_papi_et_activation_vitrine(self, app, client, tenant_admin):
        headers = tenant_admin['headers']

        with app.app_context():
            response = client.get('/api/v1/me/papi-settings', headers=headers)
            assert response.status_code == 200, response.get_json()
            statut = response.get_json()
            assert statut['papi_configured'] is False
            assert statut['vitrine_active'] is False
            assert 'papi_api_key' not in statut
            assert 'papi_api_key_encrypted' not in statut

            # La vitrine ne peut pas être activée sans compte marchand Papi
            response = client.put(
                '/api/v1/me/vitrine', json={'enabled': True}, headers=headers
            )
            assert response.status_code == 400, response.get_json()

            # Environnement Papi invalide refusé
            response = client.put(
                '/api/v1/me/papi-settings',
                json={'papi_api_key': 'pk_test_parcours', 'papi_environment': 'uat'},
                headers=headers,
            )
            assert response.status_code == 400, response.get_json()

            secret = f'whsec-{uuid.uuid4().hex}'
            response = client.put(
                '/api/v1/me/papi-settings',
                json={
                    'papi_api_key': 'pk_test_parcours',
                    'papi_webhook_secret': secret,
                    'papi_environment': 'sandbox',
                },
                headers=headers,
            )
            assert response.status_code == 200, response.get_json()
            statut = response.get_json()
            assert statut['papi_configured'] is True
            assert statut['vitrine_enabled'] is False
            assert secret not in json.dumps(statut)

            # La vitrine devient activable
            response = client.put(
                '/api/v1/me/vitrine', json={'enabled': True}, headers=headers
            )
            assert response.status_code == 200, response.get_json()
            statut = response.get_json()
            assert statut['vitrine_enabled'] is True
            assert statut['vitrine_active'] is True

            # Purge : plus de clé, vitrine coupée
            response = client.put(
                '/api/v1/me/papi-settings', json={'clear': True}, headers=headers
            )
            assert response.status_code == 200, response.get_json()
            statut = response.get_json()
            assert statut['papi_configured'] is False
            assert statut['vitrine_enabled'] is False
            assert statut['vitrine_active'] is False


class _FakePapiClient:
    """Double de test du client Papi (aucun appel réseau)."""

    def __init__(self, payment_link='https://sandbox.papi.mg/pay/fake-link'):
        self.payment_link = payment_link
        self.calls = []

    def create_payment_link(self, payload):
        self.calls.append(payload)
        return {
            'paymentLink': self.payment_link,
            'paymentReference': payload['reference'],
            'notificationToken': f"nt-{uuid.uuid4().hex[:12]}",
            'amount': payload['amount'],
        }


def _activer_papi_et_vitrine(client, headers, secret):
    response = client.put(
        '/api/v1/me/papi-settings',
        json={
            'papi_api_key': 'pk_test_parcours',
            'papi_webhook_secret': secret,
            'papi_environment': 'sandbox',
        },
        headers=headers,
    )
    assert response.status_code == 200, response.get_json()
    response = client.put('/api/v1/me/vitrine', json={'enabled': True}, headers=headers)
    assert response.status_code == 200, response.get_json()


class TestPaiementPapiCommandeVitrine:
    """Commande vitrine payée via le compte marchand Papi du tenant."""

    def test_commande_vitrine_lien_paiement_et_webhook(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        slug = tenant_admin['tenant_slug']
        tenant_id = tenant_admin['tenant_id']
        public_headers = {'X-Tenant-Slug': slug}
        suffix = uuid.uuid4().hex[:6]
        secret = f'whsec-{uuid.uuid4().hex}'

        with app.app_context():
            _activer_papi_et_vitrine(client, headers, secret)
            produit = _create_produit(client, headers, suffix, quantite_stock=50)
            produit_id = produit['id']

            # Catalogue public : le produit est visible sur la vitrine
            response = client.get('/api/v1/public/produits', headers=public_headers)
            assert response.status_code == 200
            assert any(
                p['id'] == produit_id for p in response.get_json()['produits']
            ), 'produit absent du catalogue public'

            # Commande publique (panier 2 x 40 000 HT + TVA)
            idempotency_key = f'idem-{uuid.uuid4().hex}'
            commande_payload = {
                'nom_client': 'Rasoa',
                'prenom_client': 'Marie',
                'email_client': f'rasoa-{suffix}@example.com',
                'telephone_client': '+261 34 222 2222',
                'adresse_livraison': 'Lot II B 12',
                'ville_livraison': 'Antananarivo',
                'items': [{'produit_id': produit_id, 'quantite': 2}],
            }
            response = client.post(
                '/api/v1/public/commandes',
                json=commande_payload,
                headers={**public_headers, 'Idempotency-Key': idempotency_key},
            )
            assert response.status_code == 201, response.get_json()
            commande = response.get_json()
            reference = commande['reference']
            total_ttc = Decimal(str(commande['total_ttc']))
            assert total_ttc > 0

            # Double envoi de la même clé d'idempotence : pas de doublon
            response = client.post(
                '/api/v1/public/commandes',
                json=commande_payload,
                headers={**public_headers, 'Idempotency-Key': idempotency_key},
            )
            assert response.status_code in (200, 201), response.get_json()
            assert response.get_json()['reference'] == reference

            # Lien de paiement Papi (client HTTP simulé)
            fake_client = _FakePapiClient()
            with patch(
                'app.services.commande_papi_service.get_papi_client_for_tenant',
                return_value=fake_client,
            ):
                response = client.post(
                    f'/api/v1/public/commandes/{reference}/papi-payment',
                    json={'payment_method': 'MVOLA'},
                    headers=public_headers,
                )
            assert response.status_code == 200, response.get_json()
            paiement_data = response.get_json()
            assert paiement_data['payment_link'] == fake_client.payment_link

            paiement = paiement_data['payment']
            paiement_id = paiement['id']
            assert paiement['provider'] == 'papi'
            assert paiement['statut'] == StatutPaiement.EN_ATTENTE.value

            # La référence envoyée à Papi identifie le tenant (webhook multi-tenant)
            assert fake_client.calls[0]['reference'].startswith(
                f'CMD-{tenant_id}-'
            )

            external_reference = paiement['external_reference']

            # Mode de paiement non supporté -> 400 explicite
            with patch(
                'app.services.commande_papi_service.get_papi_client_for_tenant',
                return_value=fake_client,
            ):
                response = client.post(
                    f'/api/v1/public/commandes/{reference}/papi-payment',
                    json={'payment_method': 'BITCOIN'},
                    headers=public_headers,
                )
            assert response.status_code == 400

            # Statut de paiement consultable par le client
            response = client.get(
                f'/api/v1/public/commandes/{reference}/papi-status',
                headers=public_headers,
            )
            assert response.status_code == 200
            body = response.get_json()
            # Contrat minimal volontaire (pas de détail paiement exposé) :
            # cf. PublicCommandePapiStatus — 'paiement_statut' uniquement.
            assert body['reference'] == reference
            assert body['paiement_statut'] == StatutPaiement.EN_ATTENTE.value

            webhook_payload = {
                'paymentReference': external_reference,
                'notificationToken': 'nt-webhook-parcours',
                'paymentStatus': 'SUCCESS',
                'paymentMethod': 'MVOLA',
                'currency': 'MGA',
                'amount': float(total_ttc),
                'fee': 0,
                'clientName': 'Rasoa Marie',
                'description': f'Commande {reference}',
                'payerEmail': f'rasoa-{suffix}@example.com',
                'payerPhone': '+261 34 222 2222',
            }
            raw_body = json.dumps(webhook_payload)

            # Signature absente / invalide : webhook refusé
            response = client.post(
                '/api/v1/papi/webhook',
                data=raw_body,
                content_type='application/json',
            )
            assert response.status_code == 403, response.get_json()

            response = client.post(
                '/api/v1/papi/webhook',
                data=raw_body,
                content_type='application/json',
                headers={'X-Papi-Signature': 'sha256=deadbeef'},
            )
            assert response.status_code == 403, response.get_json()

            # Signature HMAC correcte (secret webhook du tenant)
            signature = hmac.new(
                secret.encode('utf-8'), raw_body.encode('utf-8'), hashlib.sha256
            ).hexdigest()
            response = client.post(
                '/api/v1/papi/webhook',
                data=raw_body,
                content_type='application/json',
                headers={'X-Papi-Signature': f'sha256={signature}'},
            )
            assert response.status_code == 200, response.get_json()
            result = response.get_json()
            assert result['status'] == 'processed'
            assert result['payment_status'] == StatutPaiement.SUCCESS.value

            # Effets métier : paiement validé, commande confirmée
            paiement_db = db.session.get(Paiement, paiement_id)
            db.session.refresh(paiement_db)
            assert paiement_db.statut == StatutPaiement.SUCCESS
            assert paiement_db.date_paiement is not None

            from app.models.commande_client import CommandeClient, StatutCommande

            commande_db = CommandeClient.query.filter_by(reference=reference).first()
            db.session.refresh(commande_db)
            assert commande_db.statut == StatutCommande.CONFIRMEE

            # Webhook rejoué : idempotent, aucun double traitement
            response = client.post(
                '/api/v1/papi/webhook',
                data=raw_body,
                content_type='application/json',
                headers={'X-Papi-Signature': f'sha256={signature}'},
            )
            assert response.status_code == 200
            assert response.get_json()['status'] == 'already_processed'

            # Listing des paiements Papi du tenant
            response = client.get('/api/v1/papi/payments', headers=headers)
            assert response.status_code == 200
            assert any(
                p['id'] == paiement_id for p in response.get_json()['payments']
            )

            response = client.get(
                f'/api/v1/papi/payments/{paiement_id}', headers=headers
            )
            assert response.status_code == 200
            assert response.get_json()['id'] == paiement_id


class TestPaiementPapiAbonnement:
    """Paiement d'abonnement via la clé Papi plateforme."""

    def test_paiement_abonnement_electronique_et_hors_ligne(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        abonnement_id = tenant_admin['abonnement_id']
        tenant_id = tenant_admin['tenant_id']

        with app.app_context():
            fake_client = _FakePapiClient(
                payment_link='https://sandbox.papi.mg/pay/abonnement'
            )
            with patch(
                'app.services.papi.payment.PapiClient', return_value=fake_client
            ):
                response = client.post(
                    f'/api/v1/papi/payments/subscription/{abonnement_id}',
                    json={'payment_method': 'MVOLA'},
                    headers=headers,
                )
            assert response.status_code == 200, response.get_json()
            data = response.get_json()
            assert data['payment_link'] == fake_client.payment_link
            paiement = data['payment']
            assert paiement['type'] == 'abonnement'
            assert paiement['provider'] == 'papi'
            assert paiement['statut'] == StatutPaiement.EN_ATTENTE.value
            assert fake_client.calls[0]['reference'].startswith(
                f'SUB-{tenant_id}-'
            )

            # Mode de paiement inconnu -> 400
            response = client.post(
                f'/api/v1/papi/payments/subscription/{abonnement_id}',
                json={'payment_method': 'BITCOIN'},
                headers=headers,
            )
            assert response.status_code == 400, response.get_json()

            # Paiement hors ligne (espèces) : aucun appel Papi
            response = client.post(
                f'/api/v1/papi/payments/subscription/{abonnement_id}',
                json={'payment_method': 'ESPECES'},
                headers=headers,
            )
            assert response.status_code == 200, response.get_json()
            paiement_hors_ligne = response.get_json()['payment']
            assert paiement_hors_ligne['provider'] == 'manuel'
            assert paiement_hors_ligne['montant']

            # L'abonnement à payer appartient bien au tenant courant
            from app.models.abonnement import Abonnement

            abonnement = db.session.get(Abonnement, abonnement_id)
            assert abonnement.tenant_id == tenant_id
