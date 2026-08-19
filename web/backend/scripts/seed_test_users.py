import os
import sys
import secrets
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.produit import Produit
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.security.auth import hash_password

app = create_app()

DEFAULT_PASSWORD = "Test1234!"

ENTERPRISE_USERS = [
    {
        'tenant': {
            'nom': 'DistriPro Entreprise',
            'slug': 'distripro-entreprise',
            'domaine': 'distripro.local',
            'email_contact': 'contact@distripro.com',
            'telephone': '+261 34 11 223 44',
            'adresse': '10 Avenue des Entreprises',
            'ville': 'Antsiranana',
            'code_postal': '201',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'enterprise',
        },
        'user': {
            'username': 'distripro',
            'email': 'distripro@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Ramanantoandro',
            'prenom': 'Alice',
            'telephone': '+261 34 11 223 44',
            'role': Role.MANAGER,
        },
        'abonnement': {
            'montant': 199.0,
            'plan': 'enterprise',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=90),
            'statut': StatutAbonnement.ACTIF,
        },
    },
    {
        'tenant': {
            'nom': 'GrossTech Distribution',
            'slug': 'grosstech-distribution',
            'domaine': 'grosstech.local',
            'email_contact': 'contact@grosstech.com',
            'telephone': '+261 34 22 334 45',
            'adresse': '55 Route Nationale',
            'ville': 'Antsirabe',
            'code_postal': '401',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'pro',
        },
        'user': {
            'username': 'grosstech',
            'email': 'grosstech@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Rasoamanarivo',
            'prenom': 'Paul',
            'telephone': '+261 34 22 334 45',
            'role': Role.ADMIN,
        },
        'abonnement': {
            'montant': 79.0,
            'plan': 'pro',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=60),
            'statut': StatutAbonnement.ACTIF,
        },
    },
]

WHOLESALE_USERS = [
    {
        'tenant': {
            'nom': 'Wholesale Center',
            'slug': 'wholesale-center',
            'domaine': 'wholesale.local',
            'email_contact': 'contact@wholesale.com',
            'telephone': '+261 34 33 444 56',
            'adresse': '7 Rue du Grossiste',
            'ville': 'Fianarantsoa',
            'code_postal': '301',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'pro',
        },
        'user': {
            'username': 'wholesale',
            'email': 'wholesale@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Andriamiranto',
            'prenom': 'Chloé',
            'telephone': '+261 34 33 444 56',
            'role': Role.SALES,
        },
        'abonnement': {
            'montant': 79.0,
            'plan': 'pro',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=60),
            'statut': StatutAbonnement.ACTIF,
        },
    },
    {
        'tenant': {
            'nom': 'Grossiste BTP',
            'slug': 'grossiste-btp',
            'domaine': 'grossiste-btp.local',
            'email_contact': 'contact@grossiste-btp.com',
            'telephone': '+261 34 44 554 67',
            'adresse': '22 Zone Industrielle',
            'ville': 'Toamasina',
            'code_postal': '601',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'starter',
        },
        'user': {
            'username': 'grossiste-btp',
            'email': 'grossiste-btp@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Ramiaramanana',
            'prenom': 'Olivia',
            'telephone': '+261 34 44 554 67',
            'role': Role.ADMIN,
        },
        'abonnement': {
            'montant': 29.0,
            'plan': 'starter',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=30),
            'statut': StatutAbonnement.ACTIF,
        },
    },
]

SIMPLE_USERS = [
    {
        'username': 'client.simple',
        'email': 'client.simple@erp.com',
        'password': DEFAULT_PASSWORD,
        'nom': 'Durand',
        'prenom': 'Marc',
        'role': Role.USER,
        'statut': StatutUtilisateur.ACTIF,
    },
    {
        'username': 'client.pub',
        'email': 'client.pub@erp.com',
        'password': DEFAULT_PASSWORD,
        'nom': 'Petit',
        'prenom': 'Lucie',
        'role': Role.USER,
        'statut': StatutUtilisateur.ACTIF,
    },
]


def _create_enterprise(data, kind):
    tenant = Tenant.query.filter_by(slug=data['tenant']['slug']).first()
    if tenant:
        print(f"[{kind}] Tenant existe deja: {tenant.slug}")
        return

    tenant = Tenant(**data['tenant'])
    db.session.add(tenant)
    db.session.flush()

    user = data['user']
    password = user.pop('password')
    user['tenant_id'] = tenant.id
    user['password_hash'] = hash_password(password)
    user['role'] = user.get('role', Role.ADMIN)
    user['statut'] = StatutUtilisateur.ACTIF
    utilisateur = Utilisateur(**user)
    db.session.add(utilisateur)
    db.session.flush()

    abonnement = Abonnement(**data['abonnement'])
    abonnement.tenant_id = tenant.id
    db.session.add(abonnement)
    db.session.flush()

    paiement = Paiement(
        tenant_id=tenant.id,
        montant=abonnement.montant,
        devise='MGA',
        statut=StatutPaiement.CONFIRME,
        type=TypePaiement.ABONNEMENT,
        reference=abonnement.reference_paiement or f"PAY-{tenant.slug}",
        notes=f"Paiement initial - {tenant.nom}",
        date_paiement=datetime.utcnow(),
    )
    db.session.add(paiement)

    db.session.flush()
    print(f"[{kind}] Cree: {tenant.nom} | {utilisateur.email} | role={utilisateur.role.value}")


def _seed_produits(tenant):
    produits = [
        Produit(
            reference=f"{tenant.slug.upper()}-PROD-001",
            nom='Produit Entreprise 1',
            description_courte='Article professionnel de qualite',
            categorie='Divers',
            prix_achat_ht=10.0,
            prix_vente_ht=15.0,
            quantite_stock=100,
            tenant_id=tenant.id,
        ),
        Produit(
            reference=f"{tenant.slug.upper()}-PROD-002",
            nom='Produit Entreprise 2',
            description_courte='Article professionnel de qualite',
            categorie='Divers',
            prix_achat_ht=20.0,
            prix_vente_ht=35.0,
            quantite_stock=50,
            tenant_id=tenant.id,
        ),
    ]
    for p in produits:
        db.session.add(p)
    db.session.flush()


def main():
    with app.app_context():
        db.create_all()

        print("=== Entreprises (enterprise) ===")
        for item in ENTERPRISE_USERS:
            _create_enterprise(item, 'ENTERPRISE')

        print("=== Grossistes (wholesaler) ===")
        for item in WHOLESALE_USERS:
            _create_enterprise(item, 'WHOLESALE')

        for tenant_data in (_i['tenant'] for _i in (ENTERPRISE_USERS + WHOLESALE_USERS)):
            tenant = Tenant.query.filter_by(slug=tenant_data['slug']).first()
            if tenant and not Produit.query.filter_by(tenant_id=tenant.id).first():
                _seed_produits(tenant)

        print("=== Utilisateurs simples ===")
        for u in SIMPLE_USERS:
            existing = Utilisateur.query.filter_by(email=u['email']).first()
            if existing:
                print(f"[SIMPLE] Existe deja: {existing.email}")
                continue
            password = u.pop('password')
            u['password_hash'] = hash_password(password)
            utilisateur = Utilisateur(**u)
            db.session.add(utilisateur)
            db.session.flush()
            print(f"[SIMPLE] Cree: {utilisateur.email} | role={utilisateur.role.value}")

        db.session.commit()
        print("\nSeed termine. Utilisateurs de test disponibles:")
        print(f" - Mot de passe par defaut: {DEFAULT_PASSWORD}")
        print(" - Enterprise: distripro@erp.com")
        print(" - Enterprise: grosstech@erp.com")
        print(" - Wholesale: wholesale@erp.com")
        print(" - Wholesale: grossiste-btp@erp.com")
        print(" - Simple: client.simple@erp.com")
        print(" - Simple: client.pub@erp.com")


if __name__ == '__main__':
    main()
