#!/usr/bin/env python
"""
Seeder métier réaliste pour un grossiste / distributeur malgache.

Ce script génère un jeu de données complète et culturellement crédible pour
Madagascar (monnaie : Ariary MGA) incluant :

  1. PRODUITS     — 15 articles PGC (riz, huile, sucre, farine, boissons,
                     savons, conserves) avec plusieurs conditionnements et
                     prix d'achat / vente / grossiste / démarché / détail.
  2. TIERS       — Clients variés, fournisseurs crédibles, commercial fictif.
  3. VENTES      — Commandes comptant (espèces / Mobile Money), crédit 7j/15j/
                     30j avec paiements partiels, livraisons en attente.
  4. ACHATS      — Commandes fournisseurs, réceptions, factures, paiements
                     avec gestion des dettes fournisseurs.
  5. STOCKS      — Répartis sur 2 dépôts (Dépôt principal / Magasin boutique)
                     via le champ emplacement + mouvements de stock.
  6. COMPTABIL.  — Plan comptable simplifié, écritures et trésorerie.

Toutes les données sont FICTIVES mais culturellement crédibles.
Toutes les contraintes de clé étrangère sont respectées.

Usage :
    python scripts/seed_mada_business.py
    # ou via Flask CLI :
    flask seed-data mada-business
"""
import sys
import os
from datetime import datetime, timedelta, date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.fournisseur import Fournisseur, TypeFournisseur
from app.models.client import Client, TypeClient, SecteurActivite
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.commande_fournisseur import CommandeFournisseur
from app.models.commande_achat import (
    CommandeAchat, ReceptionAchat, QualiteAchat, StatutCommandeAchat
)
from app.models.facture_fournisseur import FactureFournisseur
from app.models.ligne_achat import LigneAchat
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.auth import hash_password
from app.utils.malagasy_data import VILLES_MADAGAS, tel_madag

app = create_app()

PASSWORD = "Test1234!"
TAUX_TVA = Decimal("10.00")

DEPOT_PRINCIPAL = "Dépôt principal - Zone industrielle Andraisoro, Antananarivo"
DEPOT_BOUTIQUE = "Magasin boutique - Analakely, Antananarivo"

DEPOTS = [
    {"nom": "Dépôt principal", "emplacement": DEPOT_PRINCIPAL},
    {"nom": "Magasin boutique", "emplacement": DEPOT_BOUTIQUE},
]


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 1 — TENANT ET UTILISATEURS
# ──────────────────────────────────────────────────────────────────────────────

def seed_tenant_and_users():
    """Crée le tenant 'Distrib Moderne SARL' et ses 3 utilisateurs."""
    tenant = Tenant.query.filter_by(slug='distrib-moderne').first()
    if tenant:
        print(f"  [SKIP] Tenant 'distrib-moderne' existe déjà (id={tenant.id})")
        return tenant

    now = datetime.utcnow()

    tenant = Tenant(
        nom='Distrib Moderne SARL',
        slug='distrib-moderne',
        domaine='distrib-moderne.local',
        email_contact='contact@distrib-moderne.mg',
        telephone='+261 20 22 334 45',
        adresse='Zone industrielle Andraisoro, 27 Rue du Commerce',
        ville='Antananarivo',
        pays='Madagascar',
        code_postal='101',
        statut=StatutTenant.ACTIF,
        plan='pro',
        date_debut_essai=now - timedelta(days=30),
        date_abonnement=now,
        max_utilisateurs=20,
        max_produits=500,
        max_clients=200,
        devise='MGA',
        langue='mg',
        fuseau_horaire='Indian/Antananarivo',
    )
    db.session.add(tenant)
    db.session.flush()

    # Admin
    admin = Utilisateur(
        username='admin',
        email='admin@distrib-moderne.mg',
        password_hash=hash_password(PASSWORD),
        nom='Rasolofo',
        prenom='Miora',
        telephone='+261 34 00 111 22',
        mobile='+261 34 00 111 22',
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(admin)

    # Commercial (Jean Rakoto)
    commercial = Utilisateur(
        username='jean.rakoto',
        email='jean.rakoto@distrib-moderne.mg',
        password_hash=hash_password(PASSWORD),
        nom='Rakoto',
        prenom='Jean',
        telephone='+261 34 22 333 44',
        mobile='+261 34 22 333 44',
        role=Role.SALES,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(commercial)

    # Gestionnaire de stock
    stock_mgr = Utilisateur(
        username='andry',
        email='andry@distrib-moderne.mg',
        password_hash=hash_password(PASSWORD),
        nom='Andriamianarivo',
        prenom='Andry',
        telephone='+261 34 55 666 77',
        mobile='+261 34 55 666 77',
        role=Role.STOCK,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(stock_mgr)

    db.session.flush()

    # Abonnement
    abonnement = db.session... Abonnement(
        tenant_id=tenant.id,
        montant=Decimal('79.00'),
        devise='USD',
        date_debut=now,
        date_fin=now + timedelta(days=30),
        statut=db.session... StatutAbonnement.ACTIF,
        methode_paiement='virement',
        reference_paiement='SUB-DISTRIBMG-001',
        plan='pro',
    )
    db.session.add(abonnement)

    db.session.commit()

    users = {
        'admin': admin,
        'commercial': commercial,
        'stock': stock_mgr,
    }
    print(f"  [OK] Tenant '{tenant.nom}' créé avec 3 utilisateurs")
    return {'tenant': tenant, 'users': users}


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 2 — FOURNISSEURS
# ──────────────────────────────────────────────────────────────────────────────

FOURNISSEURS_DATA = [
    # Producteur local — riz
    {
        'code': 'FOU-MG-001', 'raison_sociale': 'Rizière Mahavelika',
        'nom_commercial': 'Riz Mahavelika',
        'type': TypeFournisseur.PRODUCTEUR_LOCAL,
        'siret': '01234567890123', 'forme_juridique': 'GIE',
        'email': 'contact@mahavelika.mg', 'telephone': '+261 262 12 345',
        'mobile': '+261 34 01 234 56',
        'adresse': 'Route de Faratsaritra, RN7', 'code_postal': '301',
        'ville': 'Fianarantsoa', 'pays': 'Madagascar',
        'contact_nom': 'Rakotondramanana', 'contact_prenom': 'Julien',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 01 234 56',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 3,
        'remise_standard': Decimal('5.00'), 'remise_volume': Decimal('8.00'),
        'note': 5,
    },
    # Producteur local — sucre
    {
        'code': 'FOU-MG-002', 'raison_sociale': 'Sucreries du Pays SARL',
        'nom_commercial': 'Sucre Pays',
        'type': TypeFournisseur.PRODUCTEUR_LOCAL,
        'siret': '02345678901234', 'forme_juridique': 'SARL',
        'email': 'vente@sucreriedupays.mg', 'telephone': '+261 236 45 678',
        'mobile': '+261 34 02 345 67',
        'adresse': 'Avenue du Sucre,quartier Lavil', 'code_postal': '601',
        'ville': 'Morondava', 'pays': 'Madagascar',
        'contact_nom': 'Ramanjary', 'contact_prenom': 'Sitraka',
        'contact_fonction': 'Commercial', 'contact_telephone': '+261 34 02 345 67',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 5,
        'remise_standard': Decimal('3.00'), 'remise_volume': Decimal('6.00'),
        'note': 4,
    },
    # Fournisseur local — huile
    {
        'code': 'FOU-MG-003', 'raison_sociale': 'Huilerie Centrale',
        'nom_commercial': 'Huile Centrale',
        'type': TypeFournisseur.FOURNISSEUR_LOCAL,
        'siret': '03456789012345', 'forme_juridique': 'SA',
        'email': 'contact@huilerie-centrale.mg', 'telephone': '+261 262 55 667',
        'mobile': '+261 34 03 456 78',
        'adresse': 'Port de Toamasina, Quai 5', 'code_postal': '501',
        'ville': 'Toamasina', 'pays': 'Madagascar',
        'contact_nom': 'Rasoamanarivo', 'contact_prenom': 'Hery',
        'contact_fonction': 'Responsable Achat', 'contact_telephone': '+261 34 03 456 78',
        'conditions_paiement': '15 jours', 'delai_livraison': 5,
        'remise_standard': Decimal('4.00'), 'remise_volume': Decimal('7.00'),
        'note': 4,
    },
    # Distributeur — boissons
    {
        'code': 'FOU-MG-004', 'raison_sociale': 'Brasserie Malagasy SA',
        'nom_commercial': 'BMA Boissons',
        'type': TypeFournisseur.FOURNISSEUR_LOCAL,
        'siret': '04567890123456', 'forme_juridique': 'SA',
        'email': 'commercial@bma.mg', 'telephone': '+261 20 22 445 56',
        'mobile': '+261 34 04 567 89',
        'adresse': '12 Avenue du 14-Juin', 'code_postal': '101',
        'ville': 'Antananarivo', 'pays': 'Madagascar',
        'contact_nom': 'Andriamatoa', 'contact_prenom': 'Lalaina',
        'contact_fonction': 'Responsable Grands Comptes',
        'contact_telephone': '+261 34 04 567 89',
        'conditions_paiement': '30 jours', 'delai_livraison': 2,
        'remise_standard': Decimal('6.00'), 'remise_volume': Decimal('10.00'),
        'note': 5,
    },
    # Importateur international
    {
        'code': 'FOU-MG-005', 'raison_sociale': 'TopAliment Import',
        'nom_commercial': 'TopAliment',
        'type': TypeFournisseur.FOURNISSEUR_INTERNATIONAL,
        'siret': '05678901234567', 'forme_juridique': 'SARL',
        'email': 'info@topaliment.mg', 'telephone': '+261 262 77 889',
        'mobile': '+261 34 05 678 90',
        'adresse': 'Immeuble Mamirok, 3ème étage', 'code_postal': '501',
        'ville': 'Toamasina', 'pays': 'Madagascar',
        'contact_nom': 'Randriamialison', 'contact_prenom': 'Piera',
        'contact_fonction': 'Manager Export',
        'contact_telephone': '+261 34 05 678 90',
        'conditions_paiement': '45 jours', 'delai_livraison': 14,
        'remise_standard': Decimal('2.00'), 'remise_volume': Decimal('5.00'),
        'note': 4,
    },
    # Fabricant — boulangisme/pâtisserie
    {
        'code': 'FOU-MG-006', 'raison_sociale': 'Boulangerie Moderne SARL',
        'nom_commercial': 'Boulangerie Moderne',
        'type': TypeFournisseur.FABRICANT,
        'siret': '06789012345678', 'forme_juridique': 'SARL',
        'email': 'vente@boulangerie-moderne.mg', 'telephone': '+261 262 33 445',
        'mobile': '+261 34 06 789 01',
        'adresse': 'Rue Pasteur Wrapsaint', 'code_postal': '101',
        'ville': 'Antsirabe', 'pays': 'Madagascar',
        'contact_nom': 'Rasoamaharo', 'contact_prenom': 'Nirina',
        'contact_fonction': 'Directrice Commerciale',
        'contact_telephone': '+261 34 06 789 01',
        'conditions_paiement': '30 jours', 'delai_livraison': 7,
        'remise_standard': Decimal('5.00'), 'remise_volume': Decimal('8.00'),
        'note': 5,
    },
    # Fabricant — savonnerie
    {
        'code': 'FOU-MG-007', 'raison_sociale': 'Savonnerie du Lac SARL',
        'nom_commercial': 'Savon du Lac',
        'type': TypeFournisseur.FABRICANT,
        'siret': '07890123456789', 'forme_juridique': 'SARL',
        'email': 'contact@savondulac.mg', 'telephone': '+261 236 22 112',
        'mobile': '+261 34 07 890 12',
        'adresse': 'Route de Mahajanga, PK 8', 'code_postal': '101',
        'ville': 'Mahajanga', 'pays': 'Madagascar',
        'contact_nom': 'Ramoson', 'contact_prenom': 'Brigitte',
        'contact_fonction': 'Responsable Technique',
        'contact_telephone': '+261 34 07 890 12',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 5,
        'remise_standard': Decimal('4.00'), 'remise_volume': Decimal('7.00'),
        'note': 4,
    },
    # Fabricant — conserves
    {
        'code': 'FOU-MG-008', 'raison_sociale': 'Conserves de Madagascar SA',
        'nom_commercial': 'Conserves MG',
        'type': TypeFournisseur.FABRICANT,
        'siret': '08901234567890', 'forme_juridique': 'SA',
        'email': 'commercial@conserves-mg.mg', 'telephone': '+261 262 44 556',
        'mobile': '+261 34 08 901 23',
        'adresse': 'Zone Industrielle Togo Afo', 'code_postal': '301',
        'ville': 'Fianarantsoa', 'pays': 'Madagascar',
        'contact_nom': 'Randriamandimby', 'contact_prenom': 'Sylvain',
        'contact_fonction': 'Gérant',
        'contact_telephone': '+261 34 08 901 23',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 4,
        'remise_standard': Decimal('5.00'), 'remise_volume': Decimal('9.00'),
        'note': 5,
    },
]


def seed_fournisseurs(tenant_id, admin_id):
    fournisseurs = []
    for data in FOURNISSEURS_DATA:
        existing = Fournisseur.query.filter_by(code=data['code'], tenant_id=tenant_id).first()
        if existing:
            fournisseurs.append(existing)
            continue
        f = Fournisseur(**data)
        f.tenant_id = tenant_id
        f.created_by = admin_id
        f.updated_by = admin_id
        db.session.add(f)
        fournisseurs.append(f)
    db.session.flush()
    print(f"  [OK] {len(fournisseurs)} fournisseurs créés")
    return fournisseurs


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 3 — CLIENTS
# ──────────────────────────────────────────────────────────────────────────────

CLIENTS_DATA = [
    {
        'code': 'CLI-MG-001', 'raison_sociale': 'Boutique Soa',
        'type': TypeClient.BOUTIQUE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@boutiquesoa.mg', 'telephone': '+261 34 11 222 33',
        'mobile': '+261 34 11 222 33',
        'adresse_facturation': '27 Avenue de l\'Indépendance',
        'code_postal_facturation': '101', 'ville_facturation': 'Antananarivo',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '27 Avenue de l\'Indépendance',
        'code_postal_livraison': '101', 'ville_livraison': 'Antananarivo',
        'contact_nom': 'Ramanantoandro', 'contact_prenom': 'Mireille',
        'contact_fonction': 'Gérante', 'contact_telephone': '+261 34 11 222 33',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('2000000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('2.00'),
        'note': 5,
    },
    {
        'code': 'CLI-MG-002', 'raison_sociale': 'Épicerie Fitiavana',
        'type': TypeClient.EPICERIE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@epiceriefitiavana.mg', 'telephone': '+261 34 22 333 44',
        'mobile': '+261 34 22 333 44',
        'adresse_facturation': '15 Rue du Marché',
        'code_postal_facturation': '110', 'ville_facturation': 'Antsirabe',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '15 Rue du Marché',
        'code_postal_livraison': '110', 'ville_livraison': 'Antsirabe',
        'contact_nom': 'Rabet', 'contact_prenom': 'Pascal',
        'contact_fonction': 'Propriétaire', 'contact_telephone': '+261 34 22 333 44',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('800000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('3.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-003', 'raison_sociale': 'Shop Mada',
        'type': TypeClient.SEMI_GROSSISTE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@shopmada.mg', 'telephone': '+261 34 33 444 55',
        'mobile': '+261 34 33 444 55',
        'adresse_facturation': '12 Avenue du 14-Juin',
        'code_postal_facturation': '201', 'ville_facturation': 'Antsiranana',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '12 Avenue du 14-Juin',
        'code_postal_livraison': '201', 'ville_livraison': 'Antsiranana',
        'contact_nom': 'Andriamihaja', 'contact_prenom': 'Bruno',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 33 444 55',
        'conditions_paiement': '7 jours', 'plafond_credit': Decimal('1500000.00'),
        'echeance_credit': 7, 'remise_standard': Decimal('4.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-004', 'raison_sociale': 'Supermarché Mahajy',
        'nom': 'Mahajanarivo', 'prenom': 'Solo',
        'type': TypeClient.SUPERMARCHE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@supermarchemajy.mg', 'telephone': '+261 34 44 555 66',
        'mobile': '+261 34 44 555 66',
        'adresse_facturation': '1 Rue du Marché Central',
        'code_postal_facturation': '401', 'ville_facturation': 'Mahajanga',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '1 Rue du Marché Central',
        'code_postal_livraison': '401', 'ville_livraison': 'Mahajanga',
        'contact_nom': 'Mahajanarivo', 'contact_prenom': 'Solo',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 44 555 66',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('3000000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('3.00'),
        'note': 5,
    },
    {
        'code': 'CLI-MG-005', 'raison_sociale': 'Épicerie Maman Aina',
        'type': TypeClient.EPICERIE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'mamanaina@epicerie.mg', 'telephone': '+261 34 55 666 77',
        'mobile': '+261 34 55 666 77',
        'adresse_facturation': '45 Avenue de la Côte',
        'code_postal_facturation': '501', 'ville_facturation': 'Toamasina',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '45 Avenue de la Côte',
        'code_postal_livraison': '501', 'ville_livraison': 'Toamasina',
        'contact_nom': 'Rasoamanarivo', 'contact_prenom': 'Aïna',
        'contact_fonction': 'Propriétaire', 'contact_telephone': '+261 34 55 666 77',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('500000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('2.00'),
        'note': 3,
    },
    {
        'code': 'CLI-MG-006', 'raison_sociale': 'Boutique Mama Dina',
        'type': TypeClient.BOUTIQUE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@mamadina.mg', 'telephone': '+261 34 66 777 88',
        'mobile': '+261 34 66 777 88',
        'adresse_facturation': '8 Rue Colbert',
        'code_postal_facturation': '110', 'ville_facturation': 'Antsirabe',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '8 Rue Colbert',
        'code_postal_livraison': '110', 'ville_livraison': 'Antsirabe',
        'contact_nom': 'Andriatra', 'contact_prenom': 'Dina',
        'contact_fonction': 'Gérante', 'contact_telephone': '+261 34 66 777 88',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('600000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('2.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-007', 'raison_sociale': 'Dépôt de Quartier',
        'type': TypeClient.SEMI_GROSSISTE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@depotquartier.mg', 'telephone': '+261 34 77 888 99',
        'mobile': '+261 34 77 888 99',
        'adresse_facturation': '10 Avenue de la Liberté',
        'code_postal_facturation': '601', 'ville_facturation': 'Toliara',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '10 Avenue de la Liberté',
        'code_postal_livraison': '601', 'ville_livraison': 'Toliara',
        'contact_nom': 'Rasolofonirina', 'contact_prenom': 'Heri',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 77 888 99',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('1200000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('4.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-008', 'raison_sociale': 'Restaurant Le Zebu',
        'type': TypeClient.RESTAURANT, 'secteur': SecteurActivite.SERVICES,
        'email': 'contact@restaurantlezebu.mg', 'telephone': '+261 34 88 999 00',
        'mobile': '+261 34 88 999 00',
        'adresse_facturation': '22 Boulevard de l\'Indépendance',
        'code_postal_facturation': '101', 'ville_facturation': 'Antananarivo',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '22 Boulevard de l\'Indépendance',
        'code_postal_livraison': '101', 'ville_livraison': 'Antananarivo',
        'contact_nom': 'Rakotondramanana', 'contact_prenom': 'David',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 88 999 00',
        'conditions_paiement': '7 jours', 'plafond_credit': Decimal('300000.00'),
        'echeance_credit': 7, 'remise_standard': Decimal('5.00'),
        'note': 5,
    },
    {
        'code': 'CLI-MG-009', 'raison_sociale': 'Hôtel Coco Beach',
        'type': TypeClient.HOTEL, 'secteur': SecteurActivite.SERVICES,
        'email': 'reservations@cocobeach.mg', 'telephone': '+261 34 99 000 11',
        'mobile': '+261 34 99 000 11',
        'adresse_facturation': '10 Avenue des Baigneurs',
        'code_postal_facturation': '501', 'ville_facturation': 'Toamasina',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '10 Avenue des Baigneurs',
        'code_postal_livraison': '501', 'ville_livraison': 'Toamasina',
        'contact_nom': 'Andriamiarar', 'contact_prenom': 'Sabrina',
        'contact_fonction': 'Directrice', 'contact_telephone': '+261 34 99 000 11',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('1000000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('3.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-010', 'raison_sociale': 'Centrale des Épiceries',
        'type': TypeClient.GROSSISTE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@centrale-epicerie.mg', 'telephone': '+261 34 10 111 22',
        'mobile': '+261 34 10 111 22',
        'adresse_facturation': 'Immeuble Central, 4ème étage',
        'code_postal_facturation': '101', 'ville_facturation': 'Antananarivo',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': 'Immeuble Central, 4ème étage',
        'code_postal_livraison': '101', 'ville_livraison': 'Antananarivo',
        'contact_nom': 'Ramanantsoa', 'contact_prenom': 'Viviane',
        'contact_fonction': 'Responsable Achats',
        'contact_telephone': '+261 34 10 111 22',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('5000000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('5.00'),
        'note': 5,
    },
]


def seed_clients(tenant_id, commercial_id, admin_id):
    clients = []
    for data in CLIENTS_DATA:
        existing = Client.query.filter_by(code=data['code'], tenant_id=tenant_id).first()
        if existing:
            clients.append(existing)
            continue
        data['tenant_id'] = tenant_id
        data['commercial_id'] = commercial_id
        data['created_by'] = admin_id
        data['updated_by'] = admin_id
        c = Client(**data)
        db.session.add(c)
        clients.append(c)
    db.session.flush()
    print(f"  [OK] {len(clients)} clients créés")
    return clients


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 4 — PRODUITS
# ──────────────────────────────────────────────────────────────────────────────

# 15 produits PGC réalistes avec plusieurs conditionnements.
# Les prix sont en Ariary (MGA). Le taux de TVA est 10 % (TNV Madagascar).
PRODUITS_DATA = [
    # ─── RIZ ────────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-001', 'code_barre': '6001000010018', 'code_interne': 'MG-RIZ-001',
        'nom': 'Riz blanc Makalioka (sac 50 kg)',
        'description_courte': 'Riz de première qualité, grain long, conditionné en sac de 50 kg',
        'description_longue': 'Riz blanc Makalioka provenance du Lac Alaotra, grain long, idéal pour la consommation quotidienne et la restauration collective.',
        'categorie': 'Riz & Céréales', 'sous_categorie': 'Riz blanc', 'famille': 'Céréales',
        'marque': 'Lac Alaotra', 'modele': 'Makalioka', 'unite': 'sac',
        'prix_achat_ht': Decimal('350000.00'), 'prix_vente_ht': Decimal('450000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('200'), 'seuil_alerte': Decimal('30'), 'seuil_critique': Decimal('10'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A1', 'etagere': '03',
        'poids': Decimal('50.00'), 'longueur': Decimal('80'), 'largeur': Decimal('60'), 'hauteur': Decimal('20'),
        'marque': 'Lac Alaotra',
        'prix_grossiste': Decimal('430000.00'), 'prix_demi_gros': Decimal('440000.00'), 'prix_revendeur': Decimal('448000.00'),
        'tags': 'riz,alimentation,grande-consommation',
        'fournisseur_code': 'FOU-MG-001',
    },
    {
        'reference': 'DISTRI-MG-002', 'code_barre': '6001000010025', 'code_interne': 'MG-RIZ-002',
        'nom': 'Riz brisé (sac 25 kg)',
        'description_courte': 'Riz brisé pour la restauration collective et les pâtisseries',
        'categorie': 'Riz & Céréales', 'sous_categorie': 'Riz brisé', 'famille': 'Céréales',
        'marque': 'RSI Mada', 'modele': 'Brisé', 'unite': 'sac',
        'prix_achat_ht': Decimal('175000.00'), 'prix_vente_ht': Decimal('230000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('350'), 'seuil_alerte': Decimal('40'), 'seuil_critique': Decimal('15'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A1', 'etagere': '04',
        'poids': Decimal('25.00'), 'longueur': Decimal('70'), 'largeur': Decimal('50'), 'hauteur': Decimal('15'),
        'marque': 'RSI Mada',
        'prix_grossiste': Decimal('215000.00'), 'prix_demi_gros': Decimal('222000.00'), 'prix_revendeur': Decimal('226000.00'),
        'tags': 'riz,restauration,cereales',
        'fournisseur_code': 'FOU-MG-001',
    },
    # ─── HUILE ────────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-003', 'code_barre': '6001000020019', 'code_interne': 'MG-HUI-001',
        'nom': 'Huile de tournesol (bidon 5 L)',
        'description_courte': 'Huile végétale de tournesol, bidon de 5 L pour les boucheries et le détail',
        'categorie': 'Huiles & Grains', 'sous_categorie': 'Huile alimentaire', 'famille': 'Huiles',
        'marque': 'Hasi', 'modele': 'Classic', 'unite': 'bidon',
        'prix_achat_ht': Decimal('85000.00'), 'prix_vente_ht': Decimal('110000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('150'), 'seuil_alerte': Decimal('25'), 'seuil_critique': Decimal('10'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B2', 'etagere': '01',
        'poids': Decimal('5.50'), 'longueur': Decimal('25'), 'largeur': Decimal('20'), 'hauteur': Decimal('30'),
        'prix_grossiste': Decimal('103000.00'), 'prix_demi_gros': Decimal('108000.00'), 'prix_revendeur': Decimal('110000.00'),
        'tags': 'huile,cuisine,vegetale',
        'fournisseur_code': 'FOU-MG-003',
    },
    {
        'reference': 'DISTRI-MG-004', 'code_barre': '6001000020026', 'code_interne': 'MG-HUI-002',
        'nom': 'Huile alimentaire (bouteille 1 L)',
        'description_courte': 'Huile de cuisine premium en bouteille de 1 L, très demandée en détail',
        'categorie': 'Huiles & Grains', 'sous_categorie': 'Huile alimentaire', 'famille': 'Huiles',
        'marque': 'Loulou', 'modele': 'Premium', 'unite': 'bouteille',
        'prix_achat_ht': Decimal('2500.00'), 'prix_vente_ht': Decimal('3200.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('2000'), 'seuil_alerte': Decimal('300'), 'seuil_critique': Decimal('100'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C3', 'etagere': '02',
        'poids': Decimal('1.00'), 'longueur': Decimal('7'), 'largeur': Decimal('7'), 'hauteur': Decimal('23'),
        'prix_grossiste': Decimal('2900.00'), 'prix_demi_gros': Decimal('3050.00'), 'prix_revendeur': Decimal('3150.00'),
        'tags': 'huile,cuisine,1l,bouteille',
        'fournisseur_code': 'FOU-MG-003',
    },
    # ─── SUCRE ───────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-005', 'code_barre': '6001000030012', 'code_interne': 'MG-SUC-001',
        'nom': 'Sucre blanc (sac 25 kg)',
        'description_courte': 'Sucre de canne blanc raffiné, sac de 25 kg pour les professionnels',
        'categorie': 'Couleurs & Sucreries', 'sous_categorie': 'Sucre', 'famille': 'Sucreries',
        'marque': 'Compania', 'modele': 'Blanc', 'unite': 'sac',
        'prix_achat_ht': Decimal('95000.00'), 'prix_vente_ht': Decimal('125000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('180'), 'seuil_alerte': Decimal('30'), 'seuil_critique': Decimal('12'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A2', 'etagere': '02',
        'poids': Decimal('25.00'), 'longueur': Decimal('70'), 'largeur': Decimal('50'), 'hauteur': Decimal('15'),
        'prix_grossiste': Decimal('115000.00'), 'prix_demi_gros': Decimal('120000.00'), 'prix_revendeur': Decimal('122000.00'),
        'tags': 'sucre,cantonnade,restaurant,pâtisserie',
        'fournisseur_code': 'FOU-MG-002',
    },
    {
        'reference': 'DISTRI-MG-006', 'code_barre': '6001000030029', 'code_interne': 'MG-SUC-002',
        'nom': 'Sucre raffiné (paquet 1 kg)',
        'description_courte': 'Sucre raffiné en paquet de 1 kg pour le détail et les particuliers',
        'categorie': 'Couleurs & Sucreries', 'sous_categorie': 'Sucre', 'famille': 'Sucreries',
        'marque': 'Compania', 'modele': 'Raffiné', 'unite': 'sachet',
        'prix_achat_ht': Decimal('3500.00'), 'prix_vente_ht': Decimal('4800.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('9000'), 'seuil_alerte': Decimal('1200'), 'seuil_critique': Decimal('500'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C1', 'etagere': '05',
        'poids': Decimal('1.00'), 'longueur': Decimal('12'), 'largeur': Decimal('12'), 'hauteur': Decimal('8'),
        'prix_grossiste': Decimal('4400.00'), 'prix_demi_gros': Decimal('4600.00'), 'prix_revendeur': Decimal('4700.00'),
        'tags': 'sucre,detail,particulier,1kg',
        'fournisseur_code': 'FOU-MG-002',
    },
    # ─── FARINE ───────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-007', 'code_barre': '6001000040015', 'code_interne': 'MG-FAR-001',
        'nom': 'Farine de blé (sac 50 kg)',
        'description_courte': 'Farine de blé T45 pour boulangeries et pâtisseries',
        'categorie': 'Farines & Pâtes', 'sous_categorie': 'Farine de blé', 'famille': 'Céréales',
        'marque': 'Aux Mille', 'modele': 'T45', 'unite': 'sac',
        'prix_achat_ht': Decimal('135000.00'), 'prix_vente_ht': Decimal('180000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('120'), 'seuil_alerte': Decimal('25'), 'seuil_critique': Decimal('10'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A3', 'etagere': '01',
        'poids': Decimal('50.00'), 'longueur': Decimal('75'), 'largeur': Decimal('55'), 'hauteur': Decimal('15'),
        'prix_grossiste': Decimal('168000.00'), 'prix_demi_gros': Decimal('174000.00'), 'prix_revendeur': Decimal('177000.00'),
        'tags': 'farine,blé,boulangerie,pâtisserie',
        'fournisseur_code': 'FOU-MG-006',
    },
    {
        'reference': 'DISTRI-MG-008', 'code_barre': '6001000040022', 'code_interne': 'MG-FAR-002',
        'nom': 'Farine de maïs (sac 25 kg)',
        'description_courte': 'Farine de maïs pour les fritures et les pâtes traditionnelles',
        'categorie': 'Farines & Pâtes', 'sous_categorie': 'Farine de maïs', 'famille': 'Céréales',
        'marque': 'Aux Mille', 'modele': 'Maïs', 'unite': 'sac',
        'prix_achat_ht': Decimal('65000.00'), 'prix_vente_ht': Decimal('85000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('90'), 'seuil_alerte': Decimal('20'), 'seuil_critique': Decimal('8'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A3', 'etagere': '02',
        'poids': Decimal('25.00'), 'longueur': Decimal('65'), 'largeur': Decimal('45'), 'hauteur': Decimal('12'),
        'prix_grossiste': Decimal('80000.00'), 'prix_demi_gros': Decimal('82500.00'), 'prix_revendeur': Decimal('83500.00'),
        'tags': 'farine,maïs,friture,tradition',
        'fournisseur_code': 'FOU-MG-006',
    },
    # ─── EAUX & BOISSONS ───────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-009', 'code_barre': '6001000050018', 'code_interne': 'MG-EAS-001',
        'nom': 'Eau minérale (pack 6 x 1,5 L)',
        'description_courte': 'Pack de 6 bouteilles d\'eau minérale de source, 1,5 L chacune',
        'categorie': 'Eaux & Boissons', 'sous_categorie': 'Eaux minérales', 'famille': 'Boissons',
        'marque': 'Source Tiaca', 'modele': 'Naturelle', 'unite': 'pack',
        'prix_achat_ht': Decimal('7800.00'), 'prix_vente_ht': Decimal('10500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('800'), 'seuil_alerte': Decimal('150'), 'seuil_critique': Decimal('70'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C4', 'etagere': '03',
        'poids': Decimal('9.00'), 'longueur': Decimal('30'), 'largeur': Decimal('20'), 'hauteur': Decimal('22'),
        'prix_grossiste': Decimal('9800.00'), 'prix_demi_gros': Decimal('10100.00'), 'prix_revendeur': Decimal('10300.00'),
        'tags': 'eau,minérale,boisson,source',
        'fournisseur_code': 'FOU-MG-004',
    },
    {
        'reference': 'DISTRI-MG-010', 'code_barre': '6001000050025', 'code_interne': 'MG-BOI-001',
        'nom': 'Boisson gazeuse locale (pack 12 x 1,5 L)',
        'description_courte': 'Soda orange local, pack de 12 bouteilles de 1,5 L',
        'categorie': 'Eaux & Boissons', 'sous_categorie': 'Boissons gazeuses', 'famille': 'Boissons',
        'marque': 'VCore', 'modele': 'Orange', 'unite': 'pack',
        'prix_achat_ht': Decimal('14500.00'), 'prix_vente_ht': Decimal('19500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('600'), 'seuil_alerte': Decimal('100'), 'seuil_critique': Decimal('50'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B1', 'etagere': '04',
        'poids': Decimal('18.00'), 'longueur': Decimal('35'), 'largeur': Decimal('25'), 'hauteur': Decimal('24'),
        'prix_grossiste': Decimal('17200.00'), 'prix_demi_gros': Decimal('18200.00'), 'prix_revendeur': Decimal('18900.00'),
        'tags': 'boisson,gazéuse,soda,orange,1,5l',
        'fournisseur_code': 'FOU-MG-004',
    },
    {
        'reference': 'DISTRI-MG-011', 'code_barre': '6001000050032', 'code_interne': 'MG-EAS-002',
        'nom': 'Eau en bouteille (1,5 L)',
        'description_courte': 'Eau minérale en bouteille individuelle de 1,5 L',
        'categorie': 'Eaux & Boissons', 'sous_categorie': 'Eaux minérales', 'famille': 'Boissons',
        'marque': 'Source Tiaca', 'modele': 'Indiv', 'unite': 'bouteille',
        'prix_achat_ht': Decimal('1200.00'), 'prix_vente_ht': Decimal('1800.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('3000'), 'seuil_alerte': Decimal('500'), 'seuil_critique': Decimal('200'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C4', 'etagere': '01',
        'poids': Decimal('1.50'), 'longueur': Decimal('7'), 'largeur': Decimal('7'), 'hauteur': Decimal('23'),
        'prix_grossiste': Decimal('1550.00'), 'prix_demi_gros': Decimal('1650.00'), 'prix_revendeur': Decimal('1720.00'),
        'tags': 'eau,minérale,bouteille,1.5l,detail',
        'fournisseur_code': 'FOU-MG-004',
    },
    # ─── BISCUITS ─────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-012', 'code_barre': '6001000060011', 'code_interne': 'MG-BIS-001',
        'nom': 'Biscuit Sucré (carton 250 g x 12)',
        'description_courte': 'Biscuits sucrés au beurre, 12 paquets de 250 g',
        'categorie': 'Biscuits & Gâteaux', 'sous_categorie': 'Biscuits', 'famille': 'Épicerie sèche',
        'marque': 'Vitel', 'modele': 'Sucré', 'unite': 'paquet',
        'prix_achat_ht': Decimal('15000.00'), 'prix_vente_ht': Decimal('21000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('600'), 'seuil_alerte': Decimal('90'), 'seuil_critique': Decimal('40'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B3', 'etagere': '02',
        'poids': Decimal('3.00'), 'longueur': Decimal('25'), 'largeur': Decimal('20'), 'hauteur': Decimal('15'),
        'prix_grossiste': Decimal('19000.00'), 'prix_demi_gros': Decimal('20000.00'), 'prix_revendeur': Decimal('20500.00'),
        'tags': 'biscuit,goûter,snack,sucré',
        'fournisseur_code': 'FOU-MG-006',
    },
    # ─── SAVONS ───────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-013', 'code_barre': '6001000070010', 'code_interne': 'MG-SAV-001',
        'nom': 'Savon de toilette (carton 72)',
        'description_courte': 'Carton de 72 savons de toilette parfumés, 100 g chacun',
        'categorie': 'Hygiène', 'sous_categorie': 'Savons', 'famille': 'Produits d\'hygiène',
        'marque': 'Ny Hary', 'modele': 'Parfum', 'unite': 'carton',
        'prix_achat_ht': Decimal('65000.00'), 'prix_vente_ht': Decimal('85000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('80'), 'seuil_alerte': Decimal('15'), 'seuil_critique': Decimal('8'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A4', 'etagere': '01',
        'poids': Decimal('7.20'), 'longueur': Decimal('40'), 'largeur': Decimal('30'), 'hauteur': Decimal('25'),
        'prix_grossiste': Decimal('78000.00'), 'prix_demi_gros': Decimal('81000.00'), 'prix_revendeur': Decimal('83000.00'),
        'tags': 'savon,hygiène,toilette,barre',
        'fournisseur_code': 'FOU-MG-007',
    },
    {
        'reference': 'DISTRI-MG-014', 'code_barre': '6001000070027', 'code_interne': 'MG-SAV-002',
        'nom': 'Savon liquide (bidon 5 L)',
        'description_courte': 'Savon liquide concentré pour usages ménagers et industriels, bidon de 5 L',
        'categorie': 'Hygiène', 'sous_categorie': 'Produits ménagers', 'famille': 'Produits d\'hygiène',
        'marque': 'Ny Hary', 'modele': 'Liquide', 'unite': 'bidon',
        'prix_achat_ht': Decimal('75000.00'), 'prix_vente_ht': Decimal('95000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('60'), 'seuil_alerte': Decimal('12'), 'seuil_critique': Decimal('5'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C2', 'etagere': '04',
        'poids': Decimal('5.50'), 'longueur': Decimal('25'), 'largeur': Decimal('20'), 'hauteur': Decimal('30'),
        'prix_grossiste': Decimal('88000.00'), 'prix_demi_gros': Decimal('91000.00'), 'prix_revendeur': Decimal('93000.00'),
        'tags': 'savon,liquide,ménager,hygiène',
        'fournisseur_code': 'FOU-MG-007',
    },
    # ─── CONSERVES ────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-015', 'code_barre': '6001000080013', 'code_interne': 'MG-CON-001',
        'nom': 'Conserves de sardine (pack 12)',
        'description_courte': 'Conserves de sardines en boîte de 12, provenant de la pêche locale',
        'categorie': 'Conserves & Produits transforms', 'sous_categorie': 'Poissons conservés', 'famille': 'Conserves',
        'marque': 'Pêche MG', 'modele': 'Sardine', 'unite': 'pack',
        'prix_achat_ht': Decimal('12500.00'), 'prix_vente_ht': Decimal('17500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('400'), 'seuil_alerte': Decimal('80'), 'seuil_critique': Decimal('30'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B4', 'etagere': '03',
        'poids': Decimal('5.40'), 'longueur': Decimal('28'), 'largeur': Decimal('20'), 'hauteur': Decimal('12'),
        'prix_grossiste': Decimal('16000.00'), 'prix_demi_gros': Decimal('16800.00'), 'prix_revendeur': Decimal('17200.00'),
        'tags': 'conserves,sardine,poisson,local',
        'fournisseur_code': 'FOU-MG-008',
    },
    {
        'reference': 'DISTRI-MG-016', 'code_barre': '6001000080020', 'code_interne': 'MG-CON-002',
        'nom': 'Conserves de haricots rouges (pack 12)',
        'description_courte': 'Conserves de haricots rouges malgaches, pack de 12 boîtes',
        'categorie': 'Conserves & Produits transforms', 'sous_categorie': 'Légumes conservés', 'famille': 'Conserves',
        'marque': 'Pêche MG', 'modele': 'Haricots', 'unite': 'pack',
        'prix_achat_ht': Decimal('9800.00'), 'prix_vente_ht': Decimal('13500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('300'), 'seuil_alerte': Decimal('60'), 'seuil_critique': Decimal('25'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B4', 'etagere': '04',
        'poids': Decimal('5.00'), 'longueur': Decimal('28'), 'largeur': Decimal('20'), 'hauteur': Decimal('12'),
        'prix_grossiste': Decimal('12200.00'), 'prix_demi_gros': Decimal('12900.00'), 'prix_revendeur': Decimal('13200.00'),
        'tags': 'conserves,haricots,légumes,local',
        'fournisseur_code': 'FOU-MG-008',
    },
]


def seed_produits(tenant_id, fournisseurs, admin_id):
    fournisseur_map = {f.code: f for f in fournisseurs}
    produits = []
    for data in PRODUITS_DATA:
        existing = Produit.query.filter_by(reference=data['reference'], tenant_id=tenant_id).first()
        if existing:
            produits.append(existing)
            continue
        fou_code = data.pop('fournisseur_code')
        fournisseur = fournisseur_map.get(fou_code)
        if fournisseur:
            data['fournisseur_id'] = fournisseur.id
        data['tenant_id'] = tenant_id
        data['created_by'] = admin_id
        data['updated_by'] = admin_id
        data['prix_achat_ttc'] = data['prix_achat_ht'] * (1 + TAUX_TVA / 100)
        data['prix_vente_ttc'] = data['prix_vente_ht'] * (1 + TAUX_TVA / 100)
        data['marge_standard'] = Decimal('0')
        if data['prix_achat_ht'] > 0:
            data['marge_standard'] = (
                (data['prix_vente_ht'] - data['prix_achat_ht']) / data['prix_achat_ht']
            ) * 100
        p = Produit(**data)
        db.session.add(p)
        produits.append(p)
    db.session.flush()
    print(f"  [OK] {len(produits)} produits créés")
    return produits


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 5 — STOCKS INITIAUX (mouvements + répartition dépôts)
# ──────────────────────────────────────────────────────────────────────────────

def seed_stocks_initiaux(produits, tenant_id, stock_mgr_id):
    """Crée les mouvements d'entrée initiale et répartit les stocks sur 2 dépôts."""
    mouvements = []
    now = datetime.utcnow()
    # Date d'initialisation : 30 jours avant aujourd'hui
    date_init = now - timedelta(days=30)

    for p in produits:
        # Mouvement d'entrée initial
        mouvement = MouvementStock(
            produit_id=p.id,
            tenant_id=tenant_id,
            type_mouvement=TypeMouvement.ENTREE,
            quantite=p.quantite_stock,
            stock_avant=Decimal('0'),
            stock_apres=p.quantite_stock,
            raison=f"Réception initiale — {p.emplacement.split(' - ')[0]}",
            reference=f"BL-INIT-{p.reference}",
            created_by=stock_mgr_id,
            created_at=date_init,
        )
        db.session.add(mouvement)
        mouvements.append(mouvement)

    db.session.flush()

    # Quelques transferts entre dépôts pour illustrer la logistics
    transferts = [
        ('DISTRI-MG-006', 20, DEPOT_BOUTIQUE),   # 20 sacs de farine vers le magasin
        ('DISTRI-MG-011', 500, DEPOT_PRINCIPAL),  # 500 bouteilles d'eau retour au dépôt
        ('DISTRI-MG-004', 300, DEPOT_BOUTIQUE),   # 300 bouteilles d'huile vers boutique
    ]
    for ref, qty, emplacement in transferts:
        p = next((x for x in produits if x.reference == ref), None)
        if not p:
            continue
        before = p.quantite_stock
        after = before - qty if emplacement == DEPOT_PRINCIPAL else before  # stock total unchanged
        mouvement = MouvementStock(
            produit_id=p.id,
            tenant_id=tenant_id,
            type_mouvement=TypeMouvement.TRANSFERT,
            quantite=qty,
            stock_avant=before,
            stock_apres=after if emplacement == DEPOT_PRINCIPAL else before,
            raison=f"Transfert vers {emplacement.split(' - ')[0]}",
            reference=f"TF-{p.reference}-01",
            created_by=stock_mgr_id,
            created_at=date_init + timedelta(days=5),
        )
        db.session.add(mouvement)
        mouvements.append(mouvement)

    db.session.commit()
    depot_principal = sum(1 for p in produits if DEPOT_PRINCIPAL in p.emplacement)
    depot_boutique = sum(1 for p in produits if DEPOT_BOUTIQUE in p.emplacement)
    print(f"  [OK] {len(mouvements)} mouvements de stock créés ({depot_principal} produits au dépôt principal, {depot_boutique} au magasin boutique)")
    return mouvements


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 6 — VENTES, FACTURES, PAIEMENTS
# ──────────────────────────────────────────────────────────────────────────────

# Chaque vente définit :
#   client, produits (référence → quantité), date, statut, mode_paiement,
#   crédit_jours, paiements (liste de montants par mode)
VENTES_DATA = [
    # 1. Comptant espèces — Boutique Soa
    {
        'client_code': 'CLI-MG-001',
        'reference': 'VTE-MG-001',
        'date_jours_ago': 5,
        'lignes': [
            ('DISTRI-MG-001', 2),   # Riz 50kg x2
            ('DISTRI-MG-003', 3),   # Huile 5L x3
            ('DISTRI-MG-005', 1),   # Sucre 25kg x1
            ('DISTRI-MG-009', 5),   # Eau pack x5
        ],
        'statut': 'payee',
        'mode_paiement': 'especes',
        'credit_jours': 0,
        'echeance_jours_ago': 5,
        'paiements': [{'montant': None, 'mode': 'especes', 'jours_ago': 5}, 'complete': True],
        'notes': 'Livraison effectuée, règlement en espèces sur place',
    },
    # 2. Mobile Money — Épicerie Fitiavana
    {
        'client_code': 'CLI-MG-002',
        'reference': 'VTE-MG-002',
        'date_jours_ago': 4,
        'lignes': [
            ('DISTRI-MG-006', 20),  # Sucre 1kg x20
            ('DISTRI-MG-012', 10),   # Biscuit x10
            ('DISTRI-MG-015', 5),    # Conserves sardine x5
            ('DISTRI-MG-011', 15),   # Eau 1,5L x15
        ],
        'statut': 'payee',
        'mode_paiement': 'orange_money',
        'credit_jours': 0,
        'echeance_jours_ago': 4,
        'paiements': [{'montant': None, 'mode': 'orange_money', 'jours_ago': 4}, 'complete': True],
        'notes': 'Paiement Orange Money, reçu par SMS',
    },
    # 3. Crédit 7j, partiel — Shop Mada
    {
        'client_code': 'CLI-MG-003',
        'reference': 'VTE-MG-003',
        'date_jours_ago': 10,
        'lignes': [
            ('DISTRI-MG-002', 5),   # Riz 25kg x5
            ('DISTRI-MG-004', 20),   # Huile 1L x20
            ('DISTRI-MG-007', 2),   # Farine 50kg x2
        ],
        'statut': 'payee',
        'mode_paiement': 'a_voir',
        'credit_jours': 7,
        'echeance_jours_ago': 3,
        'paiements': [{'montant': 800000, 'mode': 'orange_money', 'jours_ago': 3}, {'montant': None, 'mode': 'a_voir', 'jours_ago': 0}, 'complete': True],
        'notes': 'Crédit 7 jours — acompte de 800 000 Ar reçu, reste à régler',
    },
    # 4. Crédit 15j, payé à l'échéance — Supermarché Mahajy
    {
        'client_code': 'CLI-MG-004',
        'reference': 'VTE-MG-004',
        'date_jours_ago': 18,
        'lignes': [
            ('DISTRI-MG-001', 3),   # Riz 50kg x3
            ('DISTRI-MG-003', 5),   # Huile 5L x5
            ('DISTRI-MG-005', 3),   # Sucre 25kg x3
            ('DISTRI-MG-016', 15),  # Conserves haricots x15
        ],
        'statut': 'payee',
        'mode_paiement': 'virement',
        'credit_jours': 15,
        'echeance_jours_ago': 3,
        'paiements': [{'montant': None, 'mode': 'virement', 'jours_ago': 3}, 'complete': True],
        'notes': 'Crédit 15 jours — solde réglé à l\'échéance par virement bancaire',
    },
    # 5. Crédit 30j, reste à payer — Centrale des Épiceries
    {
        'client_code': 'CLI-MG-010',
        'reference': 'VTE-MG-005',
        'date_jours_ago': 35,
        'lignes': [
            ('DISTRI-MG-001', 5),   # Riz 50kg x5
            ('DISTRI-MG-003', 10),  # Huile 5L x10
            ('DISTRI-MG-005', 4),   # Sucre 25kg x4
            ('DISTRI-MG-007', 3),   # Farine 50kg x3
            ('DISTRI-MG-010', 8),   # Boisson 12-pack x8
            ('DISTRI-MG-012', 20),  # Biscuit x20
        ],
        'statut': 'payee_partiel',
        'mode_paiement': 'a_voir',
        'credit_jours': 30,
        'echeance_jours_ago': 5,
        'paiements': [{'montant': 2500000, 'mode': 'virement', 'jours_ago': 5}, 'complete': False],
        'notes': 'Crédit 30 jours — acompte de 2 500 000 Ar reçu, reste à payer',
    },
    # 6. En attente, non payée — Restaurant Le Zebu
    {
        'client_code': 'CLI-MG-008',
        'reference': 'VTE-MG-006',
        'date_jours_ago': 3,
        'lignes': [
            ('DISTRI-MG-002', 3),   # Riz 25kg x3
            ('DISTRI-MG-004', 10),   # Huile 1L x10
            ('DISTRI-MG-009', 3),   # Eau pack x3
            ('DISTRI-MG-015', 10),  # Conserves sardine x10
        ],
        'statut': 'en_attente',
        'mode_paiement': 'a_voir',
        'credit_jours': 7,
        'echeance_jours_ago': 0,
        'paiements': [], 'complete': False,
        'notes': 'Commande livrée, paiement attendu dans 7 jours',
    },
    # 7. Partiellement réglée — Hôtel Coco Beach
    {
        'client_code': 'CLI-MG-009',
        'reference': 'VTE-MG-007',
        'date_jours_ago': 12,
        'lignes': [
            ('DISTRI-MG-001', 1),   # Riz 50kg x1
            ('DISTRI-MG-003', 2),   # Huile 5L x2
            ('DISTRI-MG-005', 1),   # Sucre 25kg x1
            ('DISTRI-MG-009', 8),   # Eau pack x8
            ('DISTRI-MG-012', 10),  # Biscuit x10
        ],
        'statut': 'payee_partiel',
        'mode_paiement': 'a_voir',
        'credit_jours': 15,
        'echeance_jours_ago': 2,
        'paiements': [{'montant': 500000, 'mode': 'especes', 'jours_ago': 2}, 'complete': True],
        'notes': 'Crédit 15 jours — 500 000 Ar remis en espèces, solde restant',
    },
    # 8. Livrée, non payée, crédit 15j — Dépôt de Quartier
    {
        'client_code': 'CLI-MG-007',
        'reference': 'VTE-MG-008',
        'date_jours_ago': 20,
        'lignes': [
            ('DISTRI-MG-001', 2),   # Riz 50kg x2
            ('DISTRI-MG-003', 3),   # Huile 5L x3
            ('DISTRI-MG-005', 2),   # Sucre 25kg x2
            ('DISTRI-MG-007', 2),   # Farine 50kg x2
            ('DISTRI-MG-010', 6),   # Boisson 12-pack x6
        ],
        'statut': 'en_attente',
        'mode_paiement': 'a_voir',
        'credit_jours': 15,
        'echeance_jours_ago': 5,
        'paiements': [], 'complete': False,
        'notes': 'Livraison effectuée, crédit 15 jours, paiement en attente',
    },
]


def seed_ventes(tenant_id, client_map, produits_map, commercial_id, stock_mgr_id):
    """Crée les ventes, lignes, factures, paiements et mouvements de stock."""
    ventes = []
    now = datetime.utcnow()

    for vd in VENTES_DATA:
        client = client_map.get(vd['client_code'])
        if not client:
            print(f"  [WARN] Client {vd['client_code']} introuvable")
            continue

        date_vente = now - timedelta(days=vd['date_jours_ago'])

        # Créer la vente
        vente = Vente(
            reference=vd['reference'],
            client_id=client.id,
            commercial_id=commercial_id,
            date=date_vente,
            mode_paiement=vd['mode_paiement'],
            type_vente='gros',
            remarque=vd['notes'],
            statut=vd['statut'],
            tenant_id=tenant_id,
            created_by=commercial_id,
            updated_by=commercial_id,
        )
        db.session.add(vente)
        db.session.flush()

        total_ht = Decimal('0')
        total_ttc = Decimal('0')

        for ref, qty in vd['lignes']:
            p = produits_map.get(ref)
            if not p:
                print(f"  [WARN] Produit {ref} introuvable pour vente {vd['reference']}")
                continue
            ligne = LigneVente(
                vente_id=vente.id,
                produit_id=p.id,
                tenant_id=tenant_id,
                quantite=qty,
                prix_unitaire_ht=p.prix_vente_ht,
                taux_tva=TAUX_TVA,
                remise=client.remise_standard or Decimal('0'),
                created_by=commercial_id,
                updated_by=commercial_id,
            )
            db.session.add(ligne)
            db.session.flush()

            total_ht += ligne.total_ht
            total_ttc += ligne.total_ttc

            # Réduire le stock et créer un mouvement de sortie
            p.quantite_stock -= ligne.quantite
            stock_before = p.quantite_stock + ligne.quantite
            sortie = MouvementStock(
                produit_id=p.id,
                tenant_id=tenant_id,
                type_mouvement=TypeMouvement.SORTIE,
                quantite=ligne.quantite,
                stock_avant=stock_before,
                stock_apres=p.quantite_stock,
                raison=f"Vente {vd['reference']} — {client.raison_sociale}",
                reference=vd['reference'],
                created_by=stock_mgr_id,
                created_at=date_vente,
            )
            db.session.add(sortie)

        vente.total_ht = total_ht
        vente.total_ttc = total_ttc
        db.session.flush()

        # Créer la facture liée à la vente
        facture = Facture(
            vente_id=vente.id,
            client_id=client.id,
            tenant_id=tenant_id,
            reference=f"FAC-{vd['reference']}",
            total_ht=total_ht,
            total_ttc=total_ttc,
            statut='non_payee',
            created_by=commercial_id,
            updated_by=commercial_id,
        )
        db.session.add(facture)
        db.session.flush()

        # Créer les paiements
        total_paye = Decimal('0')
        for pmnt in vd.get('paiements', []):
            if pmnt.get('complete'):
                montant = total_ttc - total_paye
            else:
                montant = Decimal(str(pmnt['montant']))

            if montant <= 0:
                continue

            date_paiement = now - timedelta(days=pmnt.get('jours_ago', 0))
            paiement = Paiement(
                facture_id=facture.id,
                client_id=client.id,
                tenant_id=tenant_id,
                montant=montant,
                mode_paiement=pmnt['mode'],
                operateur_mobile=pmnt['mode'] if pmnt['mode'] in ('orange_money', 'airtel_money', 'mvola') else None,
                numero_telephone=client.mobile,
                devise='MGA',
                statut=StatutPaiement.CONFIRME,
                type=TypePaiement.VENTE,
                reference=f"P-{facture.reference}-{pmnt.get('mode', 'especes')[:4]}",
                date_paiement=date_paiement,
                notes=f"Paiement {pmnt['mode']} — Vente {vd['reference']}",
                provider='especes',
                payment_method=pmnt['mode'].upper() if pmnt['mode'] in ('orange_money', 'airtel_money', 'mvola') else 'ESPECES',
                completed_at=date_paiement,
                created_by=commercial_id,
                updated_by=commercial_id,
            )
            db.session.add(paiement)
            total_paye += montant

        # Mettre à jour le statut de la facture
        if total_paye >= total_ttc and total_paye > 0:
            facture.statut = 'payee'
        elif total_paye > 0:
            facture.statut = 'payee_partiel'
        else:
            facture.statut = 'non_payee'

        # Mettre à jour le solde client
        client.solde = client.solde or Decimal('0')
        client.solde -= total_ttc
        client.solde += total_paye

        ventes.append(vente)
        print(f"  [OK] Vente {vd['reference']} — {client.raison_sociale} — HT={float(total_ht):,.0f} Ar — TTC={float(total_ttc):,.0f} Ar — Facture statut={facture.statut}")

    db.session.commit()
    print(f"  [OK] {len(ventes)} ventes créées avec factures et paiements")
    return ventes


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 7 — ACHATS FOURNISSEURS (CommandeAchat + LigneAchat + réception +
#            FactureFournisseur + Paiement)
# ──────────────────────────────────────────────────────────────────────────────

ACHATS_DATA = [
    # 1. Rizière Mahavelika — réceptionné, facturé, payé
    {
        'fournisseur_code': 'FOU-MG-001',
        'reference': 'ACH-MG-001',
        'date_jours_ago': 40,
        'statut': StatutCommandeAchat.RECUE,
        'lignes': [
            ('DISTRI-MG-001', 20, Decimal('350000.00')),  # Riz 50kg x20
            ('DISTRI-MG-002', 30, Decimal('175000.00')),  # Riz 25kg x30
        ],
        'facture_ref': 'FACFOU-MG-001',
        'facture_statut': 'payee',
        'paiements': [{'montant': None, 'mode': 'virement', 'jours_ago': 38, 'complete': True}],
        'notes': 'Livraison complète, paiement reçu',
    },
    # 2. Huilerie Centrale — réceptionné, facturé, partiellement payé
    {
        'fournisseur_code': 'FOU-MG-003',
        'reference': 'ACH-MG-002',
        'date_jours_ago': 25,
        'statut': StatutCommandeAchat.PARTIELLEMENT_RECUE,
        'lignes': [
            ('DISTRI-MG-003', 10, Decimal('85000.00')),  # Huile 5L x10
            ('DISTRI-MG-004', 50, Decimal('2500.00')),  # Huile 1L x50
        ],
        'facture_ref': 'FACFOU-MG-002',
        'facture_statut': 'payee_partiel',
        'paiements': [{'montant': 500000, 'mode': 'virement', 'jours_ago': 22, 'complete': False}],
        'notes': 'Livraison partielle (Huile 5L OK, Huile 1L en retard), acompte reçu',
    },
    # 3. TopAliment Import — en cours, non livré
    {
        'fournisseur_code': 'FOU-MG-005',
        'reference': 'ACH-MG-003',
        'date_jours_ago': 10,
        'statut': StatutCommandeAchat.ENVOYEE,
        'lignes': [
            ('DISTRI-MG-012', 30, Decimal('15000.00')),  # Biscuit x30
            ('DISTRI-MG-013', 10, Decimal('65000.00')),  # Savon x10
        ],
        'facture_ref': None,
        'facture_statut': None,
        'paiements': [],
        'notes': 'Commande envoyée, livraison prévue dans 14 jours',
    },
    # 4. Conserves de Madagascar — réceptionné, facturé, payé
    {
        'fournisseur_code': 'FOU-MG-008',
        'reference': 'ACH-MG-004',
        'date_jours_ago': 28,
        'statut': StatutCommandeAchat.RECUE,
        'lignes': [
            ('DISTRI-MG-015', 20, Decimal('12500.00')),  # Conserves sardine x20
            ('DISTRI-MG-016', 15, Decimal('9800.00')),  # Conserves haricots x15
        ],
        'facture_ref': 'FACFOU-MG-004',
        'facture_statut': 'payee',
        'paiements': [{'montant': None, 'mode': 'virement', 'jours_ago': 26, 'complete': True}],
        'notes': 'Livraison complète, solde réglé',
    },
]


def seed_achats(tenant_id, fournisseur_map, produits_map, stock_mgr_id, admin_id):
    """Crée les commandes d'achat, réceptions, factures fournisseur et paiements."""
    now = datetime.utcnow()
    achats = []

    for ad in ACHATS_DATA:
        fournisseur = fournisseur_map.get(ad['fournisseur_code'])
        if not fournisseur:
            continue

        date_cmd = now - timedelta(days=ad['date_jours_ago'])

        # CommandeAchat (obligatoire pour LigneAchat)
        commande_achat = CommandeAchat(
            reference=ad['reference'],
            fournisseur_id=fournisseur.id,
            tenant_id=tenant_id,
            date_commande=date_cmd,
            date_livraison_prevue=date_cmd + timedelta(days=fournisseur.delai_livraison or 5),
            statut=ad['statut'],
            conditions_paiement=fournisseur.conditions_paiement,
            remarque=ad['notes'],
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(commande_achat)
        db.session.flush()

        # CommandeFournisseur (simplifiée, pour la trace)
        ref_cmd_fou = f"CF-{ad['reference']}"
        cmd_fournisseur = CommandeFournisseur(
            reference=ref_cmd_fou,
            fournisseur_id=fournisseur.id,
            tenant_id=tenant_id,
            statut='recue' if ad['statut'] in (StatutCommandeAchat.RECUE, StatutCommandeAchat.PARTIELLEMENT_RECUE) else 'en_attente',
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(cmd_fournisseur)
        db.session.flush()

        total_ht = Decimal('0')
        total_ttc = Decimal('0')
        total_qty_recue = Decimal('0')
        total_qty_cmd = Decimal('0')

        for ref, qty, prix_achat in ad['lignes']:
            p = produits_map.get(ref)
            if not p:
                continue

            ligne_achat = LigneAchat(
                commande_fournisseur_id=cmd_fournisseur.id,
                commande_achat_id=commande_achat.id,
                produit_id=p.id,
                tenant_id=tenant_id,
                quantite=qty,
                prix_unitaire_ht=prix_achat,
                taux_tva=TAUX_TVA,
                created_by=stock_mgr_id,
                updated_by=stock_mgr_id,
            )
            db.session.add(ligne_achat)
            db.session.flush()

            total_ht += ligne_achat.total_ht
            total_ttc += ligne_achat.total_ht * (1 + TAUX_TVA / 100)
            total_qty_cmd += qty

            # Si réceptionnée, augmenter le stock
            if ad['statut'] in (StatutCommandeAchat.RECUE, StatutCommandeAchat.PARTIELLEMENT_RECUE):
                qty_recue = qty if ad['statut'] == StatutCommandeAchat.RECUE else qty // 2
                qty_recue = Decimal(str(qty_recue))
                total_qty_recue += qty_recue

                p.quantite_stock += qty_recue
                entree = MouvementStock(
                    produit_id=p.id,
                    tenant_id=tenant_id,
                    type_mouvement=TypeMouvement.ENTREE,
                    quantite=qty_recue,
                    stock_avant=p.quantite_stock - qty_recue,
                    stock_apres=p.quantite_stock,
                    raison=f"Réception achat {ad['reference']} — {fournisseur.raison_sociale}",
                    reference=ad['reference'],
                    created_by=stock_mgr_id,
                    created_at=date_cmd + timedelta(days=fournisseur.delai_livraison or 5),
                )
                db.session.add(entree)

        commande_achat.total_ht = total_ht
        commande_achat.total_ttc = total_ttc
        cmd_fournisseur.total_ht = total_ht
        cmd_fournisseur.total_ttc = total_ttc

        # Réception d'achat (si réceptionnée)
        if ad['statut'] in (StatutCommandeAchat.RECUE, StatutCommandeAchat.PARTIELLEMENT_RECUE):
            reception = ReceptionAchat(
                commande_achat_id=commande_achat.id,
                tenant_id=tenant_id,
                reference=f"REC-{ad['reference']}",
                date_reception=date_cmd + timedelta(days=fournisseur.delai_livraison or 5),
                receptionne_par_id=stock_mgr_id,
                quantite_recue=total_qty_recue,
                quantite_commandee=total_qty_cmd,
                ecart=total_qty_cmd - total_qty_recue,
                remarque='Contrôle qualité effectué',
                created_by=stock_mgr_id,
                updated_by=stock_mgr_id,
            )
            db.session.add(reception)
            db.session.flush()

        # Facture fournisseur + paiement
        if ad.get('facture_ref'):
            facture_fou = FactureFournisseur(
                fournisseur_id=fournisseur.id,
                tenant_id=tenant_id,
                reference=ad['facture_ref'],
                total_ht=total_ht,
                total_ttc=total_ttc,
                statut=ad['facture_statut'],
                created_by=admin_id,
                updated_by=admin_id,
            )
            db.session.add(facture_fou)
            db.session.flush()

            # Paiements fournisseur
            total_paye = Decimal('0')
            for pmnt in ad.get('paiements', []):
                if pmnt.get('complete'):
                    montant = total_ttc - total_paye
                else:
                    montant = Decimal(str(pmnt['montant']))

                if montant <= 0:
                    continue

                date_p = now - timedelta(days=pmnt.get('jours_ago', 0))
                paiement = Paiement(
                    fournisseur_id=fournisseur.id,
                    tenant_id=tenant_id,
                    montant=montant,
                    mode_paiement=pmnt['mode'],
                    devise='MGA',
                    statut=StatutPaiement.CONFIRME,
                    type=TypePaiement.ACHAT,
                    reference=f"PFOU-{ad['facture_ref']}",
                    date_paiement=date_p,
                    notes=f"Paiement fournisseur — {fournisseur.raison_sociale}",
                    provider='bank',
                    completed_at=date_p,
                    created_by=admin_id,
                    updated_by=admin_id,
                )
                db.session.add(paiement)
                total_paye += montant

            # Mettre à jour le statut de la facture fournisseur
            if total_paye >= total_ttc:
                facture_fou.statut = 'payee'
            elif total_paye > 0:
                facture_fou.statut = 'payee_partiel'

            print(f"  [OK] Achat {ad['reference']} — {fournisseur.raison_sociale} — HT={float(total_ht):,.0f} — Statut CMD={ad['statut'].value}, Facture={facture_fou.statut}")

        achats.append(commande_achat)

    db.session.commit()
    print(f"  [OK] {len(achats)} commandes d'achat créées")
    return achats


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 8 — COMPTABILITÉ
# ──────────────────────────────────────────────────────────────────────────────

COMPTES_DATA = [
    ('101', 'Capital social', TypeCompte.ACTIF, None),
    ('106', 'Report à nouveau', TypeCompte.ACTIF, None),
    ('120', 'Résultat de l exercice', TypeCompte.ACTIF, None),
    ('215', 'Stocks de marchandises', TypeCompte.ACTIF, None),
    ('31',  'Clients', TypeCompte.ACTIF, None),
    ('34',  'Fournisseurs', TypeCompte.PASSIF, None),
    ('445', 'Taxe sur le chiffre d\'affaires déboursée', TypeCompte.PASSIF, None),
    ('4457', 'TVA déductible sur achats', TypeCompte.ACTIF, '445'),
    ('512', 'Banque', TypeCompte.ACTIF, None),
    ('530', 'Caisse', TypeCompte.ACTIF, None),
    ('607', 'Achats de marchandises', TypeCompte.CHARGE, None),
    ('701', 'Ventes de marchandises', TypeCompte.PRODUIT, None),
    ('706', 'Représentation du service', TypeCompte.PRODUIT, None),
    ('775', 'Charges de personnel', TypeCompte.CHARGE, None),
]


def seed_comptabilite(tenant_id, ventes, achats, fournisseur_map, client_map, admin_id):
    """Crée le plan comptable, écritures et mouvements de trésorerie."""
    now = datetime.utcnow()
    comptes_map = {}

    for numero, nom, type_compte, parent_num in COMPTES_DATA:
        existing = CompteComptable.query.filter_by(numero=numero, tenant_id=tenant_id).first()
        if existing:
            comptes_map[numero] = existing.id
            continue
        parent_id = comptes_map.get(parent_num) if parent_num else None
        compte = CompteComptable(
            numero=numero,
            nom=nom,
            type_compte=type_compte,
            sous_compte_id=parent_id,
            solde=Decimal('0.00'),
            is_actif=True,
            tenant_id=tenant_id,
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(compte)
        db.session.flush()
        comptes_map[numero] = compte.id

    ecritures = []

    # Écriture d'ouverture — apport en capital
    ecritures.append({
        'date': now - timedelta(days=30),
        'compte_id': comptes_map['512'],
        'debit': Decimal('5000000.00'), 'credit': Decimal('0'),
        'libelle': 'Apport initial en capital — Distrib Moderne SARL',
        'entite_type': 'tenant', 'entite_id': None,
    })
    ecritures.append({
        'date': now - timedelta(days=30),
        'compte_id': comptes_map['101'],
        'debit': Decimal('0'), 'credit': Decimal('5000000.00'),
        'libelle': 'Capital social souscrit — Distrib Moderne SARL',
        'entite_type': 'tenant', 'entite_id': None,
    })

    # Écritures pour les ventes (Clients débit, Ventes crédit, TVA collectée crédit)
    ventes_comptees = sorted(ventes, key=lambda v: v.date)
    for v in ventes_comptees:
        if v.statut == 'annulee':
            continue
        ecritures.append({
            'date': v.date,
            'compte_id': comptes_map['31'],
            'debit': v.total_ttc, 'credit': Decimal('0'),
            'libelle': f'Vente {v.reference} — {v.client.nom_complet if v.client else "N/A"}',
            'entite_type': 'vente', 'entite_id': v.id,
        })
        ecritures.append({
            'date': v.date,
            'compte_id': comptes_map['701'],
            'debit': Decimal('0'), 'credit': v.total_ht,
            'libelle': f'Vente {v.reference} — TVA détaillée',
            'entite_type': 'vente', 'entite_id': v.id,
        })
        tva = v.total_ttc - v.total_ht
        if tva > 0:
            ecritures.append({
                'date': v.date,
                'compte_id': comptes_map['445'],
                'debit': Decimal('0'), 'credit': tva,
                'libelle': f'TVA collectée vente {v.reference}',
                'entite_type': 'vente', 'entite_id': v.id,
            })

    # Écritures pour les achats (Achats débit, Fournisseurs crédit, TVA déductible débit)
    for ca in achats:
        if ca.total_ht <= 0:
            continue
        ecritures.append({
            'date': ca.date_commande,
            'compte_id': comptes_map['607'],
            'debit': ca.total_ht, 'credit': Decimal('0'),
            'libelle': f'Achat {ca.reference} — {ca.fournisseur.raison_sociale if ca.fournisseur else "N/A"}',
            'entite_type': 'commande_achat', 'entite_id': ca.id,
        })
        ecritures.append({
            'date': ca.date_commande,
            'compte_id': comptes_map['34'],
            'debit': Decimal('0'), 'credit': ca.total_ht + (ca.total_ttc - ca.total_ht),
            'libelle': f'Facture fournisseur {ca.reference}',
            'entite_type': 'commande_achat', 'entite_id': ca.id,
        })
        tva_achat = ca.total_ttc - ca.total_ht
        if tva_achat > 0:
            ecritures.append({
                'date': ca.date_commande,
                'compte_id': comptes_map['4457'],
                'debit': tva_achat, 'credit': Decimal('0'),
                'libelle': f'TVA déductible achat {ca.reference}',
                'entite_type': 'commande_achat', 'entite_id': ca.id,
            })

    for ecr_data in ecritures:
        ecriture = EcritureComptable(
            date=ecr_data['date'],
            compte_id=ecr_data['compte_id'],
            montant_debit=ecr_data['debit'],
            montant_credit=ecr_data['credit'],
            libelle=ecr_data['libelle'],
            entite_type=ecr_data['entite_type'],
            entite_id=ecr_data['entite_id'],
            statut=StatutEcriture.VALIDE,
            tenant_id=tenant_id,
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(ecriture)
    db.session.flush()

    # Mouvements de trésorerie liés aux paiements
    tresorerie_entries = []
    all_paiements = Paiement.query.filter_by(tenant_id=tenant_id, is_active=True).all()
    for p in all_paiements:
        if p.type == TypePaiement.VENTE and p.facture_id:
            tres_type = TypeTresorerie.ENTREE
            compte_banque = '530' if p.mode_paiement == 'especes' else '512'
        elif p.type == TypePaiement.ACHAT and p.fournisseur_id:
            tres_type = TypeTresorerie.SORTIE
            compte_banque = '512'  # virement
        elif p.type == TypePaiement.ABONNEMENT:
            continue  # skip subscription payments
        else:
            continue

        tres = Tresorerie(
            date=p.date_paiement.date() if p.date_paiement else now.date(),
            type_operation=tres_type,
            montant=p.montant,
            mode_paiement=p.mode_paiement,
            libelle=p.notes or f'Paiement {p.reference}',
            compte_bancaire=compte_banque + '-MG',
            reference=p.reference,
            is_reconcilie=True,
            compte_id=comptes_map.get(compte_banque),
            tenant_id=tenant_id,
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(tres)
        tresorerie_entries.append(tres)

    db.session.commit()
    print(f"  [OK] {len(COMPTES_DATA)} comptes comptables, {len(ecritures)} écritures, {len(tresorerie_entries)} mouvements de trésorerie créés")
    return comptes_map


# ──────────────────────────────────────────────────────────────────────────────
#  POINT D'ENTRÉE
# ──────────────────────────────────────────────────────────────────────────────

def seed_all():
    """Exécute l'ensemble des phases de seed."""
    with app.app_context():
        db.create_all()
        result = seed_tenant_and_users()
        tenant = result['tenant']
        users = result['users']

        fournisseurs = seed_fournisseurs(tenant.id, users['admin'].id)
        fournisseur_map = {f.code: f for f in fournisseurs}

        clients = seed_clients(tenant.id, users['commercial'].id, users['admin'].id)
        client_map = {c.code: c for c in clients}

        produits = seed_produits(tenant.id, fournisseurs, users['admin'].id)
        produits_map = {p.reference: p for p in produits}

        seed_stocks_initiaux(produits, tenant.id, users['stock'].id)

        ventes = seed_ventes(
            tenant.id, client_map, produits_map,
            users['commercial'].id, users['stock'].id
        )

        achats = seed_achats(
            tenant.id, fournisseur_map, produits_map,
            users['stock'].id, users['admin'].id
        )

        seed_comptabilite(
            tenant.id, ventes, achats,
            fournisseur_map, client_map, users['admin'].id
        )

        print("\n" + "=" * 70)
        print("SEMAGE MÉTIER MADAGASCAR — TERMINÉ AVEC SUCCÈS")
        print("=" * 70)
        print(f"  Tenant       : {tenant.nom}")
        print(f"  Fournisseurs : {len(fournisseurs)}")
        print(f"  Clients      : {len(clients)}")
        print(f"  Produits     : {len(produits)}")
        print(f"  Ventes       : {len(ventes)}")
        print(f"  Achats       : {len(achats)}")
        print(f"  Mot de passe : {PASSWORD}")
        print(f"  Admin email  : admin@distrib-moderne.mg")
        print(f"  Commercial   : jean.rakoto@distrib-moderne.mg")
        print("=" * 70)


if __name__ == '__main__':
    seed_all()
