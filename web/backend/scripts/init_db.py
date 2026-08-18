#!/usr/bin/env python
"""
Script d'initialisation de la base de données
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur, Role
from app.models.produit import Produit
from app.models.fournisseur import Fournisseur
from app.models.client import Client
from app.models.stock import MouvementStock
from app.models.tenant import Tenant, StatutTenant
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.auth import hash_password
from decimal import Decimal
from datetime import datetime, timedelta, date
import random
import secrets

app = create_app()

def init_database():
    """Initialise la base de données avec des données de test"""
    with app.app_context():
        default_password = os.getenv('SEED_USER_PASSWORD') or secrets.token_urlsafe(12)
        
        print("  Suppression des tables existantes...")
        db.drop_all()
        
        print(" Création des tables...")
        db.create_all()

        print(" Création du tenant...")
        tenant = Tenant(
            nom='ERP Commercial',
            slug='erp-commercial',
            domaine='localhost',
            email_contact='admin@erp.com',
            statut=StatutTenant.ACTIF,
            plan='pro',
            max_utilisateurs=20,
            max_produits=1000,
            max_clients=500,
        )
        db.session.add(tenant)
        db.session.flush()
        
        print(" Création des utilisateurs...")
        # Admin
        admin = Utilisateur(
            username='admin',
            email='admin@erp.com',
            password_hash=hash_password(default_password),
            nom='Admin',
            prenom='System',
            role=Role.ADMIN,
            is_active=True
        )
        admin.save()
        
        # Commercial
        commercial = Utilisateur(
            username='commercial',
            email='commercial@erp.com',
            password_hash=hash_password(default_password),
            nom='Ramanantoandro',
            prenom='Jean',
            role=Role.SALES,
            is_active=True
        )
        commercial.save()
        
        # Stock
        stock_manager = Utilisateur(
            username='stock',
            email='stock@erp.com',
            password_hash=hash_password(default_password),
            nom='Ramiaramanana',
            prenom='Pierre',
            role=Role.STOCK,
            is_active=True
        )
        stock_manager.save()

        for utilisateur in (admin, commercial, stock_manager):
            utilisateur.tenant_id = tenant.id
        db.session.commit()
        
        print(" Création des fournisseurs...")
        fournisseurs = [
            Fournisseur(
                code='F001',
                raison_sociale='Tech Distributions',
                siret='12345678901234',
                email='contact@techdist.com',
                telephone='+261 34 12 345 67',
                adresse='15 rue des Technologies',
                code_postal='101',
                ville='Antananarivo',
                pays='Madagascar',
                type='national',
                est_actif=True
            ),
            Fournisseur(
                code='F002',
                raison_sociale='Global Import Export',
                siret='23456789012345',
                email='info@globalimport.com',
                telephone='+261 34 47 258 36',
                adresse='25 avenue du Commerce',
                code_postal='601',
                ville='Toamasina',
                pays='Madagascar',
                type='international',
                est_actif=True
            ),
            Fournisseur(
                code='F003',
                raison_sociale='Fournitures Pro',
                siret='34567890123456',
                email='contact@fourniturespro.mg',
                telephone='+261 34 47 852 36',
                adresse='8 rue des Fournisseurs',
                code_postal='301',
                ville='Fianarantsoa',
                pays='Madagascar',
                type='grossiste',
                est_actif=True
            )
        ]
        for fournisseur in fournisseurs:
            fournisseur.tenant_id = tenant.id
            fournisseur.save()
        
        print(" Création des clients...")
        clients = [
            Client(
                code='C001',
                raison_sociale='Grande Distribution SA',
                email='contact@grandedistrib.com',
                telephone='+261 34 12 345 67',
                adresse_facturation='100 rue du Commerce',
                code_postal_facturation='101',
                ville_facturation='Antananarivo',
                pays_facturation='Madagascar',
                type='distributeur',
                secteur='commerce',
                commercial_id=commercial.id,
                est_actif=True
            ),
            Client(
                code='C002',
                nom='Martin',
                prenom='Sophie',
                email='sophie.martin@email.com',
                telephone='+261 34 85 741 23',
                adresse_facturation='45 avenue des Fleurs',
                code_postal_facturation='401',
                ville_facturation='Antsirabe',
                pays_facturation='Madagascar',
                type='particulier',
                commercial_id=commercial.id,
                est_actif=True
            ),
            Client(
                code='C003',
                raison_sociale='Entreprise Solutions',
                siret='45678901234567',
                email='contact@entreprisesolutions.mg',
                telephone='+261 34 47 852 36',
                adresse_facturation='12 rue de l\'Innovation',
                code_postal_facturation='301',
                ville_facturation='Toliara',
                pays_facturation='Madagascar',
                type='professionnel',
                secteur='services',
                commercial_id=commercial.id,
                est_actif=True
            )
        ]
        for client in clients:
            client.tenant_id = tenant.id
            client.save()
        
        print(" Création des produits...")
        produits_data = [
            {
                'reference': 'P001',
                'nom': 'Ordinateur Portable Pro',
                'description_courte': 'Ordinateur portable haut de gamme',
                'categorie': 'Informatique',
                'sous_categorie': 'Ordinateurs',
                'prix_achat_ht': Decimal('800.00'),
                'prix_vente_ht': Decimal('1200.00'),
                'taux_tva': Decimal('10.00'),
                'quantite_stock': Decimal('50'),
                'seuil_alerte': Decimal('10'),
                'seuil_critique': Decimal('5'),
                'fournisseur_id': fournisseurs[0].id,
                'marque': 'Dell',
                'modele': 'Latitude 7420',
                'poids': Decimal('1.4')
            },
            {
                'reference': 'P002',
                'nom': 'Smartphone Android',
                'description_courte': 'Smartphone dernière génération',
                'categorie': 'Informatique',
                'sous_categorie': 'Téléphones',
                'prix_achat_ht': Decimal('400.00'),
                'prix_vente_ht': Decimal('650.00'),
                'taux_tva': Decimal('10.00'),
                'quantite_stock': Decimal('100'),
                'seuil_alerte': Decimal('20'),
                'seuil_critique': Decimal('10'),
                'fournisseur_id': fournisseurs[0].id,
                'marque': 'Samsung',
                'modele': 'Galaxy S21',
                'poids': Decimal('0.2')
            },
            {
                'reference': 'P003',
                'nom': 'Papier A4 Premium',
                'description_courte': 'Ramette de papier A4 80g/m²',
                'categorie': 'Bureau',
                'sous_categorie': 'Papeterie',
                'prix_achat_ht': Decimal('5.00'),
                'prix_vente_ht': Decimal('8.50'),
                'taux_tva': Decimal('10.00'),
                'quantite_stock': Decimal('500'),
                'seuil_alerte': Decimal('50'),
                'seuil_critique': Decimal('20'),
                'fournisseur_id': fournisseurs[2].id,
                'marque': 'Excellence',
                'poids': Decimal('2.5')
            },
            {
                'reference': 'P004',
                'nom': 'Cartouche d\'encre Noire',
                'description_courte': 'Cartouche d\'encre compatible',
                'categorie': 'Bureau',
                'sous_categorie': 'Fournitures',
                'prix_achat_ht': Decimal('12.00'),
                'prix_vente_ht': Decimal('19.90'),
                'taux_tva': Decimal('10.00'),
                'quantite_stock': Decimal('75'),
                'seuil_alerte': Decimal('15'),
                'seuil_critique': Decimal('5'),
                'fournisseur_id': fournisseurs[2].id,
                'marque': 'Compatible',
                'poids': Decimal('0.1')
            },
            {
                'reference': 'P005',
                'nom': 'Scanner Portable',
                'description_courte': 'Scanner portable pour documents',
                'categorie': 'Informatique',
                'sous_categorie': 'Périphériques',
                'prix_achat_ht': Decimal('150.00'),
                'prix_vente_ht': Decimal('250.00'),
                'taux_tva': Decimal('10.00'),
                'quantite_stock': Decimal('30'),
                'seuil_alerte': Decimal('8'),
                'seuil_critique': Decimal('3'),
                'fournisseur_id': fournisseurs[1].id,
                'marque': 'Brother',
                'modele': 'ScanPro 300',
                'poids': Decimal('0.8')
            }
        ]
        
        for data in produits_data:
            data['tenant_id'] = tenant.id
            produit = Produit(**data)
            produit.save()
            print(f"   {produit.nom} - {produit.quantite_stock} unités")
        
        print(" Création des mouvements de stock initiaux...")
        produits = Produit.query.all()
        for produit in produits:
            # Créer un mouvement d'entrée initial
            mouvement = MouvementStock(
                produit_id=produit.id,
                type_mouvement='entree',
                quantite=produit.quantite_stock,
                stock_avant=0,
                stock_apres=produit.quantite_stock,
                raison='Stock initial',
                created_by=admin.id,
                tenant_id=tenant.id,
            )
            mouvement.save()

        print(" Création du plan comptable...")
        comptes_data = [
            ('101', 'Capital social', 'actif', None),
            ('106', 'Réserves', 'actif', None),
            ('120', 'Résultat net', 'actif', None),
            ('164', 'Emprunts', 'passif', None),
            ('401', 'Fournisseurs', 'passif', None),
            ('411', 'Clients', 'actif', None),
            ('445', 'TVA collectée', 'passif', None),
            ('4457', 'TVA déductible', 'actif', '445'),
            ('512', 'Banque', 'actif', None),
            ('530', 'Caisse', 'actif', None),
            ('607', 'Achats marchandises', 'charge', None),
            ('701', 'Ventes marchandises', 'produit', None),
            ('706', 'Prestations de services', 'produit', None),
            ('707', 'Ventes produits fabriqués', 'produit', None),
            ('708', 'Ventes accessoires', 'produit', None),
            ('761', 'Produits financiers', 'produit', None),
            ('771', 'Produits exceptionnels', 'produit', None),
        ]
        comptes_map = {}
        for numero, nom, type_compte, parent_numero in comptes_data:
            parent_id = comptes_map.get(parent_numero) if parent_numero else None
            compte = CompteComptable(
                numero=numero,
                nom=nom,
                type_compte=TypeCompte(type_compte),
                sous_compte_id=parent_id,
                solde=Decimal('0.00'),
                is_actif=True,
                tenant_id=tenant.id,
            )
            db.session.add(compte)
            db.session.flush()
            comptes_map[numero] = compte.id

        print(" Création d'écritures comptables initiales...")
        ecritures_samples = [
            (date.today(), comptes_map.get('512'), Decimal('150000.00'), Decimal('0'), 'Apport initial capital', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('101'), Decimal('0'), Decimal('150000.00'), 'Capital social souscrit', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('401'), Decimal('0'), Decimal('45000.00'), 'Achat marchandises F001', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('607'), Decimal('45000.00'), Decimal('0'), 'Achat marchandises F001', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('411'), Decimal('32000.00'), Decimal('0'), 'Vente C001', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('701'), Decimal('0'), Decimal('32000.00'), 'Vente C001', StatutEcriture.VALIDE),
        ]
        for ecr_date, compte_id, debit, credit, libelle, statut in ecritures_samples:
            if compte_id:
                ecriture = EcritureComptable(
                    date=ecr_date,
                    compte_id=compte_id,
                    montant_debit=debit,
                    montant_credit=credit,
                    libelle=libelle,
                    statut=statut,
                    tenant_id=tenant.id,
                )
                db.session.add(ecriture)

        print(" Création d'entrées trésorerie initiales...")
        tresorerie_samples = [
            (date.today(), 'entree', Decimal('150000.00'), 'virement', 'Apport initial capital', 'BNI-001', 'APP-001'),
            (date.today(), 'sortie', Decimal('45000.00'), 'virement', 'Règlement F001', 'BNI-001', 'REG-F001'),
        ]
        for tres_date, type_op, montant, mode, libelle, compte_bancaire, reference in tresorerie_samples:
            entree = Tresorerie(
                date=tres_date,
                type_operation=TypeTresorerie(type_op),
                montant=montant,
                mode_paiement=mode,
                libelle=libelle,
                compte_bancaire=compte_bancaire,
                reference=reference,
                is_reconcilie=False,
                tenant_id=tenant.id,
            )
            db.session.add(entree)

        db.session.commit()
        
        print(" Base de données initialisée avec succès!")
        print(f"\n Mot de passe par defaut: {default_password}")
        print("  Identifiants:")
        print("  - Admin: admin@erp.com")
        print("  - Commercial: commercial@erp.com")
        print("  - Stock: stock@erp.com")

if __name__ == '__main__':
    init_database()