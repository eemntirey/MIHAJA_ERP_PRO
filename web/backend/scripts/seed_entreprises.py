from app import create_app, db
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.security.auth import hash_password
from datetime import datetime, timedelta
import os
import secrets

app = create_app()

DEFAULT_PASSWORD = os.getenv('SEED_USER_PASSWORD') or secrets.token_urlsafe(12)

with app.app_context():
    entreprises = [
        {
            'tenant': {
                'nom': 'Tech Solutions SARL',
                'slug': 'tech-solutions',
                'domaine': 'tech.local',
                'email_contact': 'contact@tech-solutions.com',
                'telephone': '+261 34 12 345 67',
                'adresse': '12 Rue de la Tech',
                'ville': 'Antananarivo',
                'code_postal': '101',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'pro',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'tech',
                'email': 'tech@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Ramanantoandro',
                'prenom': 'Thomas',
                'telephone': '+261 34 12 345 67',
                'role': Role.ADMIN,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 79.0,
                'plan': 'pro',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'carte',
                'reference_paiement': 'SUB-TECH-001',
            },
        },
        {
            'tenant': {
                'nom': 'Green Import',
                'slug': 'green-import',
                'domaine': 'green.local',
                'email_contact': 'contact@green-import.com',
                'telephone': '+261 34 98 765 32',
                'adresse': '45 Avenue des Importateurs',
                'ville': 'Toamasina',
                'code_postal': '601',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'enterprise',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'green',
                'email': 'green@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Razafindramanana',
                'prenom': 'Sophie',
                'telephone': '+261 34 98 765 32',
                'role': Role.MANAGER,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 199.0,
                'plan': 'enterprise',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'virement',
                'reference_paiement': 'SUB-GREEN-001',
            },
        },
        {
            'tenant': {
                'nom': 'DistriPlus',
                'slug': 'distriplus',
                'domaine': 'distri.local',
                'email_contact': 'contact@distriplus.com',
                'telephone': '+261 34 45 678 91',
                'adresse': '8 Boulevard de la Distribution',
                'ville': 'Antsirabe',
                'code_postal': '401',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'starter',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'distri',
                'email': 'distri@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Rasoamanarivo',
                'prenom': 'Lucas',
                'telephone': '+261 34 45 678 91',
                'role': Role.ADMIN,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 29.0,
                'plan': 'starter',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'mobile_money',
                'reference_paiement': 'SUB-DISTRI-001',
            },
        },
        {
            'tenant': {
                'nom': 'Global Trade',
                'slug': 'global-trade',
                'domaine': 'global.local',
                'email_contact': 'contact@global-trade.com',
                'telephone': '+261 34 56 789 01',
                'adresse': '100 Rue du Commerce',
                'ville': 'Toliara',
                'code_postal': '301',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'pro',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'global',
                'email': 'global@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Andriamiranto',
                'prenom': 'Emma',
                'telephone': '+261 34 56 789 01',
                'role': Role.SALES,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 79.0,
                'plan': 'pro',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'carte',
                'reference_paiement': 'SUB-GLOBAL-001',
            },
        },
        {
            'tenant': {
                'nom': 'MegaStock',
                'slug': 'megastock',
                'domaine': 'mega.local',
                'email_contact': 'contact@megastock.com',
                'telephone': '+261 34 67 890 12',
                'adresse': '25 Avenue des Entrepôts',
                'ville': 'Antsiranana',
                'code_postal': '201',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'enterprise',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'mega',
                'email': 'mega@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Ramiaramanana',
                'prenom': 'Hugo',
                'telephone': '+261 34 67 890 12',
                'role': Role.STOCK,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 199.0,
                'plan': 'enterprise',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'virement',
                'reference_paiement': 'SUB-MEGA-001',
            },
        },
    ]

    created_users = []

    for item in entreprises:
        tenant = Tenant(**item['tenant'])
        db.session.add(tenant)
        db.session.flush()

        user_data = item['user']
        user_data['tenant_id'] = tenant.id
        password = user_data.pop('password')
        user_data['password_hash'] = hash_password(password)
        user = Utilisateur(**user_data)
        db.session.add(user)
        db.session.flush()

        abonnement_data = item['abonnement']
        abonnement_data['tenant_id'] = tenant.id
        abonnement = Abonnement(**abonnement_data)
        db.session.add(abonnement)
        db.session.flush()

        paiement = Paiement(
            tenant_id=tenant.id,
            montant=abonnement.montant,
            devise='MGA',
            statut=StatutPaiement.CONFIRME,
            type=TypePaiement.ABONNEMENT,
            reference=abonnement.reference_paiement,
            notes=f"Paiement initial - {item['tenant']['nom']}",
            date_paiement=datetime.utcnow(),
        )
        db.session.add(paiement)
        db.session.flush()

        created_users.append({
            'tenant': tenant.nom,
            'email': user.email,
            'password': password,
            'role': user.role.value,
            'tenant_id': tenant.id,
        })

    db.session.commit()

    print('Entreprises et abonnements créés avec succès :')
    for u in created_users:
        print(f"- {u['tenant']} | {u['email']} | role={u['role']} | tenant_id={u['tenant_id']}")
