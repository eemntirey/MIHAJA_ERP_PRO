"""Generation simplifiee de facture de vente (module Documents).

La VENTE est la source de verite : les donnees du document (client,
lignes, totaux, devise MGA) sont construites automatiquement depuis
l'entite — plus besoin de JSON manuel — et les modeles systeme sont
installables a la demande (idempotent) pour les tenants anciens.
"""
from datetime import datetime

import pytest

from app import db
from app.models.client import Client
from app.models.facture import Facture
from app.models.ligne_vente import LigneVente
from app.models.modele_document import ModeleDocument
from app.models.produit import Produit
from app.models.tenant import Tenant
from app.models.vente import Vente
from app.services.document_service import (
    build_donnees_from_facture,
    build_donnees_from_vente,
    resolve_document_context,
)
from app.services.modele_seed_service import seed_modeles_systeme


def _unique(prefix):
    return f"{prefix}-{int(datetime.utcnow().timestamp() * 1000)}"


@pytest.fixture
def jeu_vente(db):
    """Tenant + client + produit + vente d'une ligne, prets a l'emploi."""
    tenant = Tenant(nom='Tenant Documents', slug=_unique('doc'))
    db.session.add(tenant)
    db.session.flush()

    client = Client(
        tenant_id=tenant.id, code=_unique('CL'), nom='Rakoto', prenom='Jean',
        email=f'{_unique("doc").lower()}@test.mg',
        adresse_facturation='Lot 12 Ampandrana', ville_facturation='Antananarivo',
    )
    db.session.add(client)
    db.session.flush()

    produit = Produit(
        tenant_id=tenant.id, reference=_unique('PR'), nom='Riz blanc 50kg',
        prix_achat_ht=80000, prix_vente_ht=136000,
    )
    db.session.add(produit)
    db.session.flush()

    vente = Vente(
        tenant_id=tenant.id, reference=_unique('VE'), client_id=client.id,
        date=datetime.utcnow(), total_ht=136000, total_ttc=149600,
        mode_paiement='especes',
    )
    db.session.add(vente)
    db.session.flush()
    db.session.add(LigneVente(
        tenant_id=tenant.id, vente_id=vente.id, produit_id=produit.id,
        quantite=1, prix_unitaire_ht=136000, taux_tva=10,
    ))
    db.session.commit()
    return {'tenant': tenant, 'client': client, 'produit': produit, 'vente': vente}


def test_donnees_auto_depuis_vente(app, jeu_vente):
    """Client, lignes et totaux sont derives de la vente, en MGA."""
    with app.app_context():
        vente = db.session.get(Vente, jeu_vente['vente'].id)
        donnees = build_donnees_from_vente(vente)

        assert donnees['client_nom'] == 'Jean Rakoto'
        assert donnees['client_adresse'] == 'Lot 12 Ampandrana'
        assert donnees['client_ville'] == 'Antananarivo'
        assert donnees['devise'] == 'MGA'
        assert donnees['reference'] == jeu_vente['vente'].reference
        assert len(donnees['items']) == 1
        ligne = donnees['items'][0]
        assert ligne['produit_nom'] == 'Riz blanc 50kg'
        assert ligne['total_ht'] == 136000.0
        assert '149 600' in donnees['total_ttc']


def test_contexte_vente_sans_facture_reference_vente(app, jeu_vente):
    """Sans facture : reference du document = reference de la vente."""
    with app.app_context():
        contexte = resolve_document_context({
            'entite_type': 'vente',
            'entite_id': jeu_vente['vente'].id,
        })
        assert contexte['type_document'] == 'facture'
        assert contexte['reference'] == jeu_vente['vente'].reference
        assert contexte['donnees']['items']


def test_contexte_facture_reprend_reference_facture(app, jeu_vente):
    """Avec facture : la reference du document est celle de la facture."""
    with app.app_context():
        facture = Facture(
            tenant_id=jeu_vente['tenant'].id,
            vente_id=jeu_vente['vente'].id,
            client_id=jeu_vente['client'].id,
            reference=f"FAC-{jeu_vente['vente'].reference}",
            total_ht=136000, total_ttc=149600, statut='non_payee',
        )
        db.session.add(facture)
        db.session.commit()

        contexte = resolve_document_context({
            'entite_type': 'vente',
            'entite_id': jeu_vente['vente'].id,
        })
        assert contexte['reference'] == f"FAC-{jeu_vente['vente'].reference}"

        donnees = build_donnees_from_facture(facture)
        assert donnees['reference'] == f"FAC-{jeu_vente['vente'].reference}"


def test_vente_introuvable_leve_erreur(app, jeu_vente):
    with app.app_context():
        with pytest.raises(ValueError):
            resolve_document_context({'entite_type': 'vente', 'entite_id': 999999999})


def test_overrides_restent_prioritaires(app, jeu_vente):
    """Les valeurs explicites de l'appelant ecrasent les valeurs deduites."""
    with app.app_context():
        vente = db.session.get(Vente, jeu_vente['vente'].id)
        donnees = build_donnees_from_vente(vente, {'client_nom': 'Boutique Soa'})
        assert donnees['client_nom'] == 'Boutique Soa'
        assert donnees['devise'] == 'MGA'


def test_seed_modeles_systeme_idempotent(app, jeu_vente):
    """Installer les modeles par defaut deux fois ne cree aucun doublon."""
    with app.app_context():
        tenant_id = jeu_vente['tenant'].id
        crees_1 = seed_modeles_systeme(tenant_id)
        db.session.commit()
        crees_2 = seed_modeles_systeme(tenant_id)
        db.session.commit()

        assert len(crees_1) >= 1
        assert crees_2 == []

        modele_facture = ModeleDocument.query.filter_by(
            tenant_id=tenant_id, type_document='facture', est_defaut=True,
            is_active=True,
        ).first()
        assert modele_facture is not None
