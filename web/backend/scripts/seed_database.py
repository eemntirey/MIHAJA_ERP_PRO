from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.produit import Produit
from app.security.auth import hash_password
from datetime import datetime, timedelta
import os
import secrets


def seed_tenant(tenant_data, admin_data):
    """Crée un tenant avec son admin"""
    app = create_app()
    
    with app.app_context():
        # Créer le tenant
        tenant = Tenant.query.filter_by(slug=tenant_data['slug']).first()
        if not tenant:
            tenant = Tenant(
                nom=tenant_data['nom'],
                slug=tenant_data['slug'],
                domaine=tenant_data.get('domaine'),
                email_contact=tenant_data.get('email_contact'),
                telephone=tenant_data.get('telephone'),
                adresse=tenant_data.get('adresse'),
                ville=tenant_data.get('ville'),
                pays=tenant_data.get('pays', 'Madagascar'),
                code_postal=tenant_data.get('code_postal'),
                statut=StatutTenant.ACTIF,
                plan=tenant_data.get('plan', 'gratuit'),
                max_utilisateurs=tenant_data.get('max_utilisateurs', 10),
                max_produits=tenant_data.get('max_produits', 500),
                max_clients=tenant_data.get('max_clients', 200),
                devise=tenant_data.get('devise', 'MGA'),
                langue=tenant_data.get('langue', 'mg'),
            )
            db.session.add(tenant)
            db.session.flush()
            print(f"Tenant créé: {tenant.nom}")
        
        # Créer l'admin du tenant
        admin = Utilisateur.query.filter_by(
            username=admin_data['username'],
            tenant_id=tenant.id
        ).first()
        
        if not admin:
            admin = Utilisateur(
                username=admin_data['username'],
                email=admin_data['email'],
                password_hash=hash_password(admin_data['password']),
                nom=admin_data.get('nom', 'Admin'),
                prenom=admin_data.get('prenom', 'System'),
                role=Role.ADMIN,
                statut=admin_data.get('statut', 'actif'),
                tenant_id=tenant.id,
            )
            db.session.add(admin)
            db.session.flush()
            print(f"Admin créé: {admin.username}")
        
        db.session.commit()
        return tenant, admin


def seed_default_tenant():
    """Crée le tenant par défaut"""
    default_password = "Test1234!"
    tenant_data = {
        'nom': 'ERP Démonstration',
        'slug': 'demo',
        'domaine': 'localhost',
        'email_contact': 'admin@demo.com',
        'plan': 'pro',
        'max_utilisateurs': 20,
        'max_produits': 1000,
        'max_clients': 500,
    }
    
    admin_data = {
        'username': 'admin',
        'email': 'admin@demo.com',
        'password': default_password,
        'nom': 'Administrateur',
        'prenom': 'System',
    }
    
    return seed_tenant(tenant_data, admin_data)


def seed_sample_data(tenant_slug='demo'):
    """Ajoute des données d'exemple pour un tenant"""
    app = create_app()
    
    with app.app_context():
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            print(f"Tenant {tenant_slug} non trouvé")
            return
        
        # Supprimer les anciennes données
        Produit.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        
        # Créer des produits d'exemple
        produits = [
            Produit(
                nom='Produit A',
                reference='PROD-001',
                prix_achat_ht=10.0,
                prix_vente_ht=15.0,
                quantite_stock=100,
                categorie='Electronique',
                tenant_id=tenant.id,
            ),
            Produit(
                nom='Produit B',
                reference='PROD-002',
                prix_achat_ht=20.0,
                prix_vente_ht=30.0,
                quantite_stock=50,
                categorie='Electronique',
                tenant_id=tenant.id,
            ),
            Produit(
                nom='Produit C',
                reference='PROD-003',
                prix_achat_ht=5.0,
                prix_vente_ht=10.0,
                quantite_stock=200,
                categorie='Alimentaire',
                tenant_id=tenant.id,
            ),
        ]
        
        for produit in produits:
            db.session.add(produit)
        
        db.session.commit()
        print(f"Données d'exemple créées pour {tenant.nom}")


if __name__ == '__main__':
    print("Initialisation du tenant par défaut...")
    seed_default_tenant()
    print("Données d'exemple...")
    seed_sample_data()
    print("Terminé!")
