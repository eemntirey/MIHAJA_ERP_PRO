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
            'nom': 'DistriFood Madagascar',
            'slug': 'distrifood-entreprise',
            'domaine': 'distrifood.local',
            'email_contact': 'contact@distrifood.mg',
            'telephone': '+261 32 02 345 67',
            'adresse': '12 Rue du Commerce',
            'ville': 'Antananarivo',
            'code_postal': '101',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'enterprise',
        },
        'user': {
            'username': 'distrifood',
            'email': 'distrifood@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Ravoahangy',
            'prenom': 'Mirana',
            'telephone': '+261 32 02 345 67',
            'role': Role.ADMIN,
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
            'nom': 'Epicerie Solidaire',
            'slug': 'epicerie-solidaire-enterprise',
            'domaine': 'epicerie.local',
            'email_contact': 'contact@epicerie.mg',
            'telephone': '+261 33 11 223 44',
            'adresse': '7 Avenue de l\'Indépendance',
            'ville': 'Toamasina',
            'code_postal': '601',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'starter',
        },
        'user': {
            'username': 'epicerie',
            'email': 'epicerie@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Rabet',
            'prenom': 'Pascal',
            'telephone': '+261 33 11 223 44',
            'role': Role.ADMIN,
        },
        'abonnement': {
            'montant': 29.0,
            'plan': 'starter',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=60),
            'statut': StatutAbonnement.ACTIF,
        },
    },
    {
        'tenant': {
            'nom': 'GrosRiz Import',
            'slug': 'grosriz-distribution',
            'domaine': 'grosriz.local',
            'email_contact': 'contact@grosriz.mg',
            'telephone': '+261 32 55 667 78',
            'adresse': '25 Zone Industrielle',
            'ville': 'Antsirabe',
            'code_postal': '401',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'pro',
        },
        'user': {
            'username': 'grosriz',
            'email': 'grosriz@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Rasimandimbison',
            'prenom': 'Jean',
            'telephone': '+261 32 55 667 78',
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
            'nom': 'Semi-Gros Analamanga',
            'slug': 'wholesale-center',
            'domaine': 'semigros.local',
            'email_contact': 'contact@semigros.mg',
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
        'nom': 'Andriana',
        'prenom': 'Marie',
        'role': Role.USER,
        'statut': StatutUtilisateur.ACTIF,
    },
    {
        'username': 'client.pub',
        'email': 'client.pub@erp.com',
        'password': DEFAULT_PASSWORD,
        'nom': 'Ravoahangy',
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
            nom='Riz de première qualité',
            description_courte='Riz sélectionné, grain long, qualité supérieure',
            categorie='riz',
            prix_achat_ht=7000.0,
            prix_vente_ht=9500.0,
            quantite_stock=120,
            tenant_id=tenant.id,
        ),
        Produit(
            reference=f"{tenant.slug.upper()}-PROD-002",
            nom='Huile alimentaire 1L',
            description_courte='Huile de cuisine premium, bouteille 1L',
            categorie='huile',
            prix_achat_ht=10500.0,
            prix_vente_ht=13500.0,
            quantite_stock=85,
            tenant_id=tenant.id,
        ),
        Produit(
            reference=f"{tenant.slug.upper()}-PROD-003",
            nom='Savon barre',
            description_courte='Savon hygiène quotidienne, paquet de 5',
            categorie='savon',
            prix_achat_ht=6000.0,
            prix_vente_ht=8500.0,
            quantite_stock=200,
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

        print("=== Grossistes (wholesale) ===")
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
        print(" - Enterprise: distrifood@erp.com")
        print(" - Enterprise: epicerie@erp.com")
        print(" - Enterprise: grosriz@erp.com")
        print(" - Wholesale: wholesale@erp.com")
        print(" - Wholesale: grossiste-btp@erp.com")
        print(" - Simple: client.simple@erp.com")
        print(" - Simple: client.pub@erp.com")


if __name__ == '__main__':
    main()