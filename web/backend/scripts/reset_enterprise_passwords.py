import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.security.auth import hash_password

app = create_app()

ENTERPRISE_USERS = [
    {
        'tenant': {'nom': 'Tech Solutions SARL', 'slug': 'tech-solutions', 'domaine': 'tech.local', 'email_contact': 'contact@tech-solutions.com', 'telephone': '+261 34 12 345 67', 'adresse': '12 Rue de la Tech', 'ville': 'Antananarivo', 'code_postal': '101', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'pro'},
        'user': {'username': 'tech', 'email': 'tech@erp.com', 'password': 'TechPass123!', 'nom': 'Ramanantoandro', 'prenom': 'Thomas', 'telephone': '+261 34 12 345 67', 'role': Role.ADMIN, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 79.0, 'plan': 'pro', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'especes', 'reference_paiement': 'SUB-TECH-001'},
    },
    {
        'tenant': {'nom': 'Green Import', 'slug': 'green-import', 'domaine': 'green.local', 'email_contact': 'contact@green-import.com', 'telephone': '+261 34 98 765 32', 'adresse': '45 Avenue des Importateurs', 'ville': 'Toamasina', 'code_postal': '601', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'enterprise'},
        'user': {'username': 'green', 'email': 'green@erp.com', 'password': 'GreenPass123!', 'nom': 'Razafindramanana', 'prenom': 'Sophie', 'telephone': '+261 34 98 765 32', 'role': Role.MANAGER, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 199.0, 'plan': 'enterprise', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'virement', 'reference_paiement': 'SUB-GREEN-001'},
    },
    {
        'tenant': {'nom': 'DistriPlus', 'slug': 'distriplus', 'domaine': 'distri.local', 'email_contact': 'contact@distriplus.com', 'telephone': '+261 34 45 678 91', 'adresse': '8 Boulevard de la Distribution', 'ville': 'Antsirabe', 'code_postal': '401', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'starter'},
        'user': {'username': 'distri', 'email': 'distri@erp.com', 'password': 'DistriPass123!', 'nom': 'Rasoamanarivo', 'prenom': 'Lucas', 'telephone': '+261 34 45 678 91', 'role': Role.ADMIN, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 29.0, 'plan': 'starter', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'mvola', 'reference_paiement': 'SUB-DISTRI-001'},
    },
    {
        'tenant': {'nom': 'Global Trade', 'slug': 'global-trade', 'domaine': 'global.local', 'email_contact': 'contact@global-trade.com', 'telephone': '+261 34 56 789 01', 'adresse': '100 Rue du Commerce', 'ville': 'Toliara', 'code_postal': '301', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'pro'},
        'user': {'username': 'global', 'email': 'global@erp.com', 'password': 'GlobalPass123!', 'nom': 'Andriamiranto', 'prenom': 'Emma', 'telephone': '+261 34 56 789 01', 'role': Role.SALES, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 79.0, 'plan': 'pro', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'especes', 'reference_paiement': 'SUB-GLOBAL-001'},
    },
    {
        'tenant': {'nom': 'MegaStock', 'slug': 'megastock', 'domaine': 'mega.local', 'email_contact': 'contact@megastock.com', 'telephone': '+261 34 67 890 12', 'adresse': '25 Avenue des Entrepôts', 'ville': 'Antsiranana', 'code_postal': '201', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'enterprise'},
        'user': {'username': 'mega', 'email': 'mega@erp.com', 'password': 'MegaPass123!', 'nom': 'Ramiaramanana', 'prenom': 'Hugo', 'telephone': '+261 34 67 890 12', 'role': Role.STOCK, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 199.0, 'plan': 'enterprise', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'virement', 'reference_paiement': 'SUB-MEGA-001'},
    },
]


def main():
    with app.app_context():
        for item in ENTERPRISE_USERS:
            tenant = Tenant.query.filter_by(slug=item['tenant']['slug']).first()
            if tenant:
                utilisateur = Utilisateur.query.filter_by(tenant_id=tenant.id, email=item['user']['email']).first()
                if utilisateur:
                    utilisateur.password_hash = hash_password(item['user']['password'])
                    print(f"MAJ mot de passe: {item['user']['email']}")
                else:
                    user_data = dict(item['user'])
                    password = user_data.pop('password')
                    user_data['tenant_id'] = tenant.id
                    user_data['password_hash'] = hash_password(password)
                    utilisateur = Utilisateur(**user_data)
                    db.session.add(utilisateur)
                    print(f"Ajoute user: {item['user']['email']}")
            else:
                tenant = Tenant(**item['tenant'])
                db.session.add(tenant)
                db.session.flush()

                user_data = dict(item['user'])
                password = user_data.pop('password')
                user_data['tenant_id'] = tenant.id
                user_data['password_hash'] = hash_password(password)
                utilisateur = Utilisateur(**user_data)
                db.session.add(utilisateur)
                db.session.flush()

                abonnement_data = dict(item['abonnement'])
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
                print(f"Cree: {item['tenant']['nom']} | {item['user']['email']}")

        db.session.commit()
        print("\nListe des users entreprise:")
        for item in ENTERPRISE_USERS:
            print(f"- {item['user']['email']} / {item['user']['password']} ({item['user']['role'].value})")


if __name__ == '__main__':
    main()
