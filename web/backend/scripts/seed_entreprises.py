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
                'nom': 'DistriFood Madagascar',
                'slug': 'distrifood',
                'domaine': 'distrifood.local',
                'email_contact': 'contact@distrifood.mg',
                'telephone': '+261 32 02 345 67',
                'adresse': '12 Rue du Commerce',
                'ville': 'Antananarivo',
                'code_postal': '101',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'enterprise',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'distrifood',
                'email': 'distrifood@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Ravoahangy',
                'prenom': 'Mirana',
                'telephone': '+261 32 02 345 67',
                'role': Role.ADMIN,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 199.0,
                'plan': 'enterprise',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'virement',
                'reference_paiement': 'SUB-DISTRIFOOD-001',
            },
        },
        {
            'tenant': {
                'nom': 'Epicerie Solidaire',
                'slug': 'epicerie-solidaire',
                'domaine': 'epicerie.local',
                'email_contact': 'contact@epicerie.mg',
                'telephone': '+261 33 11 223 44',
                'adresse': "7 Avenue de l'Indépendance",
                'ville': 'Toamasina',
                'code_postal': '601',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'starter',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'epicerie',
                'email': 'epicerie@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Rabet',
                'prenom': 'Pascal',
                'telephone': '+261 33 11 223 44',
                'role': Role.ADMIN,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 29.0,
                'plan': 'starter',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'orange_money',
                'reference_paiement': 'SUB-EPICIE-001',
            },
        },
        {
            'tenant': {
                'nom': 'GrosRiz Import',
                'slug': 'grosriz',
                'domaine': 'grosriz.local',
                'email_contact': 'contact@grosriz.mg',
                'telephone': '+261 32 55 667 78',
                'adresse': '25 Zone Industrielle',
                'ville': 'Antsirabe',
                'code_postal': '401',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'pro',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'grosriz',
                'email': 'grosriz@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Rasimandimbison',
                'prenom': 'Jean',
                'telephone': '+261 32 55 667 78',
                'role': Role.SALES,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 79.0,
                'plan': 'pro',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'especes',
                'reference_paiement': 'SUB-GROSRIZ-001',
            },
        },
        {
            'tenant': {
                'nom': 'PharmaDistribution',
                'slug': 'pharmadistrib',
                'domaine': 'pharma.local',
                'email_contact': 'contact@pharma.mg',
                'telephone': '+261 34 77 889 01',
                'adresse': '9 Route de l\'Hôpital',
                'ville': 'Fianarantsoa',
                'code_postal': '301',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'enterprise',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'pharma',
                'email': 'pharma@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Rakoto',
                'prenom': 'Ange',
                'telephone': '+261 34 77 889 01',
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
                'reference_paiement': 'SUB-PHARMA-001',
            },
        },
        {
            'tenant': {
                'nom': 'Boutique en Ligne',
                'slug': 'boutiqueligne',
                'domaine': 'boutique.local',
                'email_contact': 'contact@boutique.mg',
                'telephone': '+261 32 33 44 55',
                'adresse': '16 Analakely',
                'ville': 'Antsiranana',
                'code_postal': '201',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'pro',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'boutique',
                'email': 'boutique@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Ranirison',
                'prenom': 'Sophie',
                'telephone': '+261 32 33 44 55',
                'role': Role.USER,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 79.0,
                'plan': 'pro',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'mvola',
                'reference_paiement': 'SUB-BOUTIQ-001',
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
