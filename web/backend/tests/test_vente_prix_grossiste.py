"""Auto-sélection du prix selon le type de client et le type de vente.

Règle métier (docs/technical/metier-grossiste.md) :
- ``gros`` : grossiste -> prix_grossiste, semi_grossiste -> prix_demi_gros,
  revendeur -> prix_revendeur ; tout autre type de client -> prix_grossiste
  (repli) sauf produit sans valeur -> repli en cascade.
- ``detail`` : prix_vente_ht.
- ``type_vente`` dérivé du type de client lorsqu'il n'est pas fourni.
- Un ``prix_unitaire`` explicite non nul est toujours respecté.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import create_access_token_for_user, hash_password


@pytest.fixture
def tenant_admin(app):
    """Tenant actif + admin principal + abonnement actif + en-têtes JWT."""
    with app.app_context():
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'Prix Test {suffix}',
            slug=f'prix-{suffix}',
            statut=StatutTenant.ACTIF,
            plan='pro',
            email_contact=f'prix-{suffix}@example.com',
            telephone='+261 34 000 0000',
        )
        db.session.add(tenant)
        db.session.flush()

        user = Utilisateur(
            username=f'prix-{suffix}',
            email=f'prix-{suffix}@example.com',
            password_hash=hash_password('Prix123!'),
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
            'headers': {'Authorization': f'Bearer {token}'},
        }


def _creer_produit(client, headers, suffix, quantite_stock=100):
    response = client.post(
        '/api/v1/produits/',
        json={
            'nom': f'Riz 25kg {suffix}',
            'reference': f'RIZ-{suffix}',
            'unite': 'sac',
            'prix_achat_ht': 30000.0,
            'prix_vente_ht': 40000.0,
            'prix_grossiste': 33000.0,
            'prix_demi_gros': 35000.0,
            'prix_revendeur': 37000.0,
            'taux_tva': 10.0,
            'quantite_stock': quantite_stock,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _creer_produit_sans_prix_gros(client, headers, suffix, quantite_stock=100):
    response = client.post(
        '/api/v1/produits/',
        json={
            'nom': f'Miel 500g {suffix}',
            'reference': f'MIEL-{suffix}',
            'unite': 'pot',
            'prix_achat_ht': 5000.0,
            'prix_vente_ht': 8000.0,
            'taux_tva': 10.0,
            'quantite_stock': quantite_stock,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _creer_client(client, headers, suffix, type_client='particulier'):
    response = client.post(
        '/api/v1/clients/',
        json={
            'code': f'CLI{suffix}',
            'raison_sociale': f'Client {type_client} {suffix}',
            'email': f'client-{suffix}@example.com',
            'telephone': '+261 34 111 1111',
            'type': type_client,
            'ville_facturation': 'Antananarivo',
            'pays_facturation': 'Madagascar',
        },
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _creer_vente(client, headers, client_id, produit_id, quantite=2,
                 type_vente=None, prix_unitaire=None):
    lignes = [{'produit_id': produit_id, 'quantite': quantite, 'taux_tva': 10}]
    if prix_unitaire is not None:
        lignes[0]['prix_unitaire'] = prix_unitaire
    payload = {
        'client_id': client_id,
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
        'statut': 'en_attente',
        'mode_paiement': 'especes',
        'lignes': lignes,
    }
    if type_vente is not None:
        payload['type_vente'] = type_vente
    response = client.post('/api/v1/ventes/', json=payload, headers=headers)
    return response


def _prix_ligne(app, reference):
    with app.app_context():
        from app.models.vente import Vente
        vente = Vente.query.filter_by(reference=reference).first()
        assert vente is not None
        lignes = list(vente.lignes_vente.filter_by(is_active=True).all())
        return vente, lignes


class TestAutoPrixGrossiste:
    def test_grossiste_auto_prix_grossiste(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'grossiste')

        response = _creer_vente(client, headers, cli['id'], produit['id'])
        assert response.status_code == 201, response.get_json()
        vente, lignes = _prix_ligne(app, response.get_json()['reference'])
        assert vente.type_vente == 'gros'
        assert float(lignes[0].prix_unitaire_ht) == 33000.0

    def test_semi_grossiste_auto_prix_demi_gros(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'semi_grossiste')

        response = _creer_vente(client, headers, cli['id'], produit['id'])
        assert response.status_code == 201, response.get_json()
        vente, lignes = _prix_ligne(app, response.get_json()['reference'])
        assert vente.type_vente == 'gros'
        assert float(lignes[0].prix_unitaire_ht) == 35000.0

    def test_revendeur_auto_prix_revendeur(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'revendeur')

        response = _creer_vente(client, headers, cli['id'], produit['id'])
        assert response.status_code == 201, response.get_json()
        vente, lignes = _prix_ligne(app, response.get_json()['reference'])
        assert vente.type_vente == 'gros'
        assert float(lignes[0].prix_unitaire_ht) == 37000.0

    def test_client_detail_auto_prix_vente(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'epicerie')

        response = _creer_vente(client, headers, cli['id'], produit['id'])
        assert response.status_code == 201, response.get_json()
        vente, lignes = _prix_ligne(app, response.get_json()['reference'])
        assert vente.type_vente == 'detail'
        assert float(lignes[0].prix_unitaire_ht) == 40000.0

    def test_repli_cascade_sans_prix_gros(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit_sans_prix_gros(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'grossiste')

        response = _creer_vente(
            client, headers, cli['id'], produit['id'], type_vente='gros'
        )
        assert response.status_code == 201, response.get_json()
        vente, lignes = _prix_ligne(app, response.get_json()['reference'])
        assert vente.type_vente == 'gros'
        assert float(lignes[0].prix_unitaire_ht) == 8000.0

    def test_type_vente_explicite_gros_avec_client_detail(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'epicerie')

        response = _creer_vente(
            client, headers, cli['id'], produit['id'], type_vente='gros'
        )
        assert response.status_code == 201, response.get_json()
        vente, lignes = _prix_ligne(app, response.get_json()['reference'])
        assert vente.type_vente == 'gros'
        assert float(lignes[0].prix_unitaire_ht) == 33000.0

    def test_type_vente_invalide_400(self, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'epicerie')

        response = _creer_vente(
            client, headers, cli['id'], produit['id'], type_vente='grosse'
        )
        assert response.status_code == 400, response.get_json()

    def test_prix_explicite_respecte(self, app, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'grossiste')

        response = _creer_vente(
            client, headers, cli['id'], produit['id'], prix_unitaire=41000.0
        )
        assert response.status_code == 201, response.get_json()
        vente, lignes = _prix_ligne(app, response.get_json()['reference'])
        assert vente.type_vente == 'gros'
        assert float(lignes[0].prix_unitaire_ht) == 41000.0


class TestTypeVenteExposeApi:
    def test_type_vente_present_dans_liste_et_detail(self, client, tenant_admin):
        headers = tenant_admin['headers']
        suffix = uuid.uuid4().hex[:6]
        produit = _creer_produit(client, headers, suffix)
        cli = _creer_client(client, headers, suffix, 'grossiste')

        response = _creer_vente(client, headers, cli['id'], produit['id'])
        assert response.status_code == 201, response.get_json()
        vente_id = response.get_json()['id']

        detail = client.get(f'/api/v1/ventes/{vente_id}', headers=headers)
        assert detail.status_code == 200
        assert detail.get_json()['type_vente'] == 'gros'

        liste = client.get('/api/v1/ventes/', headers=headers)
        assert liste.status_code == 200
        item = next(
            (v for v in liste.get_json()['ventes'] if v['id'] == vente_id), None
        )
        assert item is not None
        assert item['type_vente'] == 'gros'