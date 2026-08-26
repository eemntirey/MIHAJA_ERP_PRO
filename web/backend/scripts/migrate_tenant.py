import os
import sys
import secrets
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.security.auth import hash_password
from sqlalchemy import text
from datetime import datetime


def migrate():
    """Applique les migrations multi-tenant"""
    app = create_app()
    
    with app.app_context():
        print("Début de la migration multi-tenant...")
        
        # Créer toutes les tables (si elles n'existent pas)
        db.create_all()
        print("Tables vérifiées/créées.")
        
        # Vérifier si la colonne tenant_id existe déjà
        inspector = db.inspect(db.engine)
        
        # Ajouter tenant_id aux tables existantes si nécessaire
        tables_to_update = [
            'utilisateurs', 'produits', 'clients', 'fournisseurs',
            'stocks', 'ventes', 'factures', 'paiements',
            'mouvements_stock', 'commandes_fournisseur', 'factures_fournisseur',
            'lignes_vente', 'lignes_achat'
        ]
        
        for table_name in tables_to_update:
            try:
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                if 'tenant_id' not in columns:
                    with db.engine.connect() as conn:
                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN tenant_id INTEGER'))
                        conn.commit()
                    print(f"  Colonne tenant_id ajoutée à {table_name}")
            except Exception as e:
                print(f"  {table_name}: {e}")
        
        # Créer le tenant par défaut s'il n'existe pas
        default_tenant = Tenant.query.filter_by(slug='demo').first()
        if not default_tenant:
            default_tenant = Tenant(
                nom='ERP Démonstration',
                slug='demo',
                domaine='localhost',
                email_contact='admin@demo.com',
                statut=StatutTenant.ACTIF,
                plan='pro',
                max_utilisateurs=20,
                max_produits=1000,
                max_clients=500,
                devise='MGA',
                langue='mg',
            )
            db.session.add(default_tenant)
            db.session.flush()
            print("Tenant par défaut créé: demo")
        
        # Créer l'admin par défaut s'il n'existe pas
        admin = Utilisateur.query.filter_by(
            username='admin',
            tenant_id=default_tenant.id
        ).first()
        
        if not admin:
            default_password = os.getenv('SEED_USER_PASSWORD') or secrets.token_urlsafe(12)
            admin = Utilisateur(
                username='admin',
                email='admin@demo.com',
                password_hash=hash_password(default_password),
                nom='Administrateur',
                prenom='System',
                role=Role.ADMIN,
                tenant_id=default_tenant.id,
            )
            db.session.add(admin)
            print(f"Admin créé: admin")
        
        db.session.commit()
        print("Migration terminée avec succès!")


def seed():
    """Remplit la base de données avec des données d'exemple"""
    app = create_app()
    
    with app.app_context():
        print("Remplissage de la base de données...")
        
        tenant = Tenant.query.filter_by(slug='demo').first()
        if not tenant:
            print("Aucun tenant trouvé. Exécutez d'abord migrate()")
            return
        
        # Supprimer les anciennes données du tenant
        Produit.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        from app.models.client import Client
        Client.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        from app.models.fournisseur import Fournisseur
        Fournisseur.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        
        # Créer des produits d'exemple
        produits = [
            Produit(
                nom='Riz blanc (sac 50 kg)', reference='PROD-001',
                prix_achat_ht=102000.0, prix_vente_ht=130000.0,
                quantite_stock=120, categorie='Alimentaire',
                unite='sac',
                tenant_id=tenant.id
            ),
            Produit(
                nom='Huile de tournesol (carton 6 x 1 L)', reference='PROD-002',
                prix_achat_ht=124000.0, prix_vente_ht=160000.0,
                quantite_stock=35, categorie='Épicerie',
                unite='carton',
                tenant_id=tenant.id
            ),
            Produit(
                nom='Eau minérale (pack 6 x 1,5 L)', reference='PROD-003',
                prix_achat_ht=5200.0, prix_vente_ht=7500.0,
                quantite_stock=500, categorie='Boissons',
                unite='pack',
                tenant_id=tenant.id
            ),
        ]
        
        # Créer des clients d'exemple
        clients = [
            Client(
                code='CLI001', raison_sociale='Boutique Soa',
                type='boutique', email='contact@boutiquesoa.mg',
                ville_facturation='Antananarivo',
                code_postal_facturation='101',
                tenant_id=tenant.id
            ),
            Client(
                code='CLI002', raison_sociale='Épicerie Fitiavana',
                type='epicerie', email='contact@epiceriefitiavana.mg',
                ville_facturation='Antsirabe',
                code_postal_facturation='110',
                tenant_id=tenant.id
            ),
        ]
        
        # Créer des fournisseurs d'exemple
        fournisseurs = [
            Fournisseur(
                code='FOU001', raison_sociale='Rizière Mahavelika',
                type='producteur_local', email='contact@mahavelika.mg',
                ville='Fianarantsoa',
                tenant_id=tenant.id
            ),
            Fournisseur(
                code='FOU002', raison_sociale='TopAliment Import',
                type='fournisseur_international', email='info@topaliment.mg',
                ville='Toamasina',
                tenant_id=tenant.id
            ),
        ]
        
        db.session.add_all(produits + clients + fournisseurs)
        db.session.commit()
        print("Données d'exemple créées!")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'seed':
            seed()
        else:
            migrate()
    else:
        migrate()
